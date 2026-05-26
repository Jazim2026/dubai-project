# -*- coding: utf-8 -*-
from odoo import api, fields, models

MEDIA_ACTIVITIES = [
    ('books_issue_import_dist', 'License for Issuing, Importing, and Distributing Books'),
    ('newspapers_magazines', 'License for Distributing and Publishing Newspapers, Magazines, and Periodicals'),
    ('books_sell', 'License for Selling Books and Publications'),
    ('sound_recordings', 'License for Distributing, Publishing, and Trading Sound Recordings and Audio Media'),
]


class SpcNmaMediaLicense(models.Model):
    _name = 'spc.nma.media.license'
    _description = 'SPC NMA Media License'
    _order = 'id desc'
    _rec_name = 'name'

    name = fields.Char(string='Reference', readonly=True, default='New', copy=False, index=True)
    license_type = fields.Selection([
        ('new', 'New'),
        ('renewal', 'Renewal'),
        ('amend', 'Amend'),
        ('cancellation', 'Cancellation'),
    ], string='License Type', required=True, default='new')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('documents_approved', 'Documents Approved'),
        ('payment_approved', 'Payment Approved'),
        ('complaints_approved', 'Complaints Approved'),
        ('under_process', 'Under Process'),
        ('completed', 'Completed'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft')

    partner_id = fields.Many2one('res.partner', string='Applicant')
    approved_company_id = fields.Many2one('spc.approved.company', string='Company')
    submission_date = fields.Datetime(string='Submission Date', readonly=True)

    # Step 1
    company_name = fields.Char(string='Company Name')
    manager_name = fields.Char(string='Manager (Selected)')
    manager_first_name = fields.Char(string='Manager First Name')
    manager_last_name = fields.Char(string='Manager Last Name')
    manager_dob = fields.Date(string='Manager Date of Birth')
    step1_remarks = fields.Text(string='Remarks')

    # Step 2
    num_activities = fields.Selection([
        ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'),
    ], string='Number of Activities')
    activity_1 = fields.Selection(MEDIA_ACTIVITIES, string='Activity 1')
    activity_2 = fields.Selection(MEDIA_ACTIVITIES, string='Activity 2')
    activity_3 = fields.Selection(MEDIA_ACTIVITIES, string='Activity 3')
    activity_4 = fields.Selection(MEDIA_ACTIVITIES, string='Activity 4')
    activity_5 = fields.Selection(MEDIA_ACTIVITIES, string='Activity 5')
    business_plan = fields.Text(string='Business Plan')

    # Step 3
    shareholder_name = fields.Char(string='Shareholder Name')
    shareholder_uae_resident = fields.Char(string='UAE Resident', default='no')
    doc_mro_form = fields.Binary(string='MRO Requisition Form', attachment=True)
    doc_mro_form_name = fields.Char(string='MRO Form Filename')
    doc_photo = fields.Binary(string='Shareholder Photo', attachment=True)
    doc_photo_name = fields.Char(string='Photo Filename')
    doc_emirates_id = fields.Binary(string='Emirates ID', attachment=True)
    doc_emirates_id_name = fields.Char(string='Emirates ID Filename')
    doc_power_of_attorney = fields.Binary(string='Power of Attorney', attachment=True)
    doc_power_of_attorney_name = fields.Char(string='Power of Attorney Filename')
    doc_request_form = fields.Binary(string='Request Form', attachment=True)
    doc_request_form_name = fields.Char(string='Request Form Filename')

    # Step 4
    declaration_accepted = fields.Boolean(string='Declaration Accepted')

    # Step 5
    additional_remarks = fields.Text(string='Additional Remarks')

    total_amount = fields.Float(string='Total Amount (AED)', default=535.0)
    current_step = fields.Integer(string='Current Step', default=1)
    started_date = fields.Datetime(string='Started Date', readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('spc.nma.media.license') or 'New'
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

