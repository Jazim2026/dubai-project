from odoo import models, fields, api

class SpcDrivingLicense(models.Model):
    _name = 'spc.driving.license'
    _description = 'Driving License Service'
    _rec_name = 'name'
    _order = 'create_date desc'

    name = fields.Char('Reference', readonly=True, default='New')
    partner_id = fields.Many2one('res.partner', 'Customer')
    approved_company_id = fields.Many2one('spc.approved.company', string='Company')
    license_type = fields.Selection([
        ('new','New'),('amendment','Amendment'),
        ('duplicate','Duplicate'),('renewal','Renewal'),('transfer','Transfer'),
    ], string='License Type')
    state = fields.Selection([
        ('draft','Draft'),('submitted','Submitted'),
        ('in_review','In Review'),('documents_approved', 'Documents Approved'),('payment_approved', 'Payment Approved'),('complaints_approved', 'Complaints Approved'),('under_process', 'Under Process'),('completed', 'Completed'),('approved','Approved'),('rejected','Rejected'),
    ], default='draft')
    # Request Tracking
    current_step = fields.Integer(string='Current Step', default=1)
    started_date = fields.Datetime(string='Started Date', readonly=True)

    # Applicant details
    first_name = fields.Char('First Name')
    last_name = fields.Char('Last Name')
    email = fields.Char('Email')
    phone_country_code = fields.Char('Country Code', default='+971')
    phone = fields.Char('Phone')
    date_of_birth = fields.Date('Date of Birth')
    remarks = fields.Text('Remarks')

    # Transfer specific
    license_country = fields.Char('Driving License Country of Issue')
    country_in_transfer_list = fields.Selection([('yes','Yes'),('no','No')], 'Country in Transfer List?')

    # Documents
    doc_passport = fields.Binary('Passport Copy', attachment=True)
    doc_passport_name = fields.Char()
    doc_emirates_id = fields.Binary('Emirates ID Copy', attachment=True)
    doc_emirates_id_name = fields.Char()
    doc_residence_visa = fields.Binary('Residence Visa Copy', attachment=True)
    doc_residence_visa_name = fields.Char()
    doc_driving_license = fields.Binary('Driving License Copy', attachment=True)
    doc_driving_license_name = fields.Char()
    doc_license_translation = fields.Binary('License Translation', attachment=True)
    doc_license_translation_name = fields.Char()

    doc_submission_ack = fields.Boolean('Document Submission Acknowledged')
    declaration_accepted = fields.Boolean('Declaration Accepted')
    amount = fields.Float('Service Fee', default=0.0)
    payment_status = fields.Selection([('pending','Pending'),('paid','Paid')], default='pending')

    @api.model
    def create(self, vals):
        if vals.get('name','New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('spc.driving.license') or 'New'
        return super().create(vals)

    def action_submit(self): self.state = 'submitted'
    def action_in_review(self): self.state = 'in_review'
    def action_approve(self): self.state = 'approved'
    def action_reject(self): self.state = 'rejected'
    def action_approve_documents(self): self.state = 'documents_approved'
    def action_approve_payment(self): self.state = 'payment_approved'
    def action_approve_complaints(self): self.state = 'complaints_approved'
    def action_under_process(self): self.state = 'under_process'
    def action_completed(self): self.state = 'completed'

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

