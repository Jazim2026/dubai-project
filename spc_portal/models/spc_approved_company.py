# -*- coding: utf-8 -*-
from odoo import models, fields, api

class SpcApprovedCompany(models.Model):
    _name = 'spc.approved.company'
    _description = 'SPC Approved Company'
    _rec_name = 'company_name'

    company_name = fields.Char(string='Company Name', required=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    application_id = fields.Many2one('spc.company.application', string='Application', ondelete='set null')
    active = fields.Boolean(string='Active', default=True)
    state = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ], string='Status', default='active')
