# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SpcCompanyApplication(models.Model):
    _name = 'spc.company.application'
    _description = 'SPC Company Application'
    _rec_name = 'reference'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    reference = fields.Char(string='Reference', readonly=True, copy=False, default='New')
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    service_type = fields.Char(string='Service Type')
    current_step = fields.Integer(string='Current Step', default=1)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='draft', string='Status', tracking=True)

    # ── STEP 1: Legal Type ──────────────────────────────────────────
    legal_type = fields.Char(string='Legal Type')
    package_type = fields.Char(string='Package Type')
    fees = fields.Float(string='Total Fees (AED)')

    # ── STEP 2: Business Activities ─────────────────────────────────
    business_activity_ids = fields.Many2many(
        'spc.business.activity',
        'spc_app_activity_rel',
        'application_id', 'activity_id',
        string='Business Activities'
    )

    # ── STEP 3: Company Name ─────────────────────────────────────────
    license_years = fields.Char(string='License Validity (Years)')
    name_reserved = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Name Reserved?')
    reserved_name = fields.Char(string='Reserved Name')
    name_preference_1 = fields.Char(string='Name Preference 1')
    name_preference_2 = fields.Char(string='Name Preference 2')
    name_preference_3 = fields.Char(string='Name Preference 3')
    arabic_translation = fields.Selection([
        ('direct', 'Direct Translation'),
        ('phonetic', 'Phonetic Sound'),
        ('own', 'Own Translation'),
    ], string='Arabic Translation Method')

    # ── STEP 4: Facility ─────────────────────────────────────────────
    facility_type = fields.Selection([
        ('coworking', 'Coworking'),
        ('office', 'Office'),
        ('store', 'Store'),
        ('shell', 'Shell & Core'),
    ], string='Facility Type')
    coworking_location_en = fields.Char(string='Coworking Location (EN)')
    coworking_location_ar = fields.Char(string='Coworking Location (AR)')

    # ── STEP 5: Visa Allocation ──────────────────────────────────────
    visa_count = fields.Integer(string='Number of Visas')

    # ── STEP 6: Shareholders ─────────────────────────────────────────
    shareholder_count = fields.Integer(string='Number of Shareholders')
    shareholder_ids = fields.One2many('spc.app.shareholder', 'application_id', string='Shareholders')
    total_shares = fields.Integer(string='Total Shares')
    value_per_share = fields.Float(string='Value Per Share (AED)')
    total_capital = fields.Float(string='Total Capital (AED)', compute='_compute_total_capital', store=True)

    @api.depends('total_shares', 'value_per_share')
    def _compute_total_capital(self):
        for rec in self:
            rec.total_capital = rec.total_shares * rec.value_per_share

    # ── STEP 7: Managers ─────────────────────────────────────────────
    manager_count = fields.Integer(string='Number of Managers')
    manager_ids = fields.One2many('spc.app.manager', 'application_id', string='Managers')

    # ── STEP 8: Directors ────────────────────────────────────────────
    director_count = fields.Integer(string='Number of Directors')
    director_ids = fields.One2many('spc.app.director', 'application_id', string='Directors')

    # ── STEP 9: UBO ──────────────────────────────────────────────────
    ubo_ids = fields.One2many('spc.app.ubo', 'application_id', string='UBOs')

    # ── STEP 10: Nature of Business ──────────────────────────────────
    annual_turnover = fields.Float(string='Annual Turnover (AED)')
    customer_market_count = fields.Integer(string='Customer Markets Count')
    customer_markets = fields.Text(string='Customer Markets')
    supplier_market_count = fields.Integer(string='Supplier Markets Count')
    supplier_markets = fields.Text(string='Supplier Markets')
    paid_up_capital = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Paid Up Capital?')
    capital_range = fields.Char(string='Capital Range')
    corporate_service_provider = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Corporate Service Provider?')
    has_website = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Has Website?')
    website_url = fields.Char(string='Website URL')
    multinational_group = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Multinational Group?')
    terms_agreed = fields.Boolean(string='Terms Agreed')
    remarks = fields.Text(string='Remarks')

    # ── STEP 11: Corporate Bank Account ──────────────────────────────
    need_bank = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Need Bank Account?')
    bank_provider = fields.Char(string='Preferred Bank')

    # ── STEP 12: Supporting Documents ────────────────────────────────
    document_ids = fields.One2many('spc.app.document', 'application_id', string='Documents')

    # ── Admin Actions ─────────────────────────────────────────────────
    admin_notes = fields.Text(string='Admin Notes')
    rejection_reason = fields.Text(string='Rejection Reason')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', 'New') == 'New':
                vals['reference'] = self.env['ir.sequence'].next_by_code('spc.company.application') or 'New'
        return super().create(vals_list)

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_under_review(self):
        self.write({'state': 'under_review'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Application',
            'res_model': 'spc.rejection.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_application_id': self.id},
        }

    def action_reset_draft(self):
        self.write({'state': 'draft'})


class SpcAppShareholder(models.Model):
    _name = 'spc.app.shareholder'
    _description = 'Application Shareholder'
    _rec_name = 'full_name'

    application_id = fields.Many2one('spc.company.application', ondelete='cascade')
    shareholder_type = fields.Selection([
        ('individual', 'Individual'),
        ('entity', 'Entity'),
    ], string='Type', default='individual')
    is_spc_user = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Existing SPC User?')

    # Individual fields
    first_name = fields.Char(string='First Name')
    last_name = fields.Char(string='Last Name')
    full_name = fields.Char(string='Full Name', compute='_compute_full_name', store=True)
    passport_no = fields.Char(string='Passport Number')
    nationality = fields.Char(string='Nationality')
    dob = fields.Date(string='Date of Birth')
    place_of_birth = fields.Char(string='Place of Birth')
    country_of_birth = fields.Char(string='Country of Birth')
    date_of_issue = fields.Date(string='Passport Issue Date')
    date_of_expiry = fields.Date(string='Passport Expiry Date')
    mobile = fields.Char(string='Mobile')
    email = fields.Char(string='Email')
    address = fields.Text(string='Address')
    city = fields.Char(string='City')
    country = fields.Char(string='Country')
    joining_date = fields.Date(string='Joining Date')
    has_uae_visa = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='UAE Residence Visa?')
    visa_no = fields.Char(string='Resident Visa Number')
    emirates_id = fields.Char(string='Emirates ID')
    uid = fields.Char(string='Unified Number (UID)')
    has_nominee = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Has Nominee?')

    # Entity fields
    entity_name = fields.Char(string='Entity Name')
    entity_name_ar = fields.Char(string='Entity Name (Arabic)')
    entity_reg_no = fields.Char(string='Entity Registration Number')
    entity_country = fields.Char(string='Country of Formation')
    jurisdiction = fields.Char(string='Jurisdiction')
    ownership_type = fields.Char(string='Ownership Type')

    # Share info
    shares_allocated = fields.Integer(string='Shares Allocated')
    share_value = fields.Float(string='Value Per Share')
    total_share_value = fields.Float(string='Total Value', compute='_compute_share_value', store=True)

    @api.depends('first_name', 'last_name', 'entity_name')
    def _compute_full_name(self):
        for rec in self:
            if rec.shareholder_type == 'entity':
                rec.full_name = rec.entity_name or ''
            else:
                rec.full_name = f"{rec.first_name or ''} {rec.last_name or ''}".strip()

    @api.depends('shares_allocated', 'share_value')
    def _compute_share_value(self):
        for rec in self:
            rec.total_share_value = rec.shares_allocated * rec.share_value


class SpcAppManager(models.Model):
    _name = 'spc.app.manager'
    _description = 'Application Manager'
    _rec_name = 'full_name'

    application_id = fields.Many2one('spc.company.application', ondelete='cascade')
    define_from = fields.Selection([
        ('shareholder', 'Shareholder of this entity'),
        ('spc_entity', 'Current shareholder of another entity in SPC FZ'),
        ('new', 'Add new'),
    ], string='Define From')
    full_name = fields.Char(string='Full Name')
    email = fields.Char(string='Email')
    passport_no = fields.Char(string='Passport Number')
    nationality = fields.Char(string='Nationality')
    mobile = fields.Char(string='Mobile')
    has_uae_residence = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='UAE Resident?')
    has_nominee = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Has Nominee?')


class SpcAppDirector(models.Model):
    _name = 'spc.app.director'
    _description = 'Application Director'
    _rec_name = 'full_name'

    application_id = fields.Many2one('spc.company.application', ondelete='cascade')
    define_from = fields.Selection([
        ('shareholder', 'Shareholder of this entity'),
        ('spc_entity', 'Current shareholder of another entity in SPC FZ'),
        ('new', 'Add new'),
    ], string='Define From')
    full_name = fields.Char(string='Full Name')
    email = fields.Char(string='Email')
    passport_no = fields.Char(string='Passport Number')
    nationality = fields.Char(string='Nationality')
    mobile = fields.Char(string='Mobile')
    has_uae_residence = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='UAE Resident?')


class SpcAppUbo(models.Model):
    _name = 'spc.app.ubo'
    _description = 'Application UBO'
    _rec_name = 'full_name'

    application_id = fields.Many2one('spc.company.application', ondelete='cascade')
    full_name = fields.Char(string='Full Name')
    ubo_type = fields.Selection([
        ('individual', 'Individual'),
        ('trust', 'Trust'),
    ], string='UBO Type')
    passport_no = fields.Char(string='Passport Number')
    nationality = fields.Char(string='Nationality')
    has_uae_residence = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='UAE Resident?')
    stakeholder_type = fields.Selection([
        ('shareholder', 'Shareholder'),
        ('manager', 'Manager'),
        ('director', 'Director'),
        ('voting', 'Voting Rights'),
    ], string='Stakeholder Type')


class SpcAppDocument(models.Model):
    _name = 'spc.app.document'
    _description = 'Application Document'

    application_id = fields.Many2one('spc.company.application', ondelete='cascade')
    doc_type = fields.Char(string='Document Type')
    related_to = fields.Char(string='Related To')  # shareholder, manager, etc.
    file = fields.Binary(string='File', attachment=True)
    filename = fields.Char(string='File Name')
    upload_date = fields.Datetime(default=fields.Datetime.now)
    step = fields.Integer(string='Step')


class SpcRejectionWizard(models.TransientModel):
    _name = 'spc.rejection.wizard'
    _description = 'Rejection Wizard'

    application_id = fields.Many2one('spc.company.application')
    reason = fields.Text(string='Rejection Reason', required=True)

    def action_confirm_reject(self):
        self.application_id.write({
            'state': 'rejected',
            'rejection_reason': self.reason,
        })
