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
        ('under_review', 'Under Review'), ('approved', 'Approved'),
    ], default='draft', string='Status')
    partner_id = fields.Many2one('res.partner', string='Applicant')
    submission_date = fields.Datetime(string='Submission Date', readonly=True)
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
