# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SpcChangeOfStatus(models.Model):
    _name = 'spc.change.of.status'
    _description = 'SPC Change of Status'
    _order = 'id desc'
    _rec_name = 'name'

    name = fields.Char(string='Reference', readonly=True, default='New', copy=False)
    state = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'),
        ('under_review', 'Under Review'), ('approved', 'Approved'),
    ], default='draft', string='Status')
    partner_id = fields.Many2one('res.partner', string='Applicant')
    submission_date = fields.Datetime(string='Submission Date', readonly=True)
    total_amount = fields.Float(string='Total Amount (AED)', default=710.0)

    # Step 1 - Application Details
    applicant_name = fields.Char(string='Applicant')
    visa_status = fields.Selection([
        ('cancelled', 'Cancelled resident visa'),
        ('valid', 'Valid visa'),
    ], string='Current Visa Status')
    remarks = fields.Text(string='Remarks')

    # Documents - Cancelled visa
    doc_cancelled_visa = fields.Binary(string='Cancelled Resident Visa Document', attachment=True)
    doc_cancelled_visa_name = fields.Char(string='Cancelled Visa Filename')

    # Documents - Valid visa
    doc_valid_visa = fields.Binary(string='Valid Visa Document', attachment=True)
    doc_valid_visa_name = fields.Char(string='Valid Visa Filename')

    # Step 2 - Applicant Information
    first_name = fields.Char(string='First Name')
    last_name = fields.Char(string='Last Name')

    # Step 3 - Declaration
    declaration_accepted = fields.Boolean(string='Declaration Accepted')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('spc.change.of.status') or 'New'
        return super().create(vals)
