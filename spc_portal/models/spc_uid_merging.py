from odoo import models, fields, api

class SpcUidMerging(models.Model):
    _name = 'spc.uid.merging'
    _description = 'UID Merging'
    _rec_name = 'name'
    _order = 'create_date desc'

    name = fields.Char('Reference', readonly=True, default='New')
    partner_id = fields.Many2one('res.partner', 'Customer')
    approved_company_id = fields.Many2one('spc.approved.company', string='Company')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('in_review', 'In Review'),
        ('documents_approved', 'Documents Approved'),
        ('payment_approved', 'Payment Approved'),
        ('complaints_approved', 'Complaints Approved'),
        ('under_process', 'Under Process'),
        ('completed', 'Completed'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='draft')
    current_step = fields.Integer(string='Current Step', default=1)
    started_date = fields.Datetime(string='Started Date', readonly=True)

    # Step 1 fields
    employee_id = fields.Many2one('res.partner', 'Employee')
    manual_employee_name = fields.Char('Manual Employee Name')
    first_name = fields.Char('First Name')
    last_name = fields.Char('Last Name')
    contact_number = fields.Char('Contact Number')
    phone_code = fields.Char('Phone Code', default='+971')
    email = fields.Char('Email Address')
    date_of_birth = fields.Date('Date of Birth')
    passport_copy = fields.Binary('Passport Copy', attachment=True)
    passport_copy_filename = fields.Char('Passport Copy Filename')
    visa_application_number = fields.Char('Visa Application Number')
    visa_cancellation_doc = fields.Binary('Visa Cancellation / Other Passport', attachment=True)
    visa_cancellation_doc_filename = fields.Char('Visa Cancellation Doc Filename')
    comments = fields.Text('Comments')

    declaration_accepted = fields.Boolean('Declaration Accepted')
    amount = fields.Float('Service Fee', default=400.0)
    payment_status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ], default='pending')
    payment_method = fields.Char('Payment Method')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('spc.uid.merging') or 'New'
        return super().create(vals)

    def action_submit(self): self.state = 'submitted'
    def action_in_review(self): self.state = 'in_review'
    def action_approve(self): self.state = 'approved'
    def action_reject(self): self.state = 'rejected'

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

