from odoo import models, fields, api

class SpcPhoneAnswering(models.Model):
    _name = 'spc.phone.answering'
    _description = 'Phone Answering Service'
    _rec_name = 'name'
    _order = 'create_date desc'

    name = fields.Char('Reference', readonly=True, default='New')
    partner_id = fields.Many2one('res.partner', 'Customer')
    approved_company_id = fields.Many2one('spc.approved.company', string='Company')
    state = fields.Selection([
        ('draft','Draft'),('submitted','Submitted'),
        ('in_review','In Review'),('documents_approved', 'Documents Approved'),('payment_approved', 'Payment Approved'),('complaints_approved', 'Complaints Approved'),('under_process', 'Under Process'),('completed', 'Completed'),('approved','Approved'),('rejected','Rejected'),
    ], default='draft')
    # Request Tracking
    current_step = fields.Integer(string='Current Step', default=1)
    started_date = fields.Datetime(string='Started Date', readonly=True)

    # Step 1 - Phone answering details
    company_brand_name = fields.Char('Company Brand Name')
    contact_first_name = fields.Char('Contact First Name')
    contact_last_name = fields.Char('Contact Last Name')
    contact_phone_code = fields.Char('Phone Code', default='+971')
    contact_phone = fields.Char('Contact Phone')
    contact_email = fields.Char('Contact Email')
    preferred_greeting = fields.Text('Preferred Greeting Message')
    call_instructions = fields.Text('Call Instructions')
    address_line1 = fields.Char('Address Line 1')
    address_line2 = fields.Char('Address Line 2')
    city = fields.Char('City')
    country = fields.Char('Country')

    # Step 2 - Service details
    months_required = fields.Selection([
        ('1','1 month'),('3','3 months'),
        ('6','6 months'),('9','9 months'),('12','12 months'),
    ], string='Number of Months')
    working_days = fields.Char('Company Working Days')
    working_hours_from = fields.Char('Working Hours From')
    working_hours_to = fields.Char('Working Hours To')
    remarks = fields.Text('Remarks')
    company_website = fields.Char('Company Website')
    additional_instructions = fields.Text('Additional Instructions')

    declaration_accepted = fields.Boolean('Declaration Accepted')
    amount = fields.Float('Service Fee', default=10.0)
    payment_status = fields.Selection([('pending','Pending'),('paid','Paid')], default='pending')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('spc.phone.answering') or 'New'
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

