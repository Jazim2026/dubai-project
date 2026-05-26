# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SpcFacilityManagement(models.Model):
    _name = 'spc.facility.management'
    _description = 'SPC Facility Management'
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
    total_amount = fields.Float(string='Total Amount (AED)', default=0.0)

    # Step 1 - Complaint Details
    complaint_category = fields.Selection([
        ('electrical', 'Electrical'),
        ('air_conditioning', 'Air Conditioning'),
        ('fire_alarm', 'Fire Alarm/Fighting'),
        ('general', 'General'),
    ], string='Complaint Category')
    incident_type = fields.Char(string='Incident Type')
    office_number = fields.Char(string='Office Number')
    contact_name = fields.Char(string='Name of Contact')
    contact_number = fields.Char(string='Contact Number')
    complaint_description = fields.Text(string='Description of Complaint')
    doc_image = fields.Binary(string='Upload Image', attachment=True)
    doc_image_name = fields.Char(string='Image Filename')

    # Declaration
    declaration_accepted = fields.Boolean(string='Declaration Accepted')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('spc.facility.management') or 'New'
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
