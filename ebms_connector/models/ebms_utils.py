import requests
from odoo import api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

def ebms_login(env):
    """
    Effectue un appel à l'API EBMS /login/ pour obtenir un token Bearer.
    Les identifiants sont lus dans les paramètres système Odoo.
    Le token obtenu est stocké dans ebms.api_token (paramètre système).
    """
    url = env['ir.config_parameter'].sudo().get_param('ebms.login_url')
    username = env['ir.config_parameter'].sudo().get_param('ebms.api_username')
    password = env['ir.config_parameter'].sudo().get_param('ebms.api_password')
    if not url or not username or not password:
        raise UserError(_('Paramètres EBMS manquants (login_url, username ou password).'))
    payload = {
        'username': username,
        'password': password,
    }
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            resp_json = response.json()
            if resp_json.get('success') and resp_json.get('result', {}).get('token'):
                token = resp_json['result']['token']
                env['ir.config_parameter'].sudo().set_param('ebms.api_token', token)
                _logger.info('Nouveau token EBMS obtenu et stocké.')
                return token
            else:
                msg = resp_json.get('msg', 'Erreur lors de l\'authentification EBMS.')
                raise UserError(_('Erreur login EBMS: %s') % msg)
        else:
            raise UserError(_('Erreur HTTP login EBMS: %s') % response.text)
    except Exception as e:
        raise UserError(_('Exception lors du login EBMS: %s') % str(e))
