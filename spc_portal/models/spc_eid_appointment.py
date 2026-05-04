from odoo import models, fields, api

class SpcEidAppointment(models.Model):
    _name = 'spc.eid.appointment'
    _description = 'EID Appointment'
    _rec_name = 'name'
    _order = 'create_date desc'

    name = fields.Char('Reference', readonly=True, default='New')
    partner_id = fields.Many2one('res.partner', 'Customer')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('in_review', 'In Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='draft')

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
