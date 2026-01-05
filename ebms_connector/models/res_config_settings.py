from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # --- Paramètres de connexion EBMS ---
    ebms_api_url = fields.Char(
        string="URL EBMS - Envoi factures",
        config_parameter='ebms.api_url',
        help="URL de l'endpoint pour l'envoi des factures (addInvoice_confirm)."
    )
    ebms_api_url_old = fields.Char(
        string="URL EBMS - Ancien envoi",
        config_parameter='ebms.api_url_old',
        help="Ancien endpoint addInvoice (sans accusé réception)."
    )
    ebms_cancel_url = fields.Char(
        string="URL EBMS - Annulation facture",
        config_parameter='ebms.cancel_url',
        help="URL de l'endpoint pour l'annulation des factures."
    )
    ebms_nif_check_url = fields.Char(
        string="URL EBMS - Vérification NIF",
        config_parameter='ebms.nif_check_url',
        help="URL de l'endpoint pour la vérification du NIF."
    )
    ebms_login_url = fields.Char(
        string="URL EBMS - Authentification",
        config_parameter='ebms.login_url',
        help="URL de l'endpoint pour obtenir un token d'accès EBMS."
    )
    ebms_getinvoice_url = fields.Char(
        string="URL EBMS - Consultation facture",
        config_parameter='ebms.getinvoice_url',
        help="URL de l'endpoint pour consulter une facture EBMS."
    )
    ebms_stock_url = fields.Char(
        string="URL EBMS - Mouvements de stock",
        config_parameter='ebms.stock_url',
        help="URL de l'endpoint pour l'envoi des mouvements de stock."
    )
    
    ebms_api_username = fields.Char(
        string="Nom d'utilisateur EBMS",
        config_parameter='ebms.api_username',
        help="Nom d'utilisateur pour l'authentification EBMS."
    )
    ebms_api_password = fields.Char(
        string="Mot de passe EBMS",
        config_parameter='ebms.api_password',
        help="Mot de passe pour l'authentification EBMS."
    )
    ebms_api_token = fields.Char(
        string="Token d'authentification EBMS",
        config_parameter='ebms.api_token',
        help="Token Bearer pour l'authentification auprès de l'API."
    )
    ebms_public_key = fields.Text(
        string="Clé Publique OBR (PEM)",
        config_parameter='ebms.public_key',
        help="Clé publique PEM fournie par l'OBR pour la vérification des signatures."
    )
    ebms_system_id = fields.Char(
        string="ID système EBMS",
        config_parameter='ebms.system_id',
        help="Identifiant du système du contribuable fourni par l'OBR."
    )
    
    # --- Paramètres société/fiscalité EBMS (préfixe ebms_ pour éviter conflit) ---
    ebms_tp_tin = fields.Char(
        string="NIF du contribuable (tp_TIN)",
        config_parameter='ebms.tp_tin',
        help="NIF du contribuable (tp_TIN)."
    )
    ebms_tp_name = fields.Char(
        string="Nom du contribuable (tp_name)",
        config_parameter='ebms.tp_name',
        help="Nom commercial ou nom/prénom du contribuable."
    )
    ebms_tp_type = fields.Selection([
        ('1', 'Personne physique'),
        ('2', 'Personne morale')
    ], string="Type de contribuable (tp_type)",
        config_parameter='ebms.tp_type',
        help="Type de contribuable : 1=physique, 2=morale."
    )
    ebms_tp_trade_number = fields.Char(
        string="N° registre de commerce",
        config_parameter='ebms.tp_trade_number',
        help="Numéro du registre de commerce du contribuable."
    )
    ebms_tp_postal_number = fields.Char(
        string="Boîte postale",
        config_parameter='ebms.tp_postal_number',
        help="Boîte postale du contribuable."
    )
    ebms_tp_phone_number = fields.Char(
        string="Téléphone du contribuable",
        config_parameter='ebms.tp_phone_number',
        help="Numéro de téléphone du contribuable."
    )
    ebms_tp_address_province = fields.Char(
        string="Adresse - Province",
        config_parameter='ebms.tp_address_province',
        help="Province du contribuable."
    )
    ebms_tp_address_commune = fields.Char(
        string="Adresse - Commune",
        config_parameter='ebms.tp_address_commune',
        help="Commune du contribuable."
    )
    ebms_tp_address_quartier = fields.Char(
        string="Adresse - Quartier",
        config_parameter='ebms.tp_address_quartier',
        help="Quartier du contribuable."
    )
    ebms_tp_address_avenue = fields.Char(
        string="Adresse - Avenue",
        config_parameter='ebms.tp_address_avenue',
        help="Avenue du contribuable."
    )
    ebms_tp_address_rue = fields.Char(
        string="Adresse - Rue",
        config_parameter='ebms.tp_address_rue',
        help="Rue du contribuable."
    )
    ebms_tp_address_number = fields.Char(
        string="Adresse - Numéro",
        config_parameter='ebms.tp_address_number',
        help="Numéro d'adresse du contribuable."
    )
    ebms_vat_taxpayer = fields.Selection([
        ('0', 'Non assujetti'),
        ('1', 'Assujetti')
    ], string="Assujetti TVA (vat_taxpayer)",
        config_parameter='ebms.vat_taxpayer',
        help="Assujetti à la TVA : 0=non, 1=oui."
    )
    ebms_ct_taxpayer = fields.Selection([
        ('0', 'Non assujetti'),
        ('1', 'Assujetti')
    ], string="Assujetti Taxe Consommation (ct_taxpayer)",
        config_parameter='ebms.ct_taxpayer',
        help="Assujetti à la taxe de consommation : 0=non, 1=oui."
    )
    ebms_tl_taxpayer = fields.Selection([
        ('0', 'Non assujetti'),
        ('1', 'Assujetti')
    ], string="Assujetti PFL (tl_taxpayer)",
        config_parameter='ebms.tl_taxpayer',
        help="Assujetti au prélèvement forfaitaire libératoire : 0=non, 1=oui."
    )
    ebms_tp_fiscal_center = fields.Char(
        string="Centre fiscal EBMS",
        config_parameter='ebms.tp_fiscal_center',
        help="Centre fiscal du contribuable. (DGC, DMC, DPMC)"
    )
    ebms_tp_activity_sector = fields.Char(
        string="Secteur d'activité EBMS",
        config_parameter='ebms.tp_activity_sector',
        help="Secteur d'activité du contribuable."
    )
    ebms_tp_legal_form = fields.Char(
        string="Forme juridique EBMS",
        config_parameter='ebms.tp_legal_form',
        help="Forme juridique du contribuable."
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
