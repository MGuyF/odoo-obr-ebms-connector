from unittest.mock import patch, MagicMock
from odoo.tests.common import TransactionCase
from odoo import fields
from odoo.exceptions import UserError
from odoo.addons.base.models.res_users import Users
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature
import base64

class TestEBMSBusiness(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Configuration des paramètres système une seule fois pour toute la classe de test
        cls.env['ir.config_parameter'].sudo().set_param('ebms.api_url', 'https://fake.ebms.api/send')
        cls.env['ir.config_parameter'].sudo().set_param('ebms.cancel_url', 'https://fake.ebms.api/cancel')
        cls.env['ir.config_parameter'].sudo().set_param('ebms.nif_check_url', 'https://fake.ebms.api/check_nif')
        cls.env['ir.config_parameter'].sudo().set_param('ebms.api_token', 'FAKE_TOKEN')

        # Générer une paire de clés RSA pour les tests de signature
        cls.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        cls.public_key = cls.private_key.public_key()

        # Sérialiser la clé publique au format PEM pour la stocker dans les paramètres
        public_key_pem = cls.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')

        cls.env['ir.config_parameter'].sudo().set_param('ebms.public_key', public_key_pem)

        # Monkey-patching: Ajoute dynamiquement les méthodes de notification à la classe res.users
        Users.notify_danger = MagicMock()
        Users.notify_success = MagicMock()

    @classmethod
    def tearDownClass(cls):
        # Nettoyage du monkey-patching pour ne pas affecter d'autres tests
        del Users.notify_danger
        del Users.notify_success
        super().tearDownClass()

    def setUp(self):
        super().setUp()
    def _create_invoice(self, **kwargs):
        """Crée une facture en draft, la poste et la retourne."""
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
        with self.assertRaisesRegex(UserError, 'Connexion impossible'):
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

    @patch('odoo.addons.ebms_connector.models.account_invoice_inherit.requests.post')
    def test_send_to_ebms_api_success(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'reference': 'EBMS-REF', 'message': 'OK'}
        invoice = self._create_invoice()
        data = invoice._prepare_ebms_data()
        result = invoice._send_to_ebms_api(data)
        self.assertTrue(result['success'])
        self.assertEqual(result['reference'], 'EBMS-REF')

    @patch('odoo.addons.ebms_connector.models.account_invoice_inherit.requests.post')
    def test_send_to_ebms_api_http_error(self, mock_post):
        mock_post.return_value.status_code = 400
        mock_post.return_value.text = 'Bad Request'
        invoice = self._create_invoice()
        data = invoice._prepare_ebms_data()
        result = invoice._send_to_ebms_api(data)
        self.assertFalse(result['success'])
        self.assertIn('Erreur HTTP', result['error_message'])

    @patch('odoo.addons.ebms_connector.models.account_invoice_inherit.requests.post')
    def test_send_to_ebms_api_request_exception(self, mock_post):
        import requests
        mock_post.side_effect = requests.exceptions.RequestException("Timeout")
        invoice = self._create_invoice()
        data = invoice._prepare_ebms_data()
        result = invoice._send_to_ebms_api(data)
        self.assertFalse(result['success'])
        self.assertIn('Erreur de connexion', result['error_message'])

    def test_ebms_manual_signature_check_no_key(self):
        # On supprime la clé pour ce test
        self.env['ir.config_parameter'].sudo().set_param('ebms.public_key', '')
        invoice = self._create_invoice()
        invoice.ebms_signature = 'FAKE'
        with self.assertRaises(UserError):
            invoice.ebms_manual_signature_check()

    def test_ebms_manual_signature_check_no_signature(self):
        invoice = self._create_invoice()
        invoice.ebms_signature = False
        with self.assertRaises(UserError):
            invoice.ebms_manual_signature_check()

    def test_ebms_manual_signature_check_valid_signature(self):
        """Teste la vérification d'une signature RSA valide."""
        invoice = self._create_invoice()
        invoice.ebms_reference = 'REF-VALID'

        # Préparer le message à signer
        message_to_sign = f"{invoice.name}|{invoice.invoice_date}|{invoice.amount_total}|{invoice.ebms_reference}".encode('utf-8')

        # Signer avec la clé privée
        signature = self.private_key.sign(
            message_to_sign,
            padding.PKCS1v15(),
            hashes.SHA256()
        )

        invoice.ebms_signature = base64.b64encode(signature).decode('utf-8')

        # Appeler la méthode. Aucune exception ne doit être levée.
        try:
            invoice.ebms_manual_signature_check()
        except UserError as e:
            self.fail(f"La vérification de signature valide a échoué avec l'erreur : {e}")

    def test_ebms_manual_signature_check_invalid_signature(self):
        """Teste la vérification d'une signature RSA invalide."""
        invoice = self._create_invoice()
        invoice.ebms_reference = 'REF-INVALID'

        # Créer une fausse signature (données incorrectes)
        message_to_sign = f"DONNEES_INCORRECTES".encode('utf-8')

        signature = self.private_key.sign(
            message_to_sign,
            padding.PKCS1v15(),
            hashes.SHA256()
        )

        invoice.ebms_signature = base64.b64encode(signature).decode('utf-8')

        # La vérification doit lever une UserError contenant 'INVALIDE'
        with self.assertRaisesRegex(UserError, 'INVALIDE'):
            invoice.ebms_manual_signature_check()
