from odoo import models, fields, api

class SpcLicenseReissue(models.Model):
    _name = 'spc.license.reissue'
    _description = 'SPC License Reissue Application'
    _rec_name = 'reference'
    _order = 'create_date desc'

    reference = fields.Char(string='Reference', readonly=True, default='New')
    customer_id = fields.Many2one('res.partner', string='Customer')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='submitted')

    # Step 1: IDN Details
    idn_company_id = fields.Many2one('res.partner', string='IDN Company')
    idn_number = fields.Char(string='IDN Number')

    # Step 2: Legal Type
    legal_type = fields.Selection([
        ('fze', 'Free Zone Establishment'),
        ('fzc', 'Free Zone Company'),
        ('branch', 'Branch'),
    ], string='Legal Type')
    package_type = fields.Char(string='Package Type')

    # Step 3: Business Activities
    business_activity_ids = fields.Many2many(
        'spc.business.activity',
        'spc_lr_activity_rel',
        'lr_id', 'activity_id',
        string='Business Activities'
    )
    activity_names = fields.Text(string='Activity Names')

    # Payment
    fee = fields.Float(string='Fee', default=0.0)
    payment_method = fields.Char(string='Payment Method')
    payment_status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ], string='Payment Status', default='pending')

    admin_notes = fields.Text(string='Admin Notes')

    @api.model
    def create(self, vals):
        if vals.get('reference', 'New') == 'New':
            vals['reference'] = self.env['ir.sequence'].next_by_code('spc.license.reissue') or 'LR/0001'
        return super().create(vals)

    def action_approve(self):
        self.state = 'approved'

    def action_reject(self):
        self.state = 'rejected'

    def action_under_review(self):
        self.state = 'under_review'


class SpcRenewal(models.Model):
    _name = 'spc.renewal'
    _description = 'SPC Renewal Application'
    _rec_name = 'reference'
    _order = 'create_date desc'

    reference = fields.Char(string='Reference', readonly=True, default='New')
    customer_id = fields.Many2one('res.partner', string='Customer')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='submitted')

    # Step 1: Choose License
    license_company_id = fields.Many2one('res.partner', string='Company')
    license_company_name = fields.Char(string='Company Name')

    # Step 2: Legal Details
    legal_type = fields.Selection([
        ('fze', 'Free Zone Establishment'),
        ('fzc', 'Free Zone Company'),
        ('branch', 'Branch'),
    ], string='Legal Type')
    package_type = fields.Char(string='Package Type')

    # Step 3: Business Activities
    business_activity_ids = fields.Many2many(
        'spc.business.activity',
        'spc_renewal_activity_rel',
        'renewal_id', 'activity_id',
        string='Business Activities'
    )
    activity_names = fields.Text(string='Activity Names')

    # Step 4: Application Details
    license_validity = fields.Char(string='License Validity (Years)')
    facility_type = fields.Char(string='Facility Type')
    visa_allocation = fields.Integer(string='Visa Allocation')
    document_name = fields.Char(string='Document Name')
    document_file = fields.Binary(string='Document', attachment=True)
    document_filename = fields.Char(string='Document Filename')

    # Payment
    fee = fields.Float(string='Fee', default=0.0)
    payment_method = fields.Char(string='Payment Method')
    payment_status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ], string='Payment Status', default='pending')

    admin_notes = fields.Text(string='Admin Notes')

    @api.model
    def create(self, vals):
        if vals.get('reference', 'New') == 'New':
            vals['reference'] = self.env['ir.sequence'].next_by_code('spc.renewal') or 'RN/0001'
        return super().create(vals)

    def action_approve(self):
        self.state = 'approved'

    def action_reject(self):
        self.state = 'rejected'

    def action_under_review(self):
        self.state = 'under_review'


class SpcRenewalAmendment(models.Model):
    _name = 'spc.renewal.amendment'
    _description = 'SPC Renewal with Amendment'
    _rec_name = 'reference'
    _order = 'create_date desc'

    reference = fields.Char(string='Reference', readonly=True, default='New')
    customer_id = fields.Many2one('res.partner', string='Customer')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='submitted')

    # Step 1: Company
    company_id = fields.Many2one('res.partner', string='Company')
    company_name = fields.Char(string='Company Name')

    # Step 2: Renewal Type
    renewal_type = fields.Selection([
        ('with_amendment', 'Renewal with Amendment'),
    ], string='Renewal Type', default='with_amendment')
    amendment_types = fields.Char(string='Amendment Types')
    board_resolution_file = fields.Binary(string='Board Resolution', attachment=True)
    board_resolution_filename = fields.Char(string='Board Resolution Filename')
    acknowledgement = fields.Boolean(string='Acknowledgement Accepted')

    # Step 3: Legal Type
    legal_type = fields.Selection([
        ('fze', 'Free Zone Establishment'),
        ('fzc', 'Free Zone Company'),
        ('branch', 'Branch'),
    ], string='Legal Type')
    package_type = fields.Char(string='Package Type')

    # Step 4: Business Activities
    business_activity_ids = fields.Many2many(
        'spc.business.activity',
        'spc_ra_activity_rel',
        'ra_id', 'activity_id',
        string='Business Activities'
    )
    activity_names = fields.Text(string='Activity Names')

    # Step 5: Shareholders
    shareholder_count = fields.Integer(string='Number of Shareholders')
    total_shares = fields.Integer(string='Total Shares')
    value_per_share = fields.Float(string='Value Per Share (AED)')
    total_capital = fields.Float(string='Total Capital (AED)')
    shareholder_ids = fields.One2many('spc.ra.shareholder', 'ra_id', string='Shareholders')

    # Step 6: Managers
    manager_count = fields.Integer(string='Number of Managers')
    manager_ids = fields.One2many('spc.ra.manager', 'ra_id', string='Managers')

    # Step 7: Directors
    director_count = fields.Integer(string='Number of Directors')
    director_ids = fields.One2many('spc.ra.director', 'ra_id', string='Directors')

    # Step 8: UBO
    ubo_ids = fields.One2many('spc.ra.ubo', 'ra_id', string='UBOs')

    # Step 9: Nature of Business
    annual_turnover = fields.Float(string='Annual Turnover (AED)')
    customer_markets = fields.Text(string='Customer Markets')
    supplier_markets = fields.Text(string='Supplier Markets')
    paid_up_capital = fields.Char(string='Paid Up Capital')
    capital_range = fields.Char(string='Capital Range')
    has_website = fields.Char(string='Has Website')
    website_url = fields.Char(string='Website URL')
    multinational_group = fields.Char(string='Multinational Group')

    # Step 10: Documents
    document_ids = fields.One2many('spc.ra.document', 'ra_id', string='Documents')

    # Payment
    fee = fields.Float(string='Fee', default=0.0)
    payment_method = fields.Char(string='Payment Method')
    payment_status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ], string='Payment Status', default='pending')

    admin_notes = fields.Text(string='Admin Notes')

    @api.model
    def create(self, vals):
        if vals.get('reference', 'New') == 'New':
            vals['reference'] = self.env['ir.sequence'].next_by_code('spc.renewal.amendment') or 'RA/0001'
        return super().create(vals)

    def action_approve(self):
        self.state = 'approved'

    def action_reject(self):
        self.state = 'rejected'

    def action_under_review(self):
        self.state = 'in_progress'


class SpcRaShareholder(models.Model):
    _name = 'spc.ra.shareholder'
    _description = 'RA Shareholder'

    ra_id = fields.Many2one('spc.renewal.amendment', string='RA Application', ondelete='cascade')
    shareholder_type = fields.Char(string='Type', default='individual')
    full_name = fields.Char(string='Full Name')
    first_name = fields.Char(string='First Name')
    last_name = fields.Char(string='Last Name')
    passport_no = fields.Char(string='Passport Number')
    nationality = fields.Char(string='Nationality')
    dob = fields.Date(string='Date of Birth')
    mobile = fields.Char(string='Mobile')
    email = fields.Char(string='Email')
    address = fields.Text(string='Address')
    city = fields.Char(string='City')
    country = fields.Char(string='Country')
    has_uae_visa = fields.Char(string='UAE Residence Visa')
    visa_no = fields.Char(string='Visa Number')
    shares_allocated = fields.Integer(string='Shares Allocated')
    entity_name = fields.Char(string='Entity Name')
    entity_reg_no = fields.Char(string='Entity Registration Number')


class SpcRaManager(models.Model):
    _name = 'spc.ra.manager'
    _description = 'RA Manager'

    ra_id = fields.Many2one('spc.renewal.amendment', string='RA Application', ondelete='cascade')
    define_from = fields.Char(string='Defined From')
    sh_val = fields.Char(string='Selected Shareholder')
    spc_email = fields.Char(string='SPC Email')
    spc_pass = fields.Char(string='SPC Passport/Reg No')
    full_name = fields.Char(string='Full Name')
    first_name = fields.Char(string='First Name')
    last_name = fields.Char(string='Last Name')
    passport_no = fields.Char(string='Passport Number')
    nationality = fields.Char(string='Nationality')
    email = fields.Char(string='Email')
    mobile = fields.Char(string='Mobile')
    has_uae_residence = fields.Char(string='UAE Residence')
    visa_no = fields.Char(string='Visa Number')
    eid_no = fields.Char(string='Emirates ID')
    uid = fields.Char(string='UID')
    dob = fields.Char(string='Date of Birth')


class SpcRaDirector(models.Model):
    _name = 'spc.ra.director'
    _description = 'RA Director'

    ra_id = fields.Many2one('spc.renewal.amendment', string='RA Application', ondelete='cascade')
    define_from = fields.Char(string='Defined From')
    sh_val = fields.Char(string='Selected Shareholder')
    spc_email = fields.Char(string='SPC Email')
    spc_pass = fields.Char(string='SPC Passport/Reg No')
    full_name = fields.Char(string='Full Name')
    first_name = fields.Char(string='First Name')
    last_name = fields.Char(string='Last Name')
    passport_no = fields.Char(string='Passport Number')
    nationality = fields.Char(string='Nationality')
    email = fields.Char(string='Email')
    mobile = fields.Char(string='Mobile')
    has_uae_residence = fields.Char(string='UAE Residence')
    visa_no = fields.Char(string='Visa Number')
    eid_no = fields.Char(string='Emirates ID')
    uid = fields.Char(string='UID')


class SpcRaUbo(models.Model):
    _name = 'spc.ra.ubo'
    _description = 'RA UBO'

    ra_id = fields.Many2one('spc.renewal.amendment', string='RA Application', ondelete='cascade')
    define_from = fields.Char(string='Defined From')
    sh_val = fields.Char(string='Selected Shareholder')
    spc_email = fields.Char(string='SPC Email')
    spc_pass = fields.Char(string='SPC Passport/Reg No')
    work_entity = fields.Char(string='Work Entity Name')
    work_addr = fields.Text(string='Work Entity Address')
    full_name = fields.Char(string='Full Name')
    ubo_type = fields.Char(string='Type', default='individual')
    first_name = fields.Char(string='First Name')
    last_name = fields.Char(string='Last Name')
    nationality = fields.Char(string='Nationality')
    stakeholder_type = fields.Char(string='Stakeholder Type')
    has_uae_residence = fields.Char(string='UAE Residence')
    date_of_shares = fields.Char(string='Date of Obtaining Shares')
    date_of_ownership = fields.Char(string='Date of Ownership')
    voting_rights = fields.Char(string='Voting Rights')


class SpcRaDocument(models.Model):
    _name = 'spc.ra.document'
    _description = 'RA Supporting Document'

    ra_id = fields.Many2one('spc.renewal.amendment', string='RA Application', ondelete='cascade')
    stage = fields.Integer(string='Stage')
    document_type = fields.Char(string='Document Type')
    related_to = fields.Char(string='Related To')
    file_name = fields.Char(string='File Name')
    file_data = fields.Binary(string='File', attachment=True)
    uploaded_on = fields.Datetime(string='Uploaded On', default=fields.Datetime.now)


class SpcAmendment(models.Model):
    _name = 'spc.amendment'
    _description = 'SPC Amendment Application'
    _rec_name = 'reference'
    _order = 'create_date desc'

    reference = fields.Char(string='Reference', readonly=True, default='New')
    customer_id = fields.Many2one('res.partner', string='Customer')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='submitted')
    company_id = fields.Many2one('res.partner', string='Company')
    company_name = fields.Char(string='Company Name')
    amendment_types = fields.Char(string='Amendment Types')
    board_resolution_file = fields.Binary(string='Board Resolution', attachment=True)
    board_resolution_filename = fields.Char(string='Board Resolution Filename')
    acknowledgement = fields.Boolean(string='Acknowledgement Accepted')
    annual_turnover = fields.Float(string='Annual Turnover (AED)')
    customer_markets = fields.Text(string='Customer Markets')
    supplier_markets = fields.Text(string='Supplier Markets')
    paid_up_capital = fields.Char(string='Paid Up Capital')
    capital_range = fields.Char(string='Capital Range')
    has_website = fields.Char(string='Has Website')
    website_url = fields.Char(string='Website URL')
    multinational_group = fields.Char(string='Multinational Group')
    # Formation Package
    fp_activity_change = fields.Char(string='Activity Change on E-Card')
    fp_shareholder_change = fields.Char(string='Shareholder Change on E-Card')
    fp_name_change = fields.Char(string='Company Name Change on E-Card')
    # Legal Type
    legal_type = fields.Char(string='Legal Type')
    package_type = fields.Char(string='Package Type')
    # Business Activities
    business_activity_ids = fields.Many2many(
        'spc.business.activity', 'spc_amd_activity_rel', 'amd_id', 'activity_id',
        string='Business Activities'
    )
    activity_names = fields.Text(string='Activity Names')
    # Shareholders
    shareholder_count = fields.Integer(string='Number of Shareholders')
    shareholder_ids = fields.One2many('spc.amd.shareholder', 'amd_id', string='Shareholders')
    # Managers
    manager_count = fields.Integer(string='Number of Managers')
    manager_ids = fields.One2many('spc.amd.manager', 'amd_id', string='Managers')
    # Directors
    director_count = fields.Integer(string='Number of Directors')
    director_ids = fields.One2many('spc.amd.director', 'amd_id', string='Directors')
    # Company Information
    new_company_name = fields.Char(string='New Company Name')
    company_name_arabic = fields.Char(string='Company Name (Arabic)')
    company_address = fields.Text(string='Company Address')
    company_phone = fields.Char(string='Company Phone')
    company_email = fields.Char(string='Company Email')
    company_website = fields.Char(string='Company Website')
    company_info_notes = fields.Text(string='Company Info Notes')
    # Facility Type
    facility_type = fields.Char(string='Facility Type')
    # Documents
    document_ids = fields.One2many('spc.amd.document', 'amd_id', string='Documents')
    fee = fields.Float(string='Fee', default=0.0)
    payment_method = fields.Char(string='Payment Method')
    payment_status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ], string='Payment Status', default='pending')
    admin_notes = fields.Text(string='Admin Notes')

    @api.model
    def create(self, vals):
        if vals.get('reference', 'New') == 'New':
            vals['reference'] = self.env['ir.sequence'].next_by_code('spc.amendment') or 'AMD/0001'
        return super().create(vals)

    def action_approve(self):
        self.state = 'approved'

    def action_reject(self):
        self.state = 'rejected'

    def action_under_review(self):
        self.state = 'in_progress'


class SpcAmdShareholder(models.Model):
    _name = 'spc.amd.shareholder'
    _description = 'AMD Shareholder'
    amd_id = fields.Many2one('spc.amendment', ondelete='cascade')
    shareholder_type = fields.Char(string='Type')
    full_name = fields.Char(string='Full Name')
    first_name = fields.Char(string='First Name')
    last_name = fields.Char(string='Last Name')
    passport_no = fields.Char(string='Passport Number')
    passport_expiry = fields.Char(string='Passport Expiry')
    nationality = fields.Char(string='Nationality')
    dob = fields.Char(string='Date of Birth')
    email = fields.Char(string='Email')
    mobile = fields.Char(string='Mobile')
    address = fields.Text(string='Address')
    city = fields.Char(string='City')
    country = fields.Char(string='Country')
    has_uae_visa = fields.Char(string='UAE Visa')
    visa_no = fields.Char(string='Visa Number')
    eid_no = fields.Char(string='Emirates ID')
    uid = fields.Char(string='UID')
    shares_allocated = fields.Integer(string='Shares Allocated')
    entity_name = fields.Char(string='Entity Name')
    entity_reg_no = fields.Char(string='Entity Reg No')


class SpcAmdManager(models.Model):
    _name = 'spc.amd.manager'
    _description = 'AMD Manager'
    amd_id = fields.Many2one('spc.amendment', ondelete='cascade')
    define_from = fields.Char(string='Defined From')
    full_name = fields.Char(string='Full Name')
    first_name = fields.Char(string='First Name')
    last_name = fields.Char(string='Last Name')
    nationality = fields.Char(string='Nationality')
    email = fields.Char(string='Email')
    mobile = fields.Char(string='Mobile')
    passport_no = fields.Char(string='Passport Number')
    passport_expiry = fields.Char(string='Passport Expiry')
    has_uae_residence = fields.Char(string='UAE Residence')
    visa_no = fields.Char(string='Visa Number')
    eid_no = fields.Char(string='Emirates ID')
    uid = fields.Char(string='UID')


class SpcAmdDirector(models.Model):
    _name = 'spc.amd.director'
    _description = 'AMD Director'
    amd_id = fields.Many2one('spc.amendment', ondelete='cascade')
    define_from = fields.Char(string='Defined From')
    full_name = fields.Char(string='Full Name')
    first_name = fields.Char(string='First Name')
    last_name = fields.Char(string='Last Name')
    nationality = fields.Char(string='Nationality')
    email = fields.Char(string='Email')
    mobile = fields.Char(string='Mobile')
    passport_no = fields.Char(string='Passport Number')
    passport_expiry = fields.Char(string='Passport Expiry')
    has_uae_residence = fields.Char(string='UAE Residence')
    visa_no = fields.Char(string='Visa Number')
    eid_no = fields.Char(string='Emirates ID')
    uid = fields.Char(string='UID')


class SpcAmdDocument(models.Model):
    _name = 'spc.amd.document'
    _description = 'Amendment Supporting Document'

    amd_id = fields.Many2one('spc.amendment', string='Amendment Application', ondelete='cascade')
    stage = fields.Integer(string='Stage')
    document_type = fields.Char(string='Document Type')
    related_to = fields.Char(string='Related To')
    file_name = fields.Char(string='File Name')
    file_data = fields.Binary(string='File', attachment=True)
    uploaded_on = fields.Datetime(string='Uploaded On', default=fields.Datetime.now)


class SpcVisaAllocationAmendment(models.Model):
    _name = 'spc.visa.allocation.amendment'
    _description = 'Visa Allocation Amendment'
    _rec_name = 'reference'

    reference = fields.Char(string='Reference', readonly=True)
    customer_id = fields.Many2one('res.partner', string='Customer')
    company_id = fields.Many2one('res.partner', string='Company')
    company_name = fields.Char(string='Company Name')
    package_type = fields.Char(string='Package Type')
    amendment_type = fields.Char(string='Amendment Type')
    license_validity = fields.Char(string='License Validity')
    facility_type = fields.Char(string='Facility Type')
    existing_visa_allocation = fields.Integer(string='Existing Visa Allocation')
    upgrade_downgrade = fields.Char(string='Upgrade/Downgrade')
    additional_visas = fields.Integer(string='Additional Visas')
    final_visa_allocation = fields.Integer(string='Final Visa Allocation')
    remarks = fields.Text(string='Remarks')
    fee = fields.Float(string='Fee', default=0.0)
    payment_method = fields.Char(string='Payment Method')
    payment_status = fields.Selection([
        ('pending', 'Pending'), ('paid', 'Paid')
    ], string='Payment Status', default='pending')
    state = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'),
        ('in_progress', 'In Progress'), ('approved', 'Approved'), ('rejected', 'Rejected')
    ], string='State', default='draft')
    admin_notes = fields.Text(string='Admin Notes')

    def action_under_review(self):
        self.state = 'in_progress'

    def action_approve(self):
        self.state = 'approved'

    def action_reject(self):
        self.state = 'rejected'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('reference'):
                vals['reference'] = self.env['ir.sequence'].next_by_code('spc.visa.allocation.amendment') or 'VAA/0001'
        return super().create(vals_list)


class SpcCertify(models.Model):
    _name = 'spc.certify'
    _description = 'SPC Certify'
    _rec_name = 'reference'

    reference = fields.Char(string='Reference', readonly=True)
    customer_id = fields.Many2one('res.partner', string='Customer')
    company_id = fields.Many2one('res.partner', string='Company')
    company_name = fields.Char(string='Company Name')
    document_names = fields.Text(string='Documents to Certify')
    remarks = fields.Text(string='Remarks')
    declaration = fields.Boolean(string='Declaration Accepted')
    fee = fields.Float(string='Fee', default=0.0)
    payment_method = fields.Char(string='Payment Method')
    payment_status = fields.Selection([
        ('pending', 'Pending'), ('paid', 'Paid')
    ], string='Payment Status', default='pending')
    state = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'),
        ('in_progress', 'In Progress'), ('approved', 'Approved'), ('rejected', 'Rejected')
    ], string='State', default='draft')
    admin_notes = fields.Text(string='Admin Notes')

    def action_under_review(self):
        self.state = 'in_progress'

    def action_approve(self):
        self.state = 'approved'

    def action_reject(self):
        self.state = 'rejected'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('reference'):
                vals['reference'] = self.env['ir.sequence'].next_by_code('spc.certify') or 'CERT/0001'
        return super().create(vals_list)


class SpcEstablishmentCard(models.Model):
    _name = 'spc.establishment.card'
    _description = 'Establishment Card and E-Channel'
    _rec_name = 'reference'

    reference = fields.Char(string='Reference', readonly=True)
    service_sub_type = fields.Selection([
        ('new', 'New'),
        ('renewal', 'Renewal'),
        ('amendment', 'New - Amendment'),
        ('cancellation', 'Cancellation'),
    ], string='Sub Type')
    customer_id = fields.Many2one('res.partner', string='Customer')
    company_id = fields.Many2one('res.partner', string='Company')
    company_name = fields.Char(string='Company Name')
    # New fields
    confirm_establishment_card = fields.Char(string='Confirm Establishment Card')
    establishment_card_validity = fields.Char(string='Establishment Card Validity')
    confirm_echannel = fields.Char(string='Confirm E-Channel')
    echannel_validity = fields.Char(string='E-Channel Validity')
    # Common
    remarks = fields.Text(string='Remarks')
    declaration = fields.Boolean(string='Declaration Accepted')
    fee = fields.Float(string='Fee', default=0.0)
    payment_method = fields.Char(string='Payment Method')
    payment_status = fields.Selection([
        ('pending', 'Pending'), ('paid', 'Paid')
    ], string='Payment Status', default='pending')
    state = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'),
        ('in_progress', 'In Progress'), ('approved', 'Approved'), ('rejected', 'Rejected')
    ], string='State', default='draft')
    admin_notes = fields.Text(string='Admin Notes')

    def action_under_review(self): self.state = 'in_progress'
    def action_approve(self): self.state = 'approved'
    def action_reject(self): self.state = 'rejected'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('reference'):
                vals['reference'] = self.env['ir.sequence'].next_by_code('spc.establishment.card') or 'EC/0001'
        return super().create(vals_list)
