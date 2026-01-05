from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging

_logger = logging.getLogger(__name__)

class StockMoveEBMS(models.Model):
    _inherit = 'stock.move'

    ebms_stock_status = fields.Selection([
        ('draft', 'Brouillon'),
        ('sent', 'Envoyé à EBMS'),
        ('error', 'Erreur d\'envoi')
    ], string='Statut EBMS Stock', default='draft', required=True)
    ebms_stock_reference = fields.Char(string='Référence EBMS Stock')
    ebms_stock_error_message = fields.Text(string="Erreur EBMS Stock")
    ebms_stock_sent_date = fields.Datetime(string="Date d'envoi EBMS Stock")

    def action_send_ebms_stock_movement(self):
        """
        Envoie le mouvement de stock à l'API EBMS AddStockMovement selon la spécification OBR.
        """
        for move in self:
            # Préparer les données strictement selon la spécification EBMS
            system_id = self.env['ir.config_parameter'].sudo().get_param('ebms.device_id')
            url = self.env['ir.config_parameter'].sudo().get_param('ebms.stock_url')
            token = self.env['ir.config_parameter'].sudo().get_param('ebms.api_token')
            if not (system_id and url and token):
                raise UserError(_('Paramètres EBMS manquants (device_id, stock_url ou token).'))
            # Champs obligatoires
            payload = {
                "system_or_device_id": system_id,
                "item_code": move.product_id.default_code or '',
                "item_designation": move.product_id.name or '',
                "item_quantity": str(move.product_uom_qty),
                "item_measurement_unit": move.product_uom.name or '',
                "item_cost_price": str(move.price_unit),
                "item_cost_price_currency": move.company_id.currency_id.name or 'BIF',
                "item_movement_type": move.ebms_movement_type or '',
                "item_movement_invoice_ref": move.ebms_movement_invoice_ref or '',
                "item_movement_description": move.ebms_movement_description or '',
                "item_movement_date": fields.Datetime.to_string(move.date or fields.Datetime.now()),
            }
            # Validation des champs obligatoires
            missing = [k for k, v in payload.items() if not v and k not in ('item_movement_invoice_ref','item_movement_description')]
            if missing:
                raise UserError(_('Champs obligatoires manquants pour EBMS: %s') % ', '.join(missing))

            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            }
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=30)
                if response.status_code == 200:
                    resp_json = response.json()
                    if resp_json.get('success'):
                        move.write({
                            'ebms_stock_status': 'sent',
                            'ebms_stock_reference': resp_json.get('reference', ''),
                            'ebms_stock_error_message': False,
                            'ebms_stock_sent_date': fields.Datetime.now(),
                        })
                        move.message_post(body=_('Mouvement de stock envoyé avec succès à EBMS.'))
                    else:
                        move.write({
                            'ebms_stock_status': 'error',
                            'ebms_stock_error_message': resp_json.get('msg', 'Erreur inconnue lors de l’envoi EBMS.')
                        })
                        move.message_post(body=_('Erreur EBMS Stock: %s') % resp_json.get('msg', ''))
                        raise UserError(_('Erreur EBMS Stock: %s') % resp_json.get('msg', ''))
                else:
                    move.write({
                        'ebms_stock_status': 'error',
                        'ebms_stock_error_message': f'Erreur HTTP {response.status_code}: {response.text}'
                    })
                    move.message_post(body=_('Erreur HTTP EBMS Stock: %s') % response.text)
                    raise UserError(_('Erreur HTTP EBMS Stock: %s') % response.text)
            except Exception as e:
                move.write({
                    'ebms_stock_status': 'error',
                    'ebms_stock_error_message': str(e)
                })
                move.message_post(body=_('Exception lors de l’envoi EBMS Stock: %s') % str(e))
                raise UserError(_('Exception lors de l’envoi EBMS Stock: %s') % str(e))

    # Champs EBMS spécifiques au mouvement de stock
    ebms_movement_type = fields.Selection([
        ('EN', 'Entrée normale'),
        ('ER', 'Entrée retour'),
        ('EI', 'Entrée inventaire'),
        ('EAJ', 'Entrée ajustement'),
        ('ET', 'Entrée transfert'),
        ('EAU', 'Entrée autre'),
        ('SN', 'Sortie normale'),
        ('SP', 'Sortie perte'),
        ('SV', 'Sortie vente'),
        ('SD', 'Sortie destruction'),
        ('SC', 'Sortie consommation'),
        ('SAJ', 'Sortie ajustement'),
        ('ST', 'Sortie transfert'),
        ('SAU', 'Sortie autre'),
    ], string='Type de mouvement EBMS', required=True)
    ebms_movement_invoice_ref = fields.Char(string='Réf. facture mouvement (optionnel)')
    ebms_movement_description = fields.Char(string='Description mouvement (optionnel)')
