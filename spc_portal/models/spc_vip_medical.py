from odoo import models, fields, api

class SpcVipMedicalEid(models.Model):
    _name = 'spc.vip.medical.eid'
    _description = 'VIP Medical and EID Service'
    _rec_name = 'name'
    _order = 'create_date desc'

    name = fields.Char('Reference', readonly=True, default='New')
    partner_id = fields.Many2one('res.partner', 'Customer')
    state = fields.Selection([
        ('draft','Draft'),('submitted','Submitted'),
        ('in_review','In Review'),('approved','Approved'),
        ('rejected','Rejected'),
    ], default='draft', string='Status')

    # Step 1 fields
    applicant_select = fields.Char('Select Applicant')
    first_name = fields.Char('First Name')
    last_name = fields.Char('Last Name')
    contact_number = fields.Char('Contact Number')
    email = fields.Char('Email Address')
    preferred_date = fields.Date('Preferred Date for Medical Appointment')
    building_villa = fields.Char('Building or Villa Name/Number')
    city = fields.Selection([
        ('abu_dhabi','Abu Dhabi'),
        ('dubai','Dubai'),
        ('sharjah','Sharjah'),
        ('ajman','Ajman'),
        ('umm_al_quwain','Umm Al Quwain'),
        ('ras_al_khaimah','Ras Al Khaimah'),
        ('fujairah','Fujairah'),
    ], string='City')
    nearest_landmark = fields.Char('Nearest Landmark')

    # Step 2 - Documents
    doc_passport_photo = fields.Binary('Passport-sized Photo', attachment=True)
    doc_passport_photo_name = fields.Char('Passport Photo Filename')
    doc_entry_visa = fields.Binary('Entry Visa with Change of Status or Entry Stamp', attachment=True)
    doc_entry_visa_name = fields.Char('Entry Visa Filename')

    declaration_accepted = fields.Boolean('Declaration Accepted')
    amount = fields.Float('Service Fee', default=3025.0)
    payment_status = fields.Selection([('pending','Pending'),('paid','Paid')], default='pending')
    admin_notes = fields.Text('Admin Notes')
    rejection_reason = fields.Text('Rejection Reason')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('spc.vip.medical.eid') or 'New'
        return super().create(vals)

    def action_submit(self): self.state = 'submitted'
    def action_approve(self): self.state = 'approved'
    def action_reject(self): self.state = 'rejected'
    def action_in_review(self): self.state = 'in_review'


class SpcCompanyStamp(models.Model):
    _name = 'spc.company.stamp'
    _description = 'Company Stamp Service'
    _rec_name = 'name'
    _order = 'create_date desc'

    name = fields.Char('Reference', readonly=True, default='New')
    partner_id = fields.Many2one('res.partner', 'Customer')
    state = fields.Selection([
        ('draft','Draft'),('submitted','Submitted'),
        ('in_review','In Review'),('approved','Approved'),
        ('rejected','Rejected'),
    ], default='draft', string='Status')

    license_number = fields.Char('License Number')
    company_name = fields.Char('Company Name')
    remarks = fields.Text('Remarks / Comments')
    declaration_accepted = fields.Boolean('Declaration Accepted')
    amount = fields.Float('Service Fee', default=260.0)
    payment_status = fields.Selection([('pending','Pending'),('paid','Paid')], default='pending')
    admin_notes = fields.Text('Admin Notes')
    rejection_reason = fields.Text('Rejection Reason')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('spc.company.stamp') or 'New'
        return super().create(vals)

    def action_submit(self): self.state = 'submitted'
    def action_approve(self): self.state = 'approved'
    def action_reject(self): self.state = 'rejected'
    def action_in_review(self): self.state = 'in_review'


class SpcDependentVisa(models.Model):
    _name = 'spc.dependent.visa'
    _description = 'Dependent Visa Service'
    _rec_name = 'name'
    _order = 'create_date desc'

    name = fields.Char('Reference', readonly=True, default='New')
    partner_id = fields.Many2one('res.partner', 'Customer')
    state = fields.Selection([
        ('draft','Draft'),('submitted','Submitted'),
        ('in_review','In Review'),('approved','Approved'),
        ('rejected','Rejected'),
    ], default='draft', string='Status')

    # Step 1 - Sponsor details
    sponsor_has_spc_visa = fields.Selection([('yes','Yes'),('no','No')], 'Sponsor has visa with SPC?')
    sponsor_type = fields.Selection([('employee','Employee'),('investor','Investor')], 'Sponsor Type')

    # Sponsor details
    sponsor_gender = fields.Selection([('male','Male'),('female','Female')], 'Gender')
    sponsor_first_name = fields.Char('First Name')
    sponsor_last_name = fields.Char('Last Name')
    sponsor_marital_status = fields.Selection([
        ('married','Married'),('widowed','Widowed'),('divorced','Divorced')
    ], 'Marital Status')
    tenancy_under_sponsor = fields.Selection([('yes','Yes'),('no','No')], 'Tenancy contract under sponsor name?')

    # Employee specific
    sponsor_select = fields.Char('Select Sponsor')
    salary = fields.Float('Salary')
    designation = fields.Selection([
        ('manager','Manager'),('director','Director'),('engineer','Engineer'),
        ('accountant','Accountant'),('hr_officer','HR Officer'),
        ('sales_executive','Sales Executive'),('it_specialist','IT Specialist'),
        ('admin_officer','Administrative Officer'),('coordinator','Coordinator'),
        ('analyst','Analyst'),('consultant','Consultant'),('supervisor','Supervisor'),
        ('technician','Technician'),('developer','Developer'),('designer','Designer'),
        ('officer','Officer'),('assistant','Assistant'),('executive','Executive'),
    ], 'Designation')

    # Documents - Sponsor
    doc_passport_copy = fields.Binary('Passport Copy', attachment=True)
    doc_passport_copy_name = fields.Char('Passport Copy Filename')
    doc_residence_visa = fields.Binary('Residence Visa Copy', attachment=True)
    doc_residence_visa_name = fields.Char('Residence Visa Filename')
    doc_emirates_id = fields.Binary('Emirates ID Copy', attachment=True)
    doc_emirates_id_name = fields.Char('Emirates ID Filename')
    doc_tenancy_contract = fields.Binary('Attested Tenancy Contract', attachment=True)
    doc_tenancy_contract_name = fields.Char('Tenancy Contract Filename')
    doc_utility_bill = fields.Binary('Most Recent Utility Bill Copy', attachment=True)
    doc_utility_bill_name = fields.Char('Utility Bill Filename')
    doc_trade_license = fields.Binary('Trade License Copy', attachment=True)
    doc_trade_license_name = fields.Char('Trade License Filename')

    declaration_accepted = fields.Boolean('Declaration Accepted')
    amount = fields.Float('Service Fee', default=5010.0)
    payment_status = fields.Selection([('pending','Pending'),('paid','Paid')], default='pending')
    admin_notes = fields.Text('Admin Notes')
    rejection_reason = fields.Text('Rejection Reason')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('spc.dependent.visa') or 'New'
        return super().create(vals)


    # Dependent details (step2)
    dep_first_name = fields.Char('Dependent First Name')
    dep_last_name = fields.Char('Dependent Last Name')
    dep_father_name = fields.Char('Father Name')
    dep_mother_name = fields.Char('Mother Name')
    dep_mobile = fields.Char('Dependent Mobile')
    dep_nationality = fields.Char('Nationality')
    dep_prev_nationality = fields.Char('Previous Nationality')
    dep_marital_status = fields.Selection([('single','Single'),('married','Married'),('divorced','Divorced'),('widowed','Widowed')], 'Dependent Marital Status')
    dep_religion = fields.Selection([('muslim','Muslim'),('hindu','Hindu'),('christian','Christian'),('buddhism','Buddhism'),('other','Other')], 'Religion')
    doc_dep_passport = fields.Binary('Dep Passport Copy')
    doc_dep_passport_name = fields.Char('Dep Passport Filename')
    doc_dep_photo = fields.Binary('Dep Photo')
    doc_dep_photo_name = fields.Char('Dep Photo Filename')
    doc_dep_passport_special = fields.Binary('Dep Passport Special Page')
    doc_dep_passport_special_name = fields.Char('Dep Passport Special Filename')
    doc_dep_noc = fields.Binary('Attested NOC')
    doc_dep_noc_name = fields.Char('NOC Filename')
    # Application details (step3)
    applicant_location = fields.Selection([('inside','Inside'),('outside','Outside')], 'Applicant Location')
    current_status = fields.Selection([('cancelled_resident','Cancelled Resident Visa'),('valid_visa','Valid Visa')], 'Current Status')
    change_of_status = fields.Selection([('yes','Yes'),('no','No')], 'Change of Status Required')
    doc_cancelled_visa_doc = fields.Binary('Cancelled Visa Doc')
    doc_cancelled_visa_doc_name = fields.Char('Cancelled Visa Doc Filename')
    doc_valid_visa_doc = fields.Binary('Valid Visa Doc')
    doc_valid_visa_doc_name = fields.Char('Valid Visa Doc Filename')
    # Remark (step4)
    additional_info = fields.Text('Additional Information')
    crm_comments = fields.Text('CRM Comments')
    doc_remark = fields.Binary('Remark Document')
    doc_remark_name = fields.Char('Remark Document Filename')
    # Declaration
    dep_declaration_accepted = fields.Boolean('Dependent Declaration Accepted')
    def action_submit(self): self.state = 'submitted'
    def action_approve(self): self.state = 'approved'
    def action_reject(self): self.state = 'rejected'
    def action_in_review(self): self.state = 'in_review'

class SpcDocumentDelivery(models.Model):
    _name = 'spc.document.delivery'
    _description = 'SPC Document Delivery'
    _rec_name = 'name'

    name = fields.Char('Reference', default=lambda self: self.env['ir.sequence'].next_by_code('spc.document.delivery') or 'New')
    partner_id = fields.Many2one('res.partner', 'Partner')
    delivery_type = fields.Selection([('driver','Driver'),('courier','Courier')], 'Delivery Type')
    # Collection details
    collection_date = fields.Date('Preferred Collection Date')
    collection_time_frame = fields.Char('Preferred Collection Time Frame')
    collection_address = fields.Text('Collection Address')
    # Delivery details
    delivery_date = fields.Date('Preferred Delivery Date')
    delivery_time_frame = fields.Char('Preferred Delivery Time Frame')
    delivery_address = fields.Text('Delivery Address')
    # Remarks
    remarks = fields.Text('Remarks')
    # Declaration
    declaration_accepted = fields.Boolean('Declaration Accepted')
    # Payment
    amount = fields.Float('Amount', default=10.0)
    payment_status = fields.Selection([('pending','Pending'),('paid','Paid')], default='pending')
    admin_notes = fields.Text('Admin Notes')
    rejection_reason = fields.Text('Rejection Reason')
    state = fields.Selection([
        ('draft','Draft'),('submitted','Submitted'),
        ('in_review','In Review'),('approved','Approved'),('rejected','Rejected')
    ], default='draft')

    delivery_standard = fields.Selection([('local','Local'),('international','International')], 'Delivery Standard')
    declaration_accepted_courier = fields.Boolean('Declaration Accepted Courier')
    return_reason = fields.Text('Reason for Returning Application')
    doc_supporting = fields.Binary('Supporting Documents')
    doc_supporting_name = fields.Char('Supporting Documents Filename')
    def action_submit(self): self.state = 'submitted'
    def action_approve(self): self.state = 'approved'
    def action_reject(self): self.state = 'rejected'
    def action_in_review(self): self.state = 'in_review'
