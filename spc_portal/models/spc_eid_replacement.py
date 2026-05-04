from odoo import models, fields, api

class SpcEidReplacement(models.Model):
    _name = 'spc.eid.replacement'
    _description = 'EID Replacement'
    _rec_name = 'name'
    _order = 'create_date desc'

    name = fields.Char('Reference', readonly=True, default='New')
    partner_id = fields.Many2one('res.partner', 'Customer')
    state = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'),
        ('in_review', 'In Review'), ('approved', 'Approved'),
        ('rejected', 'Rejected'), ('cancelled', 'Cancelled'),
    ], default='draft', string='Status')

    # STEP 1
    visa_type = fields.Selection([
        ('employee', 'Employee Visa'),
        ('partner_investor', 'Partner / Investor Visa'),
        ('student', 'Student Visa'),
    ], string='Visa Application Type')

    # STEP 2 - Personal
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], 'Gender')
    first_name = fields.Char('First Name')
    last_name = fields.Char('Last Name')
    father_name = fields.Char("Father's Full Name")
    mother_name = fields.Char("Mother's Full Name")
    phone_code = fields.Char('Country Code', default='+971')
    phone = fields.Char('Home Country Contact Number')
    applicant_email = fields.Char('Email Address')
    address = fields.Char('Address in English')
    city = fields.Char('City')
    country_id = fields.Many2one('res.country', 'Country')
    dob = fields.Date('Date of Birth')
    birth_country_id = fields.Many2one('res.country', 'Country of Birth')
    nationality_id = fields.Many2one('res.country', 'Nationality')
    prev_nationality_id = fields.Many2one('res.country', 'Previous Nationality')
    marital_status = fields.Selection([
        ('single', 'Single'), ('married', 'Married'),
        ('divorced', 'Divorced'), ('student', 'Student'),
    ], 'Marital Status')
    religion = fields.Selection([
        ('hindu', 'Hindu'), ('muslim', 'Muslim'), ('christian', 'Christian'),
        ('buddhism', 'Buddhism'), ('other', 'Other'),
    ], 'Religion')

    # STEP 2 - Designation
    designation = fields.Selection([
        ('accountant', 'Accountant'),
        ('accountant_manager', 'Accountant Manager'),
        ('ac_technician', 'AC Technician'),
        ('administrator', 'Administrator'),
        ('architect', 'Architect'),
        ('business_development_manager', 'Business Development Manager'),
        ('cashier', 'Cashier'),
        ('civil_engineer', 'Civil Engineer'),
        ('cleaner', 'Cleaner'),
        ('clerk', 'Clerk'),
        ('cook', 'Cook'),
        ('customer_service', 'Customer Service Representative'),
        ('data_entry_operator', 'Data Entry Operator'),
        ('designer', 'Designer'),
        ('director', 'Director'),
        ('doctor', 'Doctor'),
        ('driver', 'Driver'),
        ('electrical_engineer', 'Electrical Engineer'),
        ('finance_manager', 'Finance Manager'),
        ('general_manager', 'General Manager'),
        ('hr_manager', 'HR Manager'),
        ('it_manager', 'IT Manager'),
        ('legal_advisor', 'Legal Advisor'),
        ('manager', 'Manager'),
        ('marketing_manager', 'Marketing Manager'),
        ('mechanical_engineer', 'Mechanical Engineer'),
        ('nurse', 'Nurse'),
        ('office_boy', 'Office Boy'),
        ('operations_manager', 'Operations Manager'),
        ('pharmacist', 'Pharmacist'),
        ('programmer', 'Programmer'),
        ('project_manager', 'Project Manager'),
        ('receptionist', 'Receptionist'),
        ('sales_executive', 'Sales Executive'),
        ('sales_manager', 'Sales Manager'),
        ('secretary', 'Secretary'),
        ('security_guard', 'Security Guard'),
        ('software_engineer', 'Software Engineer'),
        ('storekeeper', 'Storekeeper'),
        ('supervisor', 'Supervisor'),
        ('teacher', 'Teacher'),
        ('technician', 'Technician'),
        ('other', 'Other'),
    ], 'Designation')
    designation_unavailable = fields.Boolean('Designation Unavailable in Immigration', default=False)
    highest_qualification = fields.Selection([
        ('none', 'None'),
        ('primary', 'Primary Education'),
        ('lower_secondary', 'Lower Secondary'),
        ('upper_secondary', 'Upper Secondary'),
        ('vocational', 'Vocational/Technical'),
        ('diploma', 'Diploma'),
        ('bachelors', "Bachelor's Degree"),
        ('masters', "Master's Degree"),
        ('doctorate', 'Doctorate/PhD'),
    ], 'Highest Educational Qualification')

    # STEP 2 - Dependents
    has_dependents = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Sponsor Dependents?')
    dependent_spouse = fields.Boolean('Spouse')
    dependent_children = fields.Boolean('Children')
    dependent_domestic = fields.Boolean('Domestic Helper')
    num_dependents = fields.Integer('Number of Dependents')

    # STEP 2 - Documents (Many2many attachments - up to 5 each)
    doc_photo_ids = fields.Many2many('ir.attachment', 'eid_doc_photo_rel', 'eid_id', 'att_id', string='Photos')
    doc_evisa_ids = fields.Many2many('ir.attachment', 'eid_doc_evisa_rel', 'eid_id', 'att_id', string='E-visa Copy')
    doc_change_status_ids = fields.Many2many('ir.attachment', 'eid_doc_cs_rel', 'eid_id', 'att_id', string='Change Status Copy')
    doc_medical_ids = fields.Many2many('ir.attachment', 'eid_doc_med_rel', 'eid_id', 'att_id', string='Medical Result')
    doc_emp_contract_copy_ids = fields.Many2many('ir.attachment', 'eid_doc_ec_rel', 'eid_id', 'att_id', string='Employment Contract Copy')
    doc_eid_copy_ids = fields.Many2many('ir.attachment', 'eid_doc_eidc_rel', 'eid_id', 'att_id', string='Emirates ID Copy')
    doc_attested_degree_ids = fields.Many2many('ir.attachment', 'eid_doc_deg_rel', 'eid_id', 'att_id', string='Attested Degree')

    # STEP 3 - Emirates ID
    prev_residence_visa = fields.Selection([('yes','Yes'),('no','No')], 'Previously held residence visa?')
    biometric_mobile = fields.Char('Biometric Mobile Number')
    biometric_center = fields.Char('Preferred Biometric Center')
    has_uae_pobox = fields.Selection([('yes','Yes'),('no','No')], 'Has UAE PO Box?')
    pobox_location = fields.Char('PO Box Location')
    pobox_number = fields.Char('PO Box Number')
    deliver_physical_eid = fields.Selection([('yes','Yes'),('no','No')], 'Deliver Physical EID?')
    delivery_city = fields.Char('Delivery City')
    delivery_landmark = fields.Char('Nearest Landmark')
    delivery_address = fields.Char('Delivery Address')
    delivery_country = fields.Char('Delivery Country', default='United Arab Emirates')
    delivery_phone = fields.Char('Delivery Phone')
    eid_number = fields.Char('Emirates ID Number')
    doc_eid_front_ids = fields.Many2many('ir.attachment', 'eid_doc_front_rel', 'eid_id', 'att_id', string='EID Front')
    doc_eid_back_ids = fields.Many2many('ir.attachment', 'eid_doc_back_rel', 'eid_id', 'att_id', string='EID Back')
    eid_expiry = fields.Date('EID Expiry Date')

    # STEP 4 - Employment Contract
    contract_type = fields.Selection([('2yr_limited','2 years (LIMITED)'),('unlimited','Unlimited')], 'Contract Type')
    probation_period = fields.Selection([('90','90 Days'),('180','180 Days')], 'Probation Period')
    notice_period = fields.Char('Notice Period (in days)')
    salary_basic = fields.Float('Basic Salary')
    salary_accommodation = fields.Float('Accommodation Allowance')
    salary_transport = fields.Float('Transport Allowance')
    salary_other = fields.Float('Other Allowance')
    salary_total = fields.Float('Total Remuneration')
    contract_execution = fields.Date('Execution Date')
    contract_position = fields.Char('Position in Contract')
    contract_salary = fields.Float('Basic Salary (AED)')
    contract_start = fields.Date('Contract Start Date')
    contract_end = fields.Date('Contract End Date')
    doc_contract_ids = fields.Many2many('ir.attachment', 'eid_doc_contract_rel', 'eid_id', 'att_id', string='Employment Contract')

    # Declaration + Payment
    declaration_accepted = fields.Boolean('Declaration Accepted')
    amount = fields.Float('Service Fee', default=560.0)
    payment_status = fields.Selection([
        ('pending', 'Pending'), ('paid', 'Paid')
    ], default='pending')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('spc.eid.replacement') or 'New'
        return super().create(vals)

    def action_submit(self):    self.state = 'submitted'
    def action_approve(self):   self.state = 'approved'
    def action_reject(self):    self.state = 'rejected'
    def action_in_review(self): self.state = 'in_review'
    def action_cancel(self):    self.state = 'cancelled'
