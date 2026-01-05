{
    'name': 'EBMS Connector',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Connecteur EBMS pour l\'intégration des factures avec le système EBMS du Burundi',
    'description': """
EBMS Connector (Burundi)
========================

Ce module permet l’intégration native d’Odoo avec le système EBMS de l’OBR (Burundi).

Fonctionnalités principales :
- Envoi automatique des factures vers EBMS avec accusé de réception et signature électronique
- Gestion du statut EBMS, de la référence, de la signature et des erreurs
- Annulation de facture côté EBMS (conforme doc OBR)
- Vérification du NIF client via l’API EBMS
- Vérification automatique et manuelle de la signature électronique EBMS (RSA)
- Gestion des mouvements de stock (structure prête à étendre)
- Notifications utilisateur et logs détaillés

Configuration :
1. Installer les dépendances Python requises (cryptography)
2. Configurer les paramètres système Odoo :
   - ebms.api_url : URL de l’API EBMS (envoi facture)
   - ebms.cancel_url : URL de l’API d’annulation EBMS
   - ebms.nif_check_url : URL de vérification NIF EBMS
   - ebms.api_token : Token d’authentification
   - ebms.device_id : Identifiant du système agréé
   - ebms.public_key : Clé publique OBR au format PEM (pour vérification signature)

Sécurité :
- Ne jamais exposer le token ou la clé privée dans les logs ou l’interface
- Limiter l’accès aux actions sensibles (annulation, vérification signature) aux groupes Odoo adéquats
- Changer régulièrement le token et vérifier la clé publique auprès de l’OBR

Documentation complète et exemples d’utilisation dans le README du module.
""",
    'author': 'EBMS Connector Team',
    'website': 'https://www.ebms-connector.com',
    'depends': ['account'],
    'data': [
        
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/invoice_view.xml',
        'views/stock_move_view.xml',
        'views/stock_picking_move_link.xml',
    ],
    # 'demo': [
    #     'data/demo_data.xml',
    # ],
    'assets': {},
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
