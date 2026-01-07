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

    def _get_invoice_type(self):
        """
        Retourne le type de facture selon la nomenclature EBMS Burundi.
        FN = Facture Normale
        FA = Facture d'Avoir (Note de crédit)
        RC = Reçu Comptant
        """
        self.ensure_one()
        if self.move_type == 'out_refund':
            return 'FA'  # Facture d'avoir
        elif self.move_type == 'out_invoice':
            if self.invoice_payment_term_id and self.invoice_payment_term_id.line_ids:
                if all(line.days == 0 for line in self.invoice_payment_term_id.line_ids):
                    return 'RC'  # Reçu comptant
            return 'FN'  # Facture normale par défaut
        return 'FN'

    def _get_payment_type(self):
        """
        Retourne le type de paiement selon la nomenclature EBMS.
        1 = Espèces
        2 = Compte bancaire
        3 = Crédit
        4 = Autre
        """
        self.ensure_one()
        if self.invoice_payment_term_id:
            has_delay = any(line.days > 0 for line in self.invoice_payment_term_id.line_ids)
            if has_delay:
                return '3'  # Crédit
        if self.payment_state in ('paid', 'in_payment'):
            payments = self._get_reconciled_payments()
            if payments:
                journal = payments[0].journal_id
                if journal.type == 'cash':
                    return '1'  # Espèces
                elif journal.type == 'bank':
                    return '2'  # Compte bancaire
        return '1' if not self.invoice_payment_term_id else '3'

    def action_get_ebms_invoice(self, invoice_identifier=None):
        """
        Récupère les détails d'une facture EBMS via l'API getInvoice (conforme doc OBR).
        Si invoice_identifier n'est pas fourni, prend la référence EBMS de la facture courante.
        """
        self.ensure_one()
        url = self.env['ir.config_parameter'].sudo().get_param('ebms.getinvoice_url')
        token = self.env['ir.config_parameter'].sudo().get_param('ebms.api_token')
        if not url or not token:
            raise UserError(_('Paramètres API EBMS manquants (getinvoice_url ou token).'))
        if not invoice_identifier:
            invoice_identifier = self.ebms_reference
        if not invoice_identifier:
            raise UserError(_('Aucune référence EBMS disponible pour cette facture.'))
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        payload = {
            'invoice_identifier': invoice_identifier,
        }
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code == 200:
                resp_json = response.json()
                if resp_json.get('success'):
                    # Facultatif : stocker les détails récupérés ou les afficher
                    self.message_post(body=_('Détails EBMS récupérés: %s') % json.dumps(resp_json, ensure_ascii=False))
                    return resp_json
                else:
                    msg = resp_json.get('msg', 'Erreur lors de la récupération EBMS.')
                    self.message_post(body=_('Erreur récupération EBMS: %s') % msg)
                    raise UserError(_('Erreur récupération EBMS: %s') % msg)
            else:
                error_msg = f'Erreur HTTP {response.status_code}: {response.text}'
                self.message_post(body=error_msg)
                raise UserError(error_msg)
        except UserError:
            raise
        except Exception as e:
            self.message_post(body=_('Exception récupération EBMS: %s') % str(e))
            raise UserError(_('Exception récupération EBMS: %s') % str(e))

    def write(self, vals):
        res = super().write(vals)
        if 'ebms_status' in vals:
            _logger.info(f"[DIAG EBMS] Changement de statut EBMS pour factures {self.ids} -> {vals['ebms_status']}")
        return res

    ebms_status = fields.Selection([
        ('draft', 'Brouillon'),
        ('sent', 'Envoyé à EBMS'),
        ('error', 'Erreur d\'envoi')
    ], string='Statut EBMS', default='draft', required=True, help="Statut de l'envoi vers EBMS")
    ebms_reference = fields.Char(string='Référence EBMS', help='Référence EBMS fournie par l’OBR')
    ebms_signature = fields.Text(string='Signature électronique EBMS', help='Signature électronique reçue pour vérification')
    ebms_error_message = fields.Text(string='Message d\'erreur EBMS', help='Détails de l\'erreur EBMS')
    ebms_sent_date = fields.Datetime(string='Date d\'envoi EBMS', help='Date et heure d\'envoi vers EBMS')
    ebms_result_data = fields.Text(string='Données de résultat EBMS', help='Données JSON complètes de l\'objet "result" retourné par EBMS')

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
                # Logique "intelligente" pour choisir la source des données
                url = self.env['ir.config_parameter'].sudo().get_param('ebms.api_url')
                if url and '/ebms/demo/' in url:
                    ebms_data = record._prepare_ebms_data_demo()
                else:
                    ebms_data = record._prepare_ebms_data_burundi()
                
                result = record._send_to_ebms_api_burundi(ebms_data)
                # Log brut de la réponse pour audit
                try:
                    log_msg = f"[EBMS API Response] {json.dumps(result, ensure_ascii=False)}"
                except (TypeError, ValueError):
                    log_msg = f"[EBMS API Response] {str(result)}"
                record.message_post(body=log_msg)
                
                if result.get('success'):
                    # Correction pour mode demo : récupérer la référence et la signature même si elles sont dans result_data
                    def _first_non_empty(*args):
                        for v in args:
                            if v:
                                return v
                        return ''
                    ref = _first_non_empty(result.get('reference'), result.get('result_data', {}).get('reference', '') if result.get('result_data') else '')
                    sig = _first_non_empty(result.get('electronic_signature'), result.get('result_data', {}).get('electronic_signature', '') if result.get('result_data') else '')
                    record.write({
                        'ebms_status': 'sent',
                        'ebms_reference': ref,
                        'ebms_error_message': False,
                        'ebms_sent_date': fields.Datetime.now(),
                        'ebms_signature': sig,
                        'ebms_result_data': json.dumps(result, ensure_ascii=False) if isinstance(result, (dict, list)) else str(result),
                    })

                    message = _('Facture envoyée avec succès vers EBMS. Référence: %s') % ref
                    record.message_post(body=message)
                else:
                    record.write({
                        'ebms_status': 'error',
                        'ebms_error_message': result.get('msg', 'Erreur inconnue lors de l’envoi EBMS.')
                    })
                    error_message = _('Erreur lors de l’envoi EBMS : %s') % result.get('msg', 'Erreur inconnue')
                    record.message_post(body=error_message)
                    raise UserError(error_message)
            
            except UserError:
                raise # On laisse passer les UserError métier
            
            except Exception as e:
                record.write({
                    'ebms_status': 'error',
                    'ebms_error_message': str(e)
                })
                error_msg = _('Une erreur technique est survenue lors de l’envoi vers EBMS : %s') % str(e)
                record.message_post(body=error_msg)
                raise UserError(error_msg)

    def _prepare_ebms_data(self):
        return self._prepare_ebms_data_burundi()

    def _prepare_ebms_data_burundi(self):
        """
        Prépare un dictionnaire conforme à la structure attendue par l’API EBMS Burundi (voir doc OBR).
        """
        self.ensure_one()
        
        # Génération de l'identifiant de facture unique
        system_id = self.env['ir.config_parameter'].sudo().get_param('ebms.system_id', 'ws00000000000000')
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        invoice_identifier = f"{self.company_id.vat or ''}/{system_id}/{timestamp}/{self.name}"

        invoice_lines = []
        for line in self.invoice_line_ids.filtered(lambda l: not l.display_type):
            taxes = line.tax_ids.compute_all(line.price_unit, self.currency_id, line.quantity, product=line.product_id, partner=self.partner_id)
            
            vat_tax = sum(t['amount'] for t in taxes['taxes'] if 'TVA' in t['name'])
            ct_tax = sum(t['amount'] for t in taxes['taxes'] if 'TC' in t['name'])
            invoice_lines.append({
                'item_designation': line.name,
                'item_quantity': line.quantity,
                'item_price': line.price_unit,
                'item_ct': line.price_subtotal,
                'item_tl': 0,
                'item_vat': line.price_total - line.price_subtotal,
                'item_total_amount': line.price_total,
            })
        data = {
            'tp_type': '2' if self.company_id.partner_id.company_type == 'company' else '1',
            'tp_name': self.company_id.name,
            'tp_TIN': self.company_id.vat,
            'tp_trade_number': self.company_id.company_registry or '',
            'tp_postal_number': self.company_id.partner_id.zip or '',
            'tp_phone_number': self.company_id.partner_id.phone or '',
            'tp_address_province': self.company_id.partner_id.state_id.name or '',
            'tp_address_commune': self.company_id.partner_id.city or '',
            'tp_address_quartier': self.company_id.partner_id.street2 or '',
            'tp_address_avenue': '',
            'tp_address_rue': self.company_id.partner_id.street or '',
            'tp_address_number': '',
            'vat_taxpayer': '1' if self.company_id.vat else '0',
            'ct_taxpayer': '1',
            'tl_taxpayer': '0',
            'tp_fiscal_center': self.company_id.x_fiscal_center or '',
            'tp_activity_sector': self.company_id.x_activity_sector or '',
            'tp_legal_form': self.company_id.x_legal_form or '',
            'invoice_number': self.name,
            'invoice_date': self.invoice_date.strftime('%Y-%m-%d %H:%M:%S'),
            'invoice_type': self._get_ebms_invoice_type(),
            'invoice_currency': self.currency_id.name,
            'invoice_identifier': invoice_identifier,
            'payment_type': self._get_payment_type(),
            'customer_name': self.partner_id.name,
            'customer_TIN': self.partner_id.vat or '',
            'customer_address': self._format_partner_address(),
            'vat_customer_payer': '1' if self.partner_id.vat else '0',
            'lines': invoice_lines,
            'invoice_total_amount': self.amount_total,
        }
        if 'invoice_items' in data:
            data['lines'] = data.pop('invoice_items')
        if 'invoice_items' in data:
            data['lines'] = data.pop('invoice_items')
        if 'invoice_items' in data:
            data['lines'] = data.pop('invoice_items')
        return data

    def _prepare_ebms_data_demo(self):
        """
        Prépare un dictionnaire MINIMALISTE pour la DÉMO.
        Ne contient que les champs nécessaires pour que le contrôleur de démo fonctionne.
        """
        self.ensure_one()
        _logger.info('Préparation des données de DÉMO pour la facture %s avec un montant de %s', self.name, self.amount_total)
        invoice_lines = []
        for line in self.invoice_line_ids:
            invoice_lines.append({
                'item_designation': line.name,
                'item_quantity': line.quantity,
                'item_total': line.price_subtotal,
            })
        return {
            'invoice_number': self.name,
            'invoice_date': self.invoice_date.strftime('%Y-%m-%d'),
            'client_name': self.partner_id.name or '',
            'amount_total': self.amount_total,
            'lines': invoice_lines,
        }

    def ebms_manual_signature_check(self):
        """
        Vérifie manuellement la signature électronique EBMS en utilisant la clé publique de l'OBR.
        - Récupère la clé publique depuis les paramètres système.
        - Prépare les données signées (l'objet result JSON).
        - Utilise la cryptographie RSA pour valider la signature.
        - Notifie l'utilisateur du résultat (succès ou échec).
        """
        self.ensure_one()

        public_key_pem = self.env['ir.config_parameter'].sudo().get_param('ebms.public_key')
        if not public_key_pem:
            raise UserError(_("La clé publique de l'OBR n'est pas configurée (ebms.public_key)."))

        if not self.ebms_signature or not self.ebms_result_data:
            raise UserError(_("Signature EBMS INVALIDE. La signature ou les données de résultat sont manquantes pour la vérification."))

        try:
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode('utf-8'),
                backend=default_backend()
            )

            # Normalisation du JSON pour la signature
            import binascii
            message_dict = json.loads(self.ebms_result_data)
            message_bytes = json.dumps(
                message_dict,
                sort_keys=True,
                separators=(',', ':')
            ).encode('utf-8')

            # La signature reçue est en Base64, il faut la décoder.
            try:
                signature_bytes = base64.b64decode(self.ebms_signature)
            except binascii.Error:
                error_msg = _("Signature EBMS INVALIDE. La signature ne correspond pas aux données de la facture.")
                self.message_post(body=error_msg)
                raise UserError(error_msg)

            # L'API OBR signe le HASH du message, pas le message lui-même.
            public_key.verify(
                signature_bytes,
                message_bytes,
                padding.PKCS1v15(),
                hashes.SHA256()
            )

            # Si `verify` ne lève pas d'exception, la signature est valide.
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

        except (InvalidSignature, binascii.Error):
            _logger.error("Erreur de validation de signature: La signature ne correspond pas.")
            error_msg = _("Signature EBMS INVALIDE. La signature ne correspond pas aux données de la facture.")
            self.message_post(body=error_msg)
            raise UserError(error_msg)
        except Exception as e:
            _logger.error("Erreur technique de vérification de signature: %s", str(e))
            error_msg = _("Erreur technique lors de la vérification: %s") % str(e)
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
        if not url:
            return {'success': False, 'msg': 'Paramètre API EBMS manquant (url).'}
        # Si pas de token, ou token manifestement expiré, tente un login automatique
        if not token or len(token) < 10:
            from .ebms_utils import ebms_login
            token = ebms_login(self.env)
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        try:
            response = requests.post(url, headers=headers, json=ebms_data, timeout=30)
            _logger.info('EBMS DEMO: Réponse brute HTTP = %s', response.text)
            # Si le token est expiré côté serveur (erreur 401 ou message explicite), on tente un refresh + retry (une seule fois)
            if response.status_code == 401:
                _logger.warning('Token EBMS expiré ou invalide, tentative de rafraîchissement...')
                from .ebms_utils import ebms_login
                new_token = ebms_login(self.env)
                self.env['ir.config_parameter'].sudo().set_param('ebms.api_token', new_token)
                headers['Authorization'] = f'Bearer {new_token}'
                response = requests.post(url, headers=headers, json=ebms_data, timeout=30)
                _logger.info('EBMS RETRY: Réponse brute HTTP = %s', response.text)
            response.raise_for_status()
            resp_json = response.json()
            _logger.info('EBMS DEMO: Réponse JSON décodée = %s', resp_json)
            _logger.info('EBMS API Response: %s', resp_json)

            # Patch pour compatibilité demo : succès si 'success' ou (demo et 'result')
            is_demo_success = (url and '/ebms/demo/' in url and resp_json.get('result'))
            if resp_json.get('success') or is_demo_success:
                result_data = resp_json.get('result', {})
                # Recherche tolérante de la référence
                ref = (
                    resp_json.get('reference') or
                    resp_json.get('ref') or
                    resp_json.get('invoice_reference') or
                    result_data.get('reference') or
                    result_data.get('ref') or
                    result_data.get('invoice_reference') or
                    result_data.get('invoice_registered_number', '')
                )
                return {
                    'success': True,
                    'reference': ref,
                    'electronic_signature': resp_json.get('electronic_signature', ''),
                    'result_data': result_data, # Garder l'objet result complet pour la signature
                    'msg': resp_json.get('msg', 'Succès'),
                }
            else:
                return {
                    'success': False,
                    'msg': resp_json.get('msg', 'Erreur inconnue renvoyée par EBMS.'),
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

    def action_reset_ebms_status(self):
        """Remet le statut EBMS à brouillon"""
        for record in self:
            record.write({
                'ebms_status': 'draft',
                'ebms_reference': False,
                'ebms_error_message': False,
                'ebms_sent_date': False,
                'ebms_result_data': False,
            })
            record.message_post(body=_('Statut EBMS remis à brouillon'))

    # TODO: Ajouter la gestion des mouvements de stock selon la doc OBR
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
                    'reference': response.get('reference'),
                    'ebms_status': 'sent',
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
            
