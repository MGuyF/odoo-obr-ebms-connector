from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # --- Paramètres de l'API EBMS ---
    ebms_api_url = fields.Char(
        string='URL de l\'API EBMS (Envoi)',
        config_parameter='ebms.api_url',
        help='URL de l\'endpoint pour l\'envoi des factures.'
    )
    ebms_cancel_url = fields.Char(
        string='URL de l\'API EBMS (Annulation)',
        config_parameter='ebms.cancel_url',
        help='URL de l\'endpoint pour l\'annulation des factures.'
    )
    ebms_nif_check_url = fields.Char(
        string='URL de l\'API EBMS (Vérification NIF)',
        config_parameter='ebms.nif_check_url',
        help='URL de l\'endpoint pour la vérification du NIF.'
    )
    ebms_api_username = fields.Char(
        string="Nom d'utilisateur EBMS",
        config_parameter='ebms.api_username',
        help="Nom d'utilisateur pour l'authentification EBMS."
    )
    ebms_api_password = fields.Char(
        string="Mot de passe EBMS",
        config_parameter='ebms.api_password',
        help="Mot de passe pour l'authentification EBMS.",
    )
    ebms_api_token = fields.Char(
        string='Token d\'authentification EBMS',
        config_parameter='ebms.api_token',
        help='Token Bearer pour l\'authentification auprès de l\'API.'
    )
    ebms_public_key = fields.Char(
        string='Clé Publique de l\'OBR',
        config_parameter='ebms.public_key',
        help='Clé publique au format PEM fournie par l\'OBR pour la vérification des signatures.'
    )
