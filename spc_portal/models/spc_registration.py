# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SpcRegistration(models.Model):
    _name = 'spc.registration'
    _description = 'SPC Portal Registration'
    _rec_name = 'email'

    email = fields.Char(string='Email', required=True)
    partner_type = fields.Selection([
        ('customer', 'Customer'),
        ('company', 'Company'),
    ], string='Type', required=True, default='customer')

    # Customer
    first_name = fields.Char(string='First Name')
    last_name = fields.Char(string='Last Name')
    phone = fields.Char(string='Phone')
    nationality = fields.Many2one('res.country', string='Nationality')

    # Company
    company_name = fields.Char(string='Company Name')
    company_reg_no = fields.Char(string='Registration Number')
    trade_license = fields.Char(string='Trade License')
    industry = fields.Selection([
        ('trading', 'Trading'),
        ('manufacturing', 'Manufacturing'),
        ('services', 'Services'),
        ('logistics', 'Logistics'),
        ('technology', 'Technology'),
        ('other', 'Other'),
    ], string='Industry')

    # Common
    address = fields.Text(string='Address')
    country_id = fields.Many2one('res.country', string='Country')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('otp_verified', 'OTP Verified'),
        ('registered', 'Registered'),
    ], default='draft', string='State')

    partner_id = fields.Many2one('res.partner', string='Partner')
    document_ids = fields.One2many('spc.document', 'registration_id', string='Documents')
    document_count = fields.Integer(compute='_compute_doc_count', string='Documents')

    @api.depends('document_ids')
    def _compute_doc_count(self):
        for rec in self:
            rec.document_count = len(rec.document_ids)

    def action_create_partner(self):
        self.ensure_one()
        if self.partner_type == 'company':
            name = self.company_name or self.email
            is_company = True
        else:
            name = f"{self.first_name or ''} {self.last_name or ''}".strip() or self.email
            is_company = False

        partner = self.env['res.partner'].create({
            'name': name,
            'email': self.email,
            'phone': self.phone,
            'is_company': is_company,
            'country_id': self.country_id.id,
            'customer_rank': 1,
        })
        self.partner_id = partner
        self.state = 'registered'
        return partner

    def action_view_documents(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'spc.document',
            'view_mode': 'tree,form',
            'domain': [('registration_id', '=', self.id)],
            'context': {'default_registration_id': self.id},
        }
