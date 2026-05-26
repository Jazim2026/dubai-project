from odoo import models, fields, api

class SpcMedical(models.Model):
    _name = 'spc.medical'
    _description = 'Medical Service'
    _rec_name = 'name'
    _order = 'create_date desc'

    name = fields.Char('Reference', readonly=True, default='New')
    partner_id = fields.Many2one('res.partner', 'Customer')
    approved_company_id = fields.Many2one('spc.approved.company', string='Company')
    medical_type = fields.Selection([
        ('new_residency', 'Medical for New Residency'),
        ('renewal', 'Medical for Residency Renewal'),
    ], 'Medical Type', default='new_residency')
    state = fields.Selection([
        ('draft','Draft'),('submitted','Submitted'),
        ('in_review','In Review'),('approved','Approved'),
        ('documents_approved', 'Documents Approved'),
        ('payment_approved', 'Payment Approved'),
        ('complaints_approved', 'Complaints Approved'),
        ('under_process', 'Under Process'),
        ('completed', 'Completed'),
        ('rejected','Rejected'),
    ], default='draft')
    # Request Tracking
    current_step = fields.Integer(string='Current Step', default=1)
    started_date = fields.Datetime(string='Started Date', readonly=True)

    applicant_name = fields.Char('Applicant Name')
    visa_type = fields.Selection([
        ('employee','Employee visa'),
        ('partner','Partner / investor visa'),
        ('student','Student visa'),
        ('green','Green visa'),
    ], 'Visa Application Type')
    service_type = fields.Selection([
        ('normal','Normal'),
        ('vip','VIP Medical + Transport (Dubai, Sharjah, Ajman)'),
    ], 'Service Type')

    first_name = fields.Char('First Name')
    last_name = fields.Char('Last Name')
    mother_name = fields.Char("Mother's Name")
    email = fields.Char('Email')
    phone_code = fields.Char('Phone Code', default='+971')
    mobile = fields.Char('Mobile')
    dob = fields.Date('Date of Birth')
    marital_status = fields.Selection([
        ('single','Single'),('married','Married'),
        ('divorced','Divorced'),('widowed','Widowed'),
    ], 'Marital Status')
    religion = fields.Selection([
        ('muslim','Muslim'),('christian','Christian'),
        ('hindu','Hindu'),('buddhism','Buddhism'),('other','Other'),
    ], 'Religion')

    doc_passport_ids = fields.Many2many('ir.attachment','med_doc_pass_rel','med_id','att_id', string='Passport Copy')
    doc_special_ids = fields.Many2many('ir.attachment','med_doc_special_rel','med_id','att_id', string='Special Comments Page')
    doc_entry_visa_ids = fields.Many2many('ir.attachment','med_doc_entry_rel','med_id','att_id', string='Entry Visa Copy')
    doc_photo_ids = fields.Many2many('ir.attachment','med_doc_photo_rel','med_id','att_id', string='Passport-sized Photo')

    declaration_accepted = fields.Boolean('Declaration Accepted')
    amount = fields.Float('Service Fee', default=700.0)
    payment_status = fields.Selection([('pending','Pending'),('paid','Paid')], default='pending')

    @api.model
    def create(self, vals):
        if vals.get('name','New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('spc.medical') or 'New'
        return super().create(vals)

    def action_submit(self):    self.state = 'submitted'
    def action_approve(self):   self.state = 'approved'
    def action_reject(self):    self.state = 'rejected'
    def action_in_review(self): self.state = 'in_review'

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

