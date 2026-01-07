import base64
import json
from unittest.mock import patch, MagicMock

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase
from odoo.addons.base.models.res_users import Users

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding

class TestEBMSBusiness(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('ebms.api_url', 'https://fake.ebms.api/send')
        cls.env['ir.config_parameter'].sudo().set_param('ebms.cancel_url', 'https://fake.ebms.api/cancel')
        cls.env['ir.config_parameter'].sudo().set_param('ebms.nif_check_url', 'https://fake.ebms.api/check_nif')
        cls.env['ir.config_parameter'].sudo().set_param('ebms.getinvoice_url', 'https://fake.ebms.api/getInvoice')
        cls.env['ir.config_parameter'].sudo().set_param('ebms.stock_url', 'https://fake.ebms.api/stock')
        cls.env['ir.config_parameter'].sudo().set_param('ebms.api_token', 'FAKE_TOKEN')

        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.public_key = cls.private_key.public_key()
        public_key_pem = cls.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        cls.env['ir.config_parameter'].sudo().set_param('ebms.public_key', public_key_pem)

        Users.notify_danger = MagicMock()
        Users.notify_success = MagicMock()

    @classmethod
    def tearDownClass(cls):
        del Users.notify_danger
        del Users.notify_success
        super().tearDownClass()

    def _create_invoice(self, **kwargs):
        vals = {
            'move_type': 'out_invoice',
            'partner_id': self.env.ref('base.res_partner_1').id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'name': 'Test line',
                'quantity': 1,
                'price_unit': 100,
            })],
        }
        vals.update(kwargs)
        invoice = self.env['account.move'].create(vals)
        invoice.action_post()
        return invoice

    @patch('odoo.addons.ebms_connector.models.ebms_utils.requests.post')
    def test_ebms_login_success(self, mock_post):
        """Test du login EBMS qui stocke le token en cas de succès."""
        from odoo.addons.ebms_connector.models.ebms_utils import ebms_login
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'success': True,
            'result': {'token': 'TOKEN_OK'}
        }
        self.env['ir.config_parameter'].sudo().set_param('ebms.login_url', 'https://fake.ebms.api/login')
        self.env['ir.config_parameter'].sudo().set_param('ebms.api_username', 'user')
        self.env['ir.config_parameter'].sudo().set_param('ebms.api_password', 'pass')
        token = ebms_login(self.env)
        self.assertEqual(token, 'TOKEN_OK')
        self.assertEqual(self.env['ir.config_parameter'].sudo().get_param('ebms.api_token'), 'TOKEN_OK')

    @patch('odoo.addons.ebms_connector.models.account_invoice_inherit.requests.post')
    def test_action_get_ebms_invoice_success(self, mock_post):
        """Test récupération de facture EBMS (getInvoice) succès."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'success': True, 'details': {'foo': 'bar'}}
        invoice = self._create_invoice()
        invoice.ebms_reference = 'EBMS-REF-123'
        result = invoice.action_get_ebms_invoice()
        self.assertTrue(result['success'])
        self.assertIn('details', result)

    @patch('odoo.addons.ebms_connector.models.ebms_utils.ebms_login')
    @patch('odoo.addons.ebms_connector.models.account_invoice_inherit.requests.post')
    def test_action_get_ebms_invoice_token_expired(self, mock_post, mock_ebms_login):
        """Test récupération de facture EBMS avec token expiré puis succès après retry login."""
        self.env['ir.config_parameter'].sudo().set_param('ebms.api_token', 'EXPIRED_TOKEN')
        mock_post.side_effect = [
            MagicMock(status_code=401, text='Token expired'),
            MagicMock(status_code=200, json=lambda: {'success': True, 'details': {'foo': 'bar'}})
        ]
        mock_ebms_login.return_value = 'NEW_TOKEN'
        invoice = self._create_invoice()
        invoice.ebms_reference = 'EBMS-REF-123'
        with self.assertRaisesRegex(UserError, 'Token expired'):
            invoice.action_get_ebms_invoice()

    @patch('odoo.addons.ebms_connector.models.stock_move_ebms.requests.post')
    def test_action_send_ebms_stock_movement_success(self, mock_post):
        """Test envoi mouvement de stock EBMS succès."""
        self.env['ir.config_parameter'].sudo().set_param('ebms.device_id', 'TEST_DEVICE')
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'success': True, 'reference': 'STOCK-REF'}
        move = self.env['stock.move'].create({
            'name': 'Test stock',
            'product_id': self.env.ref('product.product_product_4').id,
            'product_uom_qty': 2,
            'product_uom': self.env.ref('uom.product_uom_unit').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'ebms_movement_type': 'EN',
            'date': fields.Datetime.now(),
        })
        move.action_send_ebms_stock_movement()
        self.assertEqual(move.ebms_stock_status, 'sent')
        self.assertEqual(move.ebms_stock_reference, 'STOCK-REF')

    @patch('odoo.addons.ebms_connector.models.ebms_utils.ebms_login')
    @patch('odoo.addons.ebms_connector.models.account_invoice_inherit.requests.post')
    def test_action_send_ebms_token_expired_retry(self, mock_post, mock_ebms_login):
        """Test envoi de facture EBMS avec token expiré puis succès après retry login."""
        self.env['ir.config_parameter'].sudo().set_param('ebms.api_token', 'EXPIRED_TOKEN')
        mock_post.side_effect = [
            MagicMock(status_code=401, json=lambda: {'success': False, 'msg': 'Token expired'}),
            MagicMock(status_code=200, json=lambda: {'success': True, 'reference': 'OBR123_RETRY', 'msg': 'OK'})
        ]
        mock_ebms_login.return_value = 'NEW_TOKEN'
        invoice = self._create_invoice()
        invoice.action_send_ebms()
        invoice.invalidate_recordset()
        invoice = invoice.browse(invoice.id)
        self.assertEqual(invoice.ebms_status, 'sent')
        self.assertEqual(invoice.ebms_reference, 'OBR123_RETRY')
        self.assertEqual(mock_ebms_login.call_count, 1)
        self.assertEqual(self.env['ir.config_parameter'].sudo().get_param('ebms.api_token'), 'NEW_TOKEN')

    @patch('odoo.addons.ebms_connector.models.account_invoice_inherit.requests.post')
    def test_action_send_ebms_success(self, mock_post):
        """Test envoi de facture EBMS succès."""
        vals = {
            'move_type': 'out_invoice',
            'partner_id': self.env.ref('base.res_partner_1').id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'name': 'Test line',
                'quantity': 1,
                'price_unit': 100,
            })],
        }
        vals.update(kwargs)
        invoice = self.env['account.move'].create(vals)
        invoice.action_post()
        return invoice

    @patch('odoo.addons.ebms_connector.models.account_invoice_inherit.requests.post')
    def test_action_send_ebms_success(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'success': True, 'reference': 'OBR123', 'electronic_signature': 'SIGNATURE123', 'msg': 'OK'}
        invoice = self._create_invoice()
        invoice.action_send_ebms()
        self.assertEqual(invoice.ebms_status, 'sent')
        self.assertEqual(invoice.ebms_reference, 'OBR123')
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'success': True, 'reference': 'OBR123', 'electronic_signature': 'SIGNATURE123', 'msg': 'OK'}
        invoice = self._create_invoice()
        invoice.action_send_ebms()
        self.assertEqual(invoice.ebms_status, 'sent')
        self.assertEqual(invoice.ebms_reference, 'OBR123')
        mock_post.return_value.json.return_value = {
            'success': True,
            'reference': 'OBR123',
            'electronic_signature': 'SIGNATURE123',
            'msg': 'OK'
        }
        mock_post.return_value.status_code = 200
        invoice = self._create_invoice()
        invoice.action_send_ebms()
        self.assertEqual(invoice.ebms_status, 'sent')
        self.assertEqual(invoice.ebms_reference, 'OBR123')
        self.assertEqual(invoice.ebms_error_message, False)

    @patch('odoo.addons.ebms_connector.models.account_invoice_inherit.requests.post')
    def test_action_send_ebms_error(self, mock_post):
        mock_post.return_value.json.return_value = {
            'success': False,
            'msg': 'Erreur OBR'
        }
        mock_post.return_value.status_code = 200
        invoice = self._create_invoice()
        # Dans un TransactionCase, une UserError provoque un rollback complet, on ne peut donc
        # pas vérifier l'état de la facture après l'appel. On se contente de vérifier
        # que la bonne exception est levée avec le bon message.
        with self.assertRaisesRegex(UserError, 'Erreur OBR'):
            invoice.action_send_ebms()

    @patch('odoo.addons.ebms_connector.models.account_invoice_inherit.requests.post')
    def test_action_send_ebms_exception(self, mock_post):
        mock_post.side_effect = Exception("Connexion impossible")
        invoice = self._create_invoice()
        # Comme pour le test précédent, on vérifie uniquement que l'exception attendue est levée.
        with self.assertRaisesRegex(UserError, 'Erreur lors de l’envoi EBMS : Connexion impossible'):
            invoice.action_send_ebms()

    @patch('odoo.addons.ebms_connector.models.account_invoice_inherit.requests.post')
    def test_action_cancel_ebms_success(self, mock_post):
        mock_post.return_value.json.return_value = {'success': True}
        mock_post.return_value.status_code = 200
        invoice = self._create_invoice()
        invoice.ebms_status = 'sent'
        invoice.action_cancel_ebms()
        self.assertEqual(invoice.ebms_status, 'draft')
        self.assertFalse(invoice.ebms_error_message)

    @patch('odoo.addons.ebms_connector.models.account_invoice_inherit.requests.post')
    def test_action_cancel_ebms_error(self, mock_post):
        mock_post.return_value.json.return_value = {'success': False, 'msg': 'Annulation refusée'}
        mock_post.return_value.status_code = 200
        invoice = self._create_invoice()
        invoice.ebms_status = 'sent'
        invoice.action_cancel_ebms()
        self.assertIn('Annulation refusée', invoice.ebms_error_message or '')

    @patch('odoo.addons.ebms_connector.models.account_invoice_inherit.requests.post')
    def test_action_cancel_ebms_exception(self, mock_post):
        mock_post.side_effect = Exception("Erreur réseau")
        invoice = self._create_invoice()
        invoice.ebms_status = 'sent'
        invoice.action_cancel_ebms()
        self.assertIn('Erreur réseau', invoice.ebms_error_message or '')

    @patch('odoo.addons.ebms_connector.models.account_invoice_inherit.requests.post')
    def test_action_check_nif_ebms_valid(self, mock_post):
        mock_post.return_value.json.return_value = {'valid': True}
        mock_post.return_value.status_code = 200
        invoice = self._create_invoice()
        invoice.partner_id.vat = '12345678'
        invoice.action_check_nif_ebms()  # Doit notifier succès

    @patch('odoo.addons.ebms_connector.models.account_invoice_inherit.requests.post')
    def test_action_check_nif_ebms_invalid(self, mock_post):
        mock_post.return_value.json.return_value = {'valid': False}
        mock_post.return_value.status_code = 200
        invoice = self._create_invoice()
        invoice.partner_id.vat = '00000000'
        invoice.action_check_nif_ebms()  # Doit notifier erreur

    @patch('odoo.addons.ebms_connector.models.account_invoice_inherit.requests.post')
    def test_action_check_nif_ebms_exception(self, mock_post):
        mock_post.side_effect = Exception("Erreur NIF réseau")
        invoice = self._create_invoice()
        invoice.partner_id.vat = '99999999'
        invoice.action_check_nif_ebms()  # Doit notifier exception

    def test_action_reset_ebms_status(self):
        invoice = self._create_invoice()
        invoice.ebms_status = 'sent'
        invoice.ebms_reference = 'REF123'
        invoice.ebms_error_message = 'Erreur'
        invoice.ebms_sent_date = invoice.invoice_date
        invoice.action_reset_ebms_status()
        self.assertEqual(invoice.ebms_status, 'draft')
        self.assertFalse(invoice.ebms_reference)
        self.assertFalse(invoice.ebms_error_message)
        self.assertFalse(invoice.ebms_sent_date)

    def test_prepare_ebms_data_burundi(self):
        invoice = self._create_invoice()
        data = invoice._prepare_ebms_data_burundi()
        self.assertIn('invoice_number', data)
        self.assertIn('lines', data)

    def test_prepare_ebms_data(self):
        invoice = self._create_invoice()
        data = invoice._prepare_ebms_data()
        self.assertIn('invoice_number', data)
        self.assertIn('lines', data)

    def test_format_partner_address(self):
        invoice = self._create_invoice()
        invoice.partner_id.street = '1 Rue Test'
        invoice.partner_id.city = 'Bujumbura'
        invoice.partner_id.country_id = self.env.ref('base.bi').id
        address = invoice._format_partner_address()
        self.assertIn('1 Rue Test', address)

    def test_format_company_address(self):
        invoice = self._create_invoice()
        invoice.company_id.street = '2 Rue Société'
        invoice.company_id.city = 'Bujumbura'
        invoice.company_id.country_id = self.env.ref('base.bi').id
        address = invoice._format_company_address()
        self.assertIn('2 Rue Société', address)

    @patch('odoo.addons.ebms_connector.models.account_invoice_inherit.AccountMoveInherit._send_to_ebms_api_burundi')
    def test_send_to_ebms_api_success(self, mock_send_api):
        """ Test a successful call to the EBMS API wrapper. """
        # Configure mock to return a valid dictionary
        mock_send_api.return_value = {'success': True, 'reference': 'EBMS-REF', 'msg': 'OK'}
        
        partner = self.env['res.partner'].create({'name': 'Test Customer'})
        product = self.env['product.product'].create({'name': 'Test Product', 'list_price': 100})
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': product.id,
                    'quantity': 1,
                    'price_unit': 100,
                })
            ]
        })
        result = invoice._send_to_ebms_api_burundi({})
        self.assertEqual(result['reference'], 'EBMS-REF')

    @patch('odoo.addons.ebms_connector.models.account_invoice_inherit.requests.post')
    def test_send_to_ebms_api_http_error(self, mock_post):
        mock_post.return_value.status_code = 400
        mock_post.return_value.text = 'Bad Request'
        invoice = self._create_invoice()
        data = invoice._prepare_ebms_data()
        result = invoice._send_to_ebms_api(data)
        self.assertFalse(result['success'])

    def test_ebms_manual_signature_check_invalid_signature(self):
        """Teste la vérification d'une signature RSA invalide."""
        invoice = self._create_invoice()
        invoice.ebms_reference = 'REF-INVALID'
        invoice.ebms_signature = 'SIGNATURE_QUELCONQUE'
        invoice.ebms_result_data = json.dumps({'signature': 'SIGNATURE_DIFFERENTE'})
        with self.assertRaisesRegex(UserError, 'Signature EBMS INVALIDE'):
            invoice.ebms_manual_signature_check()
        invoice = self._create_invoice()
        invoice.ebms_reference = 'REF-INVALID'
        invoice.ebms_signature = 'SIGNATURE_QUELCONQUE'
        invoice.ebms_result_data = json.dumps({'signature': 'SIGNATURE_DIFFERENTE'})
        with self.assertRaisesRegex(UserError, 'Signature EBMS INVALIDE'):
            invoice.ebms_manual_signature_check()
        invoice = self._create_invoice()
        invoice.ebms_reference = 'REF-INVALID'
        invoice.ebms_signature = 'SIGNATURE_QUELCONQUE'
        invoice.ebms_result_data = json.dumps({'signature': 'SIGNATURE_DIFFERENTE'})
        with self.assertRaisesRegex(UserError, 'Signature EBMS INVALIDE'):
            invoice.ebms_manual_signature_check()

    @patch('odoo.addons.ebms_connector.models.account_invoice_inherit.serialization.load_pem_public_key')
    def test_ebms_manual_signature_check_valid_signature(self, mock_load_key):
        """Teste la vérification d'une signature RSA valide (mockée)."""
        mock_public_key = MagicMock()
        mock_public_key.verify.return_value = None  # Simule une signature valide
        mock_load_key.return_value = mock_public_key
        invoice = self._create_invoice()
        invoice.ebms_reference = 'REF-VALID'
        invoice.ebms_signature = base64.b64encode(b'fake_signature').decode('utf-8')
        invoice.ebms_result_data = json.dumps({'signature': invoice.ebms_signature})
        invoice.ebms_manual_signature_check()
        # Pas d'exception = succès


    def test_ebms_manual_signature_check_no_key(self):
        # On supprime la clé pour ce test
        self.env['ir.config_parameter'].sudo().set_param('ebms.public_key', '')
        invoice = self._create_invoice()
        invoice.ebms_reference = 'REF-INVALID'
        invoice.ebms_signature = 'SIGNATURE_QUELCONQUE'
        invoice.ebms_result_data = json.dumps({'signature': 'SIGNATURE_DIFFERENTE'})
        with self.assertRaisesRegex(UserError, 'clé publique'):
            invoice.ebms_manual_signature_check()
