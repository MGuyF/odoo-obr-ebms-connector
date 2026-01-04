from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


import time

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

    @http.route('/ebms/demo/send_invoice', type='json', auth='none', methods=['POST'], csrf=False)
    def ebms_demo_send_invoice(self, **kwargs):
        """
        Ceci est un FAUX endpoint d'API EBMS pour la démonstration.
        Il simule une réponse de succès ou d'erreur basée sur le montant de la facture.
        """
        try:
            invoice_data = getattr(request, 'jsonrequest', None)
            if invoice_data is None:
                import json
                try:
                    invoice_data = json.loads(request.httprequest.data)
                except Exception:
                    invoice_data = {}
            _logger.info('DEMO EBMS API a reçu: %s', invoice_data)

            amount_total = invoice_data.get('amount_total', 0)
            _logger.info('DEMO EBMS API: Montant total reçu = %s', amount_total)

            # Scénario 1: Succès
            if amount_total and amount_total < 1000000:
                response_data = {
                    'success': True,
                    'reference': f'OBR_DEMO_{int(time.time())}',
                    'electronic_signature': 'U0lHTkFUVVJFX0RFTU9fVkFMSURFXzEyMzQ1Njc4OTA=', # Signature base64 simulée
                    'msg': 'Facture reçue avec succès par le système de démo.'
                }
                return response_data

            # Scénario 2: Erreur métier
            else:
                error_msg = 'TEST_FINAL_ERREUR_V5: Le montant est invalide ou non fourni.'
                if amount_total >= 1000000:
                    error_msg = 'TEST_FINAL_ERREUR_V5: Le montant est trop élevé.'
                
                _logger.warning('DEMO EBMS API: Scénario d\'erreur déclenché. Message: %s', error_msg)
                return {'success': False, 'msg': error_msg}

        except Exception as e:
            _logger.error('Erreur dans le contrôleur de démo EBMS: %s', str(e))
            # Scénario 3: Erreur technique
            return {'success': False, 'msg': f'Erreur technique interne du serveur de démo: {e}'}
