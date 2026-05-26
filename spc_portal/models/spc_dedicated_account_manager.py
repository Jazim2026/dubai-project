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
        ('under_review', 'Under Review'), 
        ('documents_approved', 'Documents Approved'),
        ('payment_approved', 'Payment Approved'),
        ('complaints_approved', 'Complaints Approved'),
        ('under_process', 'Under Process'),
        ('completed', 'Completed'),
        ('approved', 'Approved'),
    ], default='draft', string='Status')
    partner_id = fields.Many2one('res.partner', string='Customer')
    approved_company_id = fields.Many2one('spc.approved.company', string='Company')
    submission_date = fields.Datetime(string='Submission Date', readonly=True)
    # Request Tracking
    current_step = fields.Integer(string='Current Step', default=1)
    started_date = fields.Datetime(string='Started Date', readonly=True)
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

    def action_approve_documents(self):
        self.state = 'documents_approved'
    def action_approve_payment(self):
        self.state = 'payment_approved'
    def action_approve_complaints(self):
        self.state = 'complaints_approved'
    def action_under_process(self):
        self.state = 'under_process'
    def action_completed(self):
        self.state = 'completed'

    def action_send_notification(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Send Notification',
            'res_model': 'spc.send.notification.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_source_model': self._name,
                'default_source_id': self.id,
            }
        }

