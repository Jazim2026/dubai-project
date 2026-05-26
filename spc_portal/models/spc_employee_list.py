# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SpcEmployeeList(models.Model):
    _name = 'spc.employee.list'
    _description = 'SPC Employee List'
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
    partner_id = fields.Many2one('res.partner', string='Applicant')
    approved_company_id = fields.Many2one('spc.approved.company', string='Company')
    submission_date = fields.Datetime(string='Submission Date', readonly=True)
    # Request Tracking
    current_step = fields.Integer(string='Current Step', default=1)
    started_date = fields.Datetime(string='Started Date', readonly=True)
    total_amount = fields.Float(string='Total Amount (AED)', default=385.0)

    # Declaration
    declaration_accepted = fields.Boolean(string='Declaration Accepted')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('spc.employee.list') or 'New'
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

