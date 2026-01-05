# -*- coding: utf-8 -*-

from odoo import models, fields

class ResCompanyInherit(models.Model):
    _inherit = 'res.company'

    x_fiscal_center = fields.Char(string='Centre Fiscal')
    x_activity_sector = fields.Char(string='Secteur d’activité')
    x_legal_form = fields.Char(string='Forme Juridique')
