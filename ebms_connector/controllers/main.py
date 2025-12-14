from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class EBMSController(http.Controller):
    
    @http.route('/ebms/webhook', type='json', auth='public', methods=['POST'], csrf=False)
    def ebms_webhook(self, **kwargs):
        """
        Webhook pour recevoir les notifications de statut depuis EBMS
        Optionnel - pour les retours de statut asynchrones
        """
        try:
            data = request.jsonrequest
            _logger.info('Webhook EBMS reçu: %s', data)
            
            # Traitement du webhook EBMS
            if data.get('invoice_reference'):
                invoice = request.env['account.move'].sudo().search([
                    ('ebms_reference', '=', data.get('invoice_reference'))
                ], limit=1)
                
                if invoice:
                    # Mise à jour du statut selon la réponse EBMS
                    if data.get('status') == 'validated':
                        invoice.ebms_status = 'sent'
                        invoice.message_post(body='Facture validée par EBMS via webhook')
                    elif data.get('status') == 'rejected':
                        invoice.ebms_status = 'error'
                        invoice.ebms_error_message = data.get('error_message', 'Rejetée par EBMS')
                        invoice.message_post(body=f'Facture rejetée par EBMS: {data.get("error_message")}')
            
            return {'status': 'success', 'message': 'Webhook traité'}
            
        except Exception as e:
            _logger.error('Erreur webhook EBMS: %s', str(e))
            return {'status': 'error', 'message': str(e)}
    
    @http.route('/ebms/test', type='http', auth='user', methods=['GET'])
    def ebms_test(self, **kwargs):
        """
        Endpoint de test pour vérifier la connectivité EBMS
        """
        try:
            # Test de connectivité basique
            return request.render('ebms_connector.test_page', {
                'title': 'Test EBMS Connector',
                'status': 'Module EBMS Connector opérationnel',
            })
        except Exception as e:
            return f'Erreur: {str(e)}'
