# -*- coding: utf-8 -*-
from odoo import models, fields


class SpcDocument(models.Model):
    _name = 'spc.document'
    _description = 'SPC Portal Document'
    _rec_name = 'doc_type'

    registration_id = fields.Many2one('spc.registration', string='Registration', required=True, ondelete='cascade')
    email = fields.Char(related='registration_id.email', string='Email', store=True)

    doc_type = fields.Selection([
        ('passport', 'Passport / Emirates ID'),
        ('trade_license', 'Trade License'),
        ('company_docs', 'Company Documents'),
        ('application_form', 'Application Form'),
        ('contract', 'Contract / Agreement'),
    ], string='Document Type', required=True)

    file = fields.Binary(string='Upload File', required=True)
    filename = fields.Char(string='File Name')
    note = fields.Text(string='Notes')

    state = fields.Selection([
        ('uploaded', 'Uploaded'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='uploaded', string='Status')

    upload_date = fields.Datetime(string='Upload Date', default=fields.Datetime.now)
