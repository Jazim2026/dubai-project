# -*- coding: utf-8 -*-
from odoo import api, fields, models

class SpcDedicatedAccountManager(models.Model):
    _name = 'spc.dedicated.account.manager'
    _description = 'SPC Dedicated Account Manager'
    _order = 'id desc'
    _rec_name = 'name'

    name = fields.Char(string='Reference', readonly=True, default='New', copy=False)
    state = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'),
        ('under_review', 'Under Review'), ('approved', 'Approved'),
    ], default='draft', string='Status')
    partner_id = fields.Many2one('res.partner', string='Customer')
    submission_date = fields.Datetime(string='Submission Date', readonly=True)
    total_amount = fields.Float(string='Total Amount (AED)', default=3000.0)

    # Step 1 - Point of Contact
    is_existing_stakeholder = fields.Selection([
        ('yes', 'Yes'), ('no', 'No')
    ], string='Is Existing Stakeholder?')
    employee_list = fields.Char(string='Employee List')
    first_name = fields.Char(string='First Name')
    last_name = fields.Char(string='Last Name')
    contact_number = fields.Char(string='Contact Number')
    email = fields.Char(string='Email')
    designation = fields.Char(string='Designation')
    language_preference = fields.Char(string='Language of Preference')

    # Step 2 - DAM Details
    number_of_stakeholders = fields.Selection(
        [(str(i), str(i)) for i in range(1, 11)],
        string='Number of Stakeholders'
    )

    # Step 3 - Subscription Duration
    number_of_years = fields.Selection(
        [(str(i), f'{i} Year{"s" if i > 1 else ""}') for i in range(1, 11)],
        string='Number of Years'
    )

    # Declaration
    declaration_accepted = fields.Boolean(string='Declaration Accepted')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('spc.dedicated.account.manager') or 'New'
        return super().create(vals)
