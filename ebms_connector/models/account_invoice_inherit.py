from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import requests
import json
import logging
from datetime import datetime
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature

_logger = logging.getLogger(__name__)


class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    ebms_status = fields.Selection([
        ('draft', 'Brouillon'),
        ('sent', 'Envoyé à EBMS'),
        ('error', 'Erreur d\'envoi')
    ], string='Statut EBMS', default='draft', help="Statut de l'envoi vers EBMS")
    ebms_reference = fields.Char(string='Référence EBMS', help='Référence EBMS fournie par l’OBR')
    ebms_signature = fields.Text(string='Signature électronique EBMS', help='Signature électronique reçue pour vérification')
    ebms_error_message = fields.Text(string='Message d\'erreur EBMS', help='Détails de l\'erreur EBMS')
    ebms_sent_date = fields.Datetime(string='Date d\'envoi EBMS', help='Date et heure d\'envoi vers EBMS')

    def action_send_ebms(self):
        """
        Envoi la facture à l’API EBMS du Burundi (conforme spécification OBR).
        - Prépare les données selon le format attendu
        - Appelle l’API avec authentification Bearer
        - Gère l’accusé de réception et la signature électronique
        - Met à jour le statut, la référence, la date, la signature, les erreurs
        """
        for record in self:
            if record.move_type not in ['out_invoice', 'out_refund', 'fa', 'rc']:
                raise UserError(_('Seules les factures clients (FN, FA, RC) peuvent être envoyées vers EBMS.'))
            if record.state != 'posted':
                raise UserError(_('La facture doit être validée avant l\'envoi vers EBMS.'))
            if record.ebms_status == 'sent':
                raise UserError(_('Cette facture a déjà été envoyée vers EBMS.'))

            try:
                ebms_data = record._prepare_ebms_data_burundi()
                result = record._send_to_ebms_api_burundi(ebms_data)
                # Log brut de la réponse pour audit
                record.message_post(body=f"[EBMS API Response] {json.dumps(result, ensure_ascii=False)}")
                if result.get('success'):
                    record.write({
                        'ebms_status': 'sent',
                        'ebms_reference': result.get('reference'),
                        'ebms_signature': result.get('electronic_signature'),
                        'ebms_sent_date': fields.Datetime.now(),
                        'ebms_error_message': False
                    })
                    message = _('Facture envoyée avec succès vers EBMS. Référence: %s') % result.get('reference')
                    record.message_post(body=message)
                else:
                    record.write({
                        'ebms_status': 'error',
                        'ebms_error_message': result.get('msg', 'Erreur inconnue lors de l’envoi EBMS.')
                    })
                    error_message = _('Erreur lors de l’envoi EBMS : %s') % result.get('msg', 'Erreur inconnue')
                    record.message_post(body=error_message)
                    raise UserError(error_message)
            except Exception as e:
                record.write({
                    'ebms_status': 'error',
                    'ebms_error_message': str(e)
                })
                error_msg = _('Une erreur technique est survenue lors de l’envoi vers EBMS : %s') % str(e)
                record.message_post(body=error_msg)
                raise UserError(error_msg)

    def _prepare_ebms_data_burundi(self):
        """
        Prépare un dictionnaire conforme à la structure attendue par l’API EBMS Burundi (voir doc OBR).
        Inclut : numéro, date, client, type, lignes, taxes, totaux, etc.
        """
        self.ensure_one()
        return {
            # En-tête facture EBMS
            'invoice_number': self.name,  # Numéro unique Odoo
            'invoice_date': self.invoice_date.strftime('%Y-%m-%d'),  # Date de la facture
            'invoice_time': self.invoice_date.strftime('%H:%M:%S') if self.invoice_date else '',  # Heure d’émission de la facture
            'cashier_name': self.env.user.name,  # Nom du caissier/opérateur
            'invoice_type': self._get_ebms_invoice_type(),  # FN, FA, RC
            'system_or_device_id': self.env['ir.config_parameter'].sudo().get_param('ebms.device_id', ''),
            'invoice_status': 'valid',  # TODO: Dynamique selon le statut réel
            'payment_amount': self.amount_total,  # TODO: Gérer les paiements partiels
            'invoice_reference': self.ref or '',  # Référence interne/externe supplémentaire
            # Données client
            'client_nif': self.partner_id.vat or '',
            'client_name': self.partner_id.name or '',
            'client_address': self.partner_id.contact_address or '',
            'client_phone': self.partner_id.phone or '',
            'client_email': self.partner_id.email or '',
            # Paiement
            'payment_type': '1',  # 1=Espèces, 2=Chèque, 3=Carte, 4=Mobile (à adapter)
            'payment_reference': self.payment_reference or self.name,
            # Devise
            'currency': self.currency_id.name,
            # Champs fiscaux
            'amount_untaxed': self.amount_untaxed,
            'amount_tax': self.amount_tax,
            'amount_total': self.amount_total,
            # Lignes de facture détaillées
            'lines': [
                {
                    'item_code': line.product_id.default_code or '',
                    'item_designation': line.name,
                    'item_quantity': line.quantity,
                    'item_measurement_unit': line.product_uom_id.name if line.product_uom_id else '',
                    'item_cost_price': line.price_unit,
                    'item_cost_price_currency': self.currency_id.name,
                    'item_vat': sum([t.amount for t in line.tax_ids if t.tax_group_id.name == 'TVA']),
                    'item_vat_rate': next((t.amount for t in line.tax_ids if t.tax_group_id.name == 'TVA'), 0.0),
                    'item_total': line.price_subtotal,
                    # Champs avancés EBMS
                    'item_tsce_tax': sum([t.amount for t in line.tax_ids if t.tax_group_id.name == 'TSCE']),
                    'item_ott_tax': sum([t.amount for t in line.tax_ids if t.tax_group_id.name == 'OTT']),
                    'item_price_nvat': line.price_subtotal,  # À ajuster selon la doc (prix hors TVA)
                    'item_price_wvat': line.price_total,     # À ajuster selon la doc (prix avec TVA)
                    'item_total_amount': line.price_total,   # Montant total ligne avec toutes taxes
                    'item_vat_code': next((t.name for t in line.tax_ids if t.tax_group_id.name == 'TVA'), ''),
                    'item_vat_category': '',  # TODO: Catégorie TVA selon la doc
                    'item_discount': 0.0,    # TODO: À calculer si remises
                    'item_discount_type': '', # TODO: Pourcentage ou montant fixe
                    # TODO: Ajouter d'autres champs avancés si besoin
                } for line in self.invoice_line_ids
            ],
            # Mouvements de stock EBMS (exemple de structure à adapter selon la doc OBR)
            'stock_movements': [
                # Exemple d'entrée, à générer dynamiquement selon les mouvements réels
                # {
                #     'movement_type': 'ENTREE',  # ou 'SORTIE', 'AJUSTEMENT', etc.
                #     'movement_date': '2023-11-25',
                #     'item_code': 'PROD123',
                #     'item_designation': 'Produit exemple',
                #     'quantity': 10,
                #     'uom': 'PCE',
                #     'warehouse': 'PRINCIPAL',
                #     # ... autres champs requis selon la doc OBR ...
                # }
                # TODO: Générer dynamiquement à partir des mouvements Odoo si besoin
            ],
            # Signature (à remplir après retour EBMS)
            'electronic_signature': '',
            # TODO: Ajouter d'autres blocs EBMS si besoin
        }

    def ebms_manual_signature_check(self):
        """
        Vérifie manuellement la signature électronique EBMS en utilisant la clé publique de l'OBR.
        - Récupère la clé publique depuis les paramètres système.
        - Prépare les données signées (concaténation de champs clés).
        - Utilise la cryptographie RSA pour valider la signature.
        - Notifie l'utilisateur du résultat (succès ou échec).
        """
        self.ensure_one()
        
        # 1. Récupérer la clé publique
        public_key_pem = self.env['ir.config_parameter'].sudo().get_param('ebms.public_key')
        if not public_key_pem:
            raise UserError(_("La clé publique de l'OBR n'est pas configurée dans les paramètres système (ebms.public_key)."))
            
        if not self.ebms_signature:
            raise UserError(_("Aucune signature électronique à vérifier pour cette facture."))

        try:
            # 2. Charger la clé publique
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode('utf-8'),
                backend=default_backend()
            )

            # 3. Préparer le message qui a été signé
            # IMPORTANT : La composition de ce message doit correspondre EXACTEMENT
            # à ce que l'API EBMS a signé. C'est généralement une concaténation
            # de champs clés de la facture. À adapter selon la doc de l'OBR.
            message_to_verify = f"{self.name}|{self.invoice_date}|{self.amount_total}|{self.ebms_reference}"
            message_bytes = message_to_verify.encode('utf-8')

            # 4. Décoder la signature (souvent en Base64)
            signature_bytes = base64.b64decode(self.ebms_signature)

            # 5. Vérifier la signature
            public_key.verify(
                signature_bytes,
                message_bytes,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            message = _("La signature électronique EBMS est VALIDE.")
            self.message_post(body=message)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Vérification Réussie'),
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }

        except InvalidSignature:
            error_msg = _("La signature électronique EBMS est INVALIDE. La facture pourrait être altérée ou frauduleuse.")
            self.message_post(body=error_msg)
            raise UserError(error_msg)
        except Exception as e:
            error_msg = _("Une erreur technique est survenue lors de la vérification de la signature : %s") % str(e)
            self.message_post(body=error_msg)
            raise UserError(error_msg)

    def _get_ebms_invoice_type(self):
        """
        Retourne le type de facture EBMS attendu ('FN', 'FA', 'RC') selon le contexte Odoo.
        """
        if self.move_type == 'out_invoice':
            return 'FN'
        elif self.move_type == 'out_refund':
            return 'FA'
        # TODO: Ajouter la détection pour 'RC' si besoin
        return 'FN'


    def _send_to_ebms_api_burundi(self, ebms_data):
        """
        Envoie les données à l’API EBMS (Burundi) via HTTP POST avec Bearer token.
        Retourne un dict avec success, reference, electronic_signature, msg, etc.
        """
        url = self.env['ir.config_parameter'].sudo().get_param('ebms.api_url')
        token = self.env['ir.config_parameter'].sudo().get_param('ebms.api_token')
        if not url or not token:
            return {'success': False, 'msg': 'Paramètres API EBMS manquants (url ou token).'}
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        try:
            response = requests.post(url, headers=headers, json=ebms_data, timeout=30)
            response.raise_for_status()
            resp_json = response.json()
            # Selon la doc OBR, adapter le parsing
            if resp_json.get('success'):
                return {
                    'success': True,
                    'reference': resp_json.get('reference', ''),
                    'electronic_signature': resp_json.get('electronic_signature', ''),
                    'msg': resp_json.get('msg', ''),
                }
            else:
                return {
                    'success': False,
                    'msg': resp_json.get('msg', 'Erreur inconnue côté EBMS.'),
                }
        except Exception as e:
            _logger.error('Erreur lors de l’appel API EBMS : %s', str(e))
            return {'success': False, 'msg': str(e)}

    def action_cancel_ebms(self):
        """
        Annule une facture côté EBMS (conforme doc OBR).
        Appelle l’endpoint d’annulation, gère la réponse et notifie l’utilisateur.
        """
        self.ensure_one()
        url = self.env['ir.config_parameter'].sudo().get_param('ebms.cancel_url')
        token = self.env['ir.config_parameter'].sudo().get_param('ebms.api_token')
        if not url or not token:
            raise UserError(_('Paramètres API EBMS manquants (url ou token).'))
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        payload = {
            'invoice_number': self.name,  # Ou autre identifiant selon la doc OBR
            # TODO: Ajouter d’autres champs requis si besoin
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            resp_json = response.json()
            self.message_post(body=f"[EBMS Cancel Response] {resp_json}")
            if resp_json.get('success'):
                self.ebms_status = 'draft'  # Ou autre statut selon la logique métier
                self.ebms_error_message = False
                message = _('Facture annulée avec succès côté EBMS.')
                self.message_post(body=message)
                self.env.user.notify_success(message)
            else:
                self.ebms_error_message = resp_json.get('msg', 'Erreur inconnue lors de l’annulation EBMS.')
                message = _('Erreur lors de l’annulation EBMS : %s') % resp_json.get('msg', 'Erreur inconnue')
                self.message_post(body=message)
                self.env.user.notify_danger(message)
        except Exception as e:
            self.ebms_error_message = str(e)
            error_msg = _('Exception annulation EBMS : %s') % e
            self.message_post(body=error_msg)
            self.env.user.notify_danger(error_msg)

    def action_check_nif_ebms(self):
        """
        Vérifie le NIF d’un client via l’API EBMS (conforme doc OBR).
        Appelle l’endpoint de vérification, affiche le résultat à l’utilisateur, loggue la réponse.
        """
        self.ensure_one()
        url = self.env['ir.config_parameter'].sudo().get_param('ebms.nif_check_url')
        token = self.env['ir.config_parameter'].sudo().get_param('ebms.api_token')
        if not url or not token:
            raise UserError(_('Paramètres API EBMS manquants (url ou token).'))
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        payload = {
            'nif': self.partner_id.vat or '',
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            resp_json = response.json()
            self.message_post(body=f"[EBMS NIF Check Response] {resp_json}")
            if resp_json.get('valid', False):
                message = _('NIF client valide selon EBMS.')
                self.message_post(body=message)
                self.env.user.notify_success(message)
            else:
                message = _('NIF client invalide ou non reconnu par EBMS.')
                self.message_post(body=message)
                self.env.user.notify_danger(message)
        except Exception as e:
            error_msg = _('Exception vérification NIF EBMS : %s') % e
            self.message_post(body=error_msg)
            self.env.user.notify_danger(error_msg)

    # TODO: Ajouter la gestion des mouvements de stock selon la doc OBR

    def _prepare_ebms_data(self):
        """
        Prépare les données de la facture pour l'envoi vers EBMS
        Format selon la documentation EBMS
        """
        self.ensure_one()
        
        # Préparation des lignes de facture
        invoice_lines = []
        for line in self.invoice_line_ids:
            if line.display_type not in ['line_section', 'line_note']:
                invoice_lines.append({
                    'description': line.name or line.product_id.name,
                    'quantity': line.quantity,
                    'unit_price': line.price_unit,
                    'discount': line.discount,
                    'tax_amount': sum(line.tax_ids.mapped('amount')),
                    'total': line.price_subtotal,
                })
        
        # Structure des données EBMS
        ebms_data = {
            'invoice_number': self.name,
            'invoice_date': self.invoice_date.isoformat() if self.invoice_date else False,
            'due_date': self.invoice_date_due.isoformat() if self.invoice_date_due else False,
            'customer': {
                'name': self.partner_id.name,
                'vat': self.partner_id.vat or '',
                'address': self._format_partner_address(),
                'phone': self.partner_id.phone or '',
                'email': self.partner_id.email or '',
            },
            'company': {
                'name': self.company_id.name,
                'vat': self.company_id.vat or '',
                'address': self._format_company_address(),
            },
            'lines': invoice_lines,
            'totals': {
                'subtotal': self.amount_untaxed,
                'tax_amount': self.amount_tax,
                'total': self.amount_total,
            },
            'currency': self.currency_id.name,
            'payment_terms': self.invoice_payment_term_id.name if self.invoice_payment_term_id else '',
        }
        
        return ebms_data

    def _format_partner_address(self):
        """Formate l'adresse du partenaire"""
        address_parts = []
        if self.partner_id.street:
            address_parts.append(self.partner_id.street)
        if self.partner_id.street2:
            address_parts.append(self.partner_id.street2)
        if self.partner_id.city:
            address_parts.append(self.partner_id.city)
        if self.partner_id.state_id:
            address_parts.append(self.partner_id.state_id.name)
        if self.partner_id.country_id:
            address_parts.append(self.partner_id.country_id.name)
        return ', '.join(address_parts)

    def _format_company_address(self):
        """Formate l'adresse de la société"""
        address_parts = []
        if self.company_id.street:
            address_parts.append(self.company_id.street)
        if self.company_id.street2:
            address_parts.append(self.company_id.street2)
        if self.company_id.city:
            address_parts.append(self.company_id.city)
        if self.company_id.state_id:
            address_parts.append(self.company_id.state_id.name)
        if self.company_id.country_id:
            address_parts.append(self.company_id.country_id.name)
        return ', '.join(address_parts)

    def _send_to_ebms_api(self, ebms_data):
        """
        Envoie les données vers l'API EBMS
        Cette méthode simule l'envoi - à remplacer par l'API réelle EBMS
        """
        # Configuration EBMS (à adapter selon la documentation réelle)
        ebms_config = self.env['ir.config_parameter'].sudo()
        ebms_url = ebms_config.get_param('ebms.api_url', 'https://api.ebms.cm/v1/invoices')
        ebms_token = ebms_config.get_param('ebms.api_token', '')
        
        if not ebms_token:
            # Mode simulation si pas de token configuré
            _logger.info('Mode simulation EBMS - Pas de token configuré')
            return {
                'success': True,
                'reference': f'EBMS-SIM-{datetime.now().strftime("%Y%m%d%H%M%S")}',
                'message': 'Envoi simulé avec succès'
            }
        
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {ebms_token}',
            }
            
            response = requests.post(
                ebms_url,
                json=ebms_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'reference': result.get('reference'),
                    'message': result.get('message', 'Envoi réussi')
                }
            else:
                return {
                    'success': False,
                    'error_message': f'Erreur HTTP {response.status_code}: {response.text}'
                }
                
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error_message': f'Erreur de connexion: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error_message': f'Erreur inattendue: {str(e)}'
            }

    def action_reset_ebms_status(self):
        """Remet le statut EBMS à brouillon"""
        for record in self:
            record.write({
                'ebms_status': 'draft',
                'ebms_reference': False,
                'ebms_error_message': False,
                'ebms_sent_date': False
            })
            record.message_post(body=_('Statut EBMS remis à brouillon'))

    def test_button_action(self):
        print("TEST BUTTON ACTION")
        return True

    def ebms_manual_signature_check(self):
        """
        Vérifie manuellement la signature électronique EBMS en utilisant la clé publique de l'OBR.
        - Récupère la clé publique depuis les paramètres système.
        - Prépare les données signées (concaténation de champs clés).
        - Utilise la cryptographie RSA pour valider la signature.
        - Notifie l'utilisateur du résultat (succès ou échec).
        """
        self.ensure_one()
        
        # 1. Récupérer la clé publique
        public_key_pem = self.env['ir.config_parameter'].sudo().get_param('ebms.public_key')
        if not public_key_pem:
            raise UserError(_("La clé publique de l'OBR n'est pas configurée dans les paramètres système (ebms.public_key)."))
            
        if not self.ebms_signature:
            raise UserError(_("Aucune signature électronique à vérifier pour cette facture."))

        try:
            # 2. Charger la clé publique
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode('utf-8'),
                backend=default_backend()
            )

            # 3. Préparer le message qui a été signé
            # IMPORTANT : La composition de ce message doit correspondre EXACTEMENT
            # à ce que l'API EBMS a signé. C'est généralement une concaténation
            # de champs clés de la facture. À adapter selon la doc de l'OBR.
            message_to_verify = f"{self.name}|{self.invoice_date}|{self.amount_total}|{self.ebms_reference}"
            message_bytes = message_to_verify.encode('utf-8')

            # 4. Décoder la signature (souvent en Base64)
            signature_bytes = base64.b64decode(self.ebms_signature)

            # 5. Vérifier la signature
            public_key.verify(
                signature_bytes,
                message_bytes,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            message = _("La signature électronique EBMS est VALIDE.")
            self.message_post(body=message)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Vérification Réussie'),
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }

        except InvalidSignature:
            error_msg = _("La signature électronique EBMS est INVALIDE. La facture pourrait être altérée ou frauduleuse.")
            self.message_post(body=error_msg)
            raise UserError(error_msg)
        except Exception as e:
            error_msg = _("Une erreur technique est survenue lors de la vérification de la signature : %s") % str(e)
            self.message_post(body=error_msg)
            raise UserError(error_msg)
