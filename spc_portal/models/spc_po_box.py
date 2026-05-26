from odoo import models, fields, api

class SpcPoBox(models.Model):
    _name = 'spc.po.box'
    _description = 'PO Box Service'
    _rec_name = 'name'
    _order = 'create_date desc'

    name = fields.Char('Reference', readonly=True, default='New')
    partner_id = fields.Many2one('res.partner', 'Customer')
    approved_company_id = fields.Many2one('spc.approved.company', string='Company')
    service_type = fields.Selection([
        ('new', 'New'),
        ('renewal', 'Renewal'),
    ], string='Service Type', default='new')
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
    # Request Tracking
    current_step = fields.Integer(string='Current Step', default=1)
    started_date = fields.Datetime(string='Started Date', readonly=True)

    # Step 1
    package_type = fields.Selection([
        ('light', 'PO Box Light'),
        ('bronze', 'PO Box Bronze'),
    ], string='PO Box Package')

    # Extra fields for PO Box Light
    prev_pobox_number = fields.Char('Previous PO Box Number')
    prev_pobox_emirate = fields.Char('Emirates')
    manager_fullname = fields.Char('Manager Full Name')
    manager_phone_code = fields.Char('Phone Code', default='+971')
    manager_phone = fields.Char('Manager Mobile Number')
    manager_sponsor = fields.Char('Sponsor Name')

    remarks = fields.Text('Remarks')
    declaration_accepted = fields.Boolean('Declaration Accepted')
    amount = fields.Float('Service Fee', default=10.0)
    payment_status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ], default='pending')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('spc.po.box') or 'New'
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

