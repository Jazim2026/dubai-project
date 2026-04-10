# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SpcServiceRequest(models.Model):
    _name = 'spc.service.request'
    _description = 'SPC Service Request'
    _rec_name = 'reference'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    reference = fields.Char(string='Reference', readonly=True, copy=False, default='New')
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    
    # Service Category
    service_category = fields.Selection([
        ('company_formation', 'Company Formation'),
        ('establishment_card', 'Establishment Card & E-Channel'),
        ('business_license', 'Business License'),
        ('corporate_letters', 'Corporate Letters'),
        ('name_reservation', 'Name Reservation'),
        ('pre_approval', 'Pre-Approval'),
        ('nma_media_license', 'NMA Media License'),
        ('nma_permit', 'NMA Permit'),
    ], string='Service Category', required=True)

    # Service Type
    service_type = fields.Selection([
        # Company Formation
        ('license_reissue', 'License Reissue'),
        ('renewal_only', 'Renewal Only'),
        ('renewal_amendment', 'Renewal with Amendment'),
        ('amendment', 'Amendment'),
        ('visa_allocation_amendment', 'Visa Allocation Amendment'),
        ('cancellation', 'Cancellation'),
        ('certify', 'Certify'),
        # Establishment Card
        ('ec_new', 'Establishment Card - New'),
        ('ec_renewal', 'Establishment Card - Renewal'),
        ('ec_amendment', 'Establishment Card - Amendment'),
        ('ec_cancellation', 'Establishment Card - Cancellation'),
        # Business License
        ('bl_ultimate', 'Ultimate'),
        ('bl_publishing', 'Publishing'),
        ('bl_epublishing', 'E-Publishing'),
        ('bl_instant_publishing', 'Instant License - Publishing'),
        ('bl_instant_epublishing', 'Instant License - E-Publishing'),
        ('bl_instant_ultimate', 'Instant License - Ultimate'),
        # Corporate Letters
        ('cl_noc', 'No Objection Certificate'),
        ('cl_incumbency', 'Certificate of Incumbency'),
        ('cl_good_standing', 'Certificate of Good Standing'),
        ('cl_other', 'Other'),
        # Name Reservation
        ('nr_new', 'Name Reservation - New'),
        # Pre Approval
        ('pa_new', 'Pre-Approval - New'),
        # NMA Media License
        ('nma_new', 'NMA Media License - New'),
        ('nma_renewal', 'NMA Media License - Renewal'),
        ('nma_amend', 'NMA Media License - Amendment'),
        ('nma_cancel', 'NMA Media License - Cancellation'),
        # NMA Permit
        ('permit_printing', 'Printing Permit'),
        ('permit_trading', 'Trading Permit'),
        ('permit_text', 'Text Permit'),
        ('permit_regulatory', 'Regulatory Entry Permit'),
    ], string='Service Type', required=True)

    # Status
    state = fields.Selection([
        ('draft', 'Unsubmitted'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('doc_pending', 'Documents Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ], default='draft', string='Status')

    # Dates
    submission_date = fields.Datetime(string='Submission Date')
    estimated_completion = fields.Date(string='Estimated Completion')

    # Fees
    fees = fields.Float(string='Fees (AED)')

    # Company details
    company_name = fields.Char(string='Company Name')
    license_number = fields.Char(string='License Number')
    formation_number = fields.Char(string='Formation Number')
    idn_number = fields.Char(string='IDN Number')

    # Business Activities
    business_activity_ids = fields.Many2many(
        'spc.business.activity',
        string='Business Activities'
    )

    # Corporate Letter specific
    corporate_letter_type = fields.Selection([
        ('noc', 'No Objection Certificate'),
        ('incumbency', 'Certificate of Incumbency'),
        ('good_standing', 'Certificate of Good Standing'),
        ('other', 'Other'),
    ], string='Corporate Letter Type')

    # Manager details (NMA)
    manager_first_name = fields.Char(string='Manager First Name')
    manager_last_name = fields.Char(string='Manager Last Name')
    manager_dob = fields.Date(string='Manager Date of Birth')

    # Permit type
    permit_type = fields.Selection([
        ('printing', 'Printing Permit'),
        ('trading', 'Trading Permit'),
        ('text', 'Text Permit'),
        ('regulatory', 'Regulatory Entry Permit'),
    ], string='Permit Type')

    # Declaration
    declaration_accepted = fields.Boolean(string='Declaration Accepted')

    # Setup New Company - Step fields
    legal_type = fields.Selection([
        ('fze', 'Free Zone Establishment'),
        ('fzc', 'Free Zone Company'),
        ('branch', 'Branch'),
    ], string='Legal Type')
    package_type = fields.Selection([
        ('standard', 'Standard'),
        ('publishing', 'Publishing'),
        ('epublishing', 'E-Publishing'),
    ], string='Package Type')
    branch_location = fields.Selection([
        ('inside_uae', 'Inside UAE'),
        ('outside_uae', 'Outside UAE'),
    ], string='Branch Location')
    parent_company_name = fields.Char(string='Parent Company Name')
    parent_company_name_arabic = fields.Char(string='Parent Company Name (Arabic)')
    emirate_of_company = fields.Char(string='Emirate of Company')
    license_issuing_authority = fields.Char(string='License Issuing Authority')
    company_activity_description = fields.Text(string='Company Activity Description')
    br_acknowledgement = fields.Boolean(string='BR Acknowledgement')
    current_step = fields.Integer(string='Current Step', default=1)
    products_services = fields.Text(string='List of Products/Services')

    # Remarks
    remarks = fields.Text(string='Remarks')

    # Feedback
    feedback = fields.Text(string='Feedback')
    task_status = fields.Char(string='Task Status')

    # Documents
    document_ids = fields.One2many('spc.service.document', 'request_id', string='Documents')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', 'New') == 'New':
                vals['reference'] = self.env['ir.sequence'].next_by_code('spc.service.request') or 'New'
        return super().create(vals_list)

    def action_submit(self):
        self.write({
            'state': 'submitted',
            'submission_date': fields.Datetime.now(),
        })

    def action_under_review(self):
        self.write({'state': 'under_review'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_reject(self):
        self.write({'state': 'rejected'})


class SpcBusinessActivity(models.Model):
    _name = 'spc.business.activity'
    _description = 'SPC Business Activity'
    _rec_name = 'name'

    name = fields.Char(string='Activity Name', required=True)
    code = fields.Char(string='Code')
    category = fields.Selection([
        ('publishing_media', 'Publishing and Media'),
        ('wholesale_retail', 'Wholesale and Retail'),
        ('services_consultancy', 'Services and Consultancy'),
        ('electronic_publishing', 'Electronic Publishing'),
        ('real_publishing', 'Real Publishing'),
    ], string='Category')
    division = fields.Char(string='Division')
    active = fields.Boolean(default=True)


class SpcServiceDocument(models.Model):
    _name = 'spc.service.document'
    _description = 'SPC Service Document'

    request_id = fields.Many2one('spc.service.request', string='Request', ondelete='cascade')
    doc_type = fields.Char(string='Document Type')
    file = fields.Binary(string='File')
    filename = fields.Char(string='File Name')
    upload_date = fields.Datetime(default=fields.Datetime.now)
