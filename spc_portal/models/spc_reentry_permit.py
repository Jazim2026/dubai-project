from odoo import models, fields, api

class SpcReentryPermit(models.Model):
    _name = 'spc.reentry.permit'
    _description = 'Re-Entry Permit'
    _rec_name = 'name'
    _order = 'create_date desc'

    name = fields.Char('Reference', readonly=True, default='New')
    partner_id = fields.Many2one('res.partner', 'Customer')
    approved_company_id = fields.Many2one('spc.approved.company', string='Company')
    state = fields.Selection([
        ('draft','Draft'),('submitted','Submitted'),
        ('in_review','In Review'),('approved','Approved'),
        ('documents_approved', 'Documents Approved'),
        ('payment_approved', 'Payment Approved'),
        ('complaints_approved', 'Complaints Approved'),
        ('under_process', 'Under Process'),
        ('completed', 'Completed'),
        ('rejected','Rejected'),('cancelled','Cancelled'),
    ], default='draft')
    # Request Tracking
    current_step = fields.Integer(string='Current Step', default=1)
    started_date = fields.Datetime(string='Started Date', readonly=True)

    # STEP 1
    applicant_name = fields.Char('Applicant Name')
    first_name = fields.Char('First Name')
    last_name = fields.Char('Last Name')
    phone_code = fields.Char('Phone Code', default='+971')
    mobile = fields.Char('Mobile Number')
    email = fields.Char('Email Address')
    passport_number = fields.Char('Passport Number')
    designation = fields.Selection([
        ('ac_technician','AC Technician'),
        ('civil_engineer','Civil Engineer'),
        ('cleaner','Cleaner'),
        ('cook','Cook'),
        ('data_entry_operator','Data Entry Operator'),
        ('driver','Driver'),
        ('electrical_engineer','Electrical Engineer'),
        ('it_manager','IT Manager'),
        ('mechanical_engineer','Mechanical Engineer'),
        ('nurse','Nurse'),
        ('office_boy','Office Boy'),
        ('pharmacist','Pharmacist'),
        ('programmer','Programmer'),
        ('security_guard','Security Guard'),
        ('software_engineer','Software Engineer'),
        ('storekeeper','Storekeeper'),
        ('supervisor','Supervisor'),
        ('teacher','Teacher'),
        ('technician','Technician'),
        ('other','Other'),
    ], 'Designation')
    visa_type = fields.Selection([
        ('employment','Employment Visa'),
        ('investor','Investor Visa'),
        ('dependent','Dependent Visa'),
        ('student','Student Visa'),
    ], 'Visa Type')
    reason_outside_uae = fields.Selection([
        ('study','Study'),
        ('work','Work'),
        ('medical','Medical Treatment'),
        ('others','Others'),
    ], 'Reason of staying outside UAE')
    months_outside_uae = fields.Selection([
        ('6','6 Months'),('7','7 Months'),('8','8 Months'),
        ('9','9 Months'),('10','10 Months'),('11','11 Months'),
        ('12','1 Year'),('18','1.5 Years'),('24','2 Years'),
        ('36','3 Years'),('48','4 Years'),('60','5 Years'),
        ('72','6 Years'),('84','7 Years'),('96','8 Years'),
        ('108','9 Years'),('120','10 Years'),
    ], 'Number of months outside UAE')
    visa_issue_date = fields.Date('Residence Visa Issue Date')
    visa_expiry_date = fields.Date('Residence Visa Expiry Date')

    # Documents
    doc_passport_ids = fields.Many2many('ir.attachment','rep_doc_pass_rel','rep_id','att_id', string='Passport Copy')
    doc_visa_ids = fields.Many2many('ir.attachment','rep_doc_visa_rel','rep_id','att_id', string='Residence Visa Copy')
    doc_proof_ids = fields.Many2many('ir.attachment','rep_doc_proof_rel','rep_id','att_id', string='Proof of Reason')

    declaration_accepted = fields.Boolean('Declaration Accepted')
    amount = fields.Float('Service Fee', default=765.0)
    payment_status = fields.Selection([('pending','Pending'),('paid','Paid')], default='pending')

    @api.model
    def create(self, vals):
        if vals.get('name','New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('spc.reentry.permit') or 'New'
        return super().create(vals)

    def action_submit(self):    self.state = 'submitted'
    def action_approve(self):   self.state = 'approved'
    def action_reject(self):    self.state = 'rejected'
    def action_in_review(self): self.state = 'in_review'
    def action_cancel(self):    self.state = 'cancelled'

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

