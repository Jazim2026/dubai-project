from odoo import models, fields, api

class SpcEidAppointment(models.Model):
    _name = 'spc.eid.appointment'
    _description = 'EID Appointment'
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
    # Request Tracking
    current_step = fields.Integer(string='Current Step', default=1)
    started_date = fields.Datetime(string='Started Date', readonly=True)

    # Step 1
    applicant_type = fields.Selection([
        ('employee', 'Employee'),
        ('investor', 'Investor'),
        ('student', 'Student'),
    ], string='Applicant Type')

    # Employee fields
    employee_profile_id = fields.Many2one('res.partner', 'Employee Profile')
    manual_employee_name = fields.Char('Employee Name')

    # Investor fields
    investor_profile_id = fields.Many2one('res.partner', 'Investor Profile')
    partner_profile_id = fields.Many2one('res.partner', 'Partner Profile')
    manual_investor_name = fields.Char('Investor Name')
    manual_partner_name = fields.Char('Partner Name')

    # Student fields
    student_profile_id = fields.Many2one('res.partner', 'Student Profile')
    manual_student_name = fields.Char('Student Name')

    # Common fields
    first_name = fields.Char('First Name')
    last_name = fields.Char('Last Name')
    email = fields.Char('Email')

    remarks = fields.Text('Remarks')
    declaration_accepted = fields.Boolean('Declaration Accepted')
    amount = fields.Float('Service Fee', default=360.0)
    payment_status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ], default='pending')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('spc.eid.appointment') or 'New'
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

