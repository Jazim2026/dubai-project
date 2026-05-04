from odoo import models, fields, api

class SpcMovementReport(models.Model):
    _name = 'spc.movement.report'
    _description = 'Movement Report'
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

    # Step 1 - Application details
    applicant_id = fields.Many2one('res.partner', 'Applicant')
    first_name = fields.Char('First Name')
    last_name = fields.Char('Last Name')
    passport_number = fields.Char('Passport Number')
    email = fields.Char('Email Address')
    phone_code = fields.Char('Phone Code', default='+971')
    phone = fields.Char('Phone Number')
    date_of_birth = fields.Date('Date of Birth')
    passport_copy = fields.Binary('Passport Copy', attachment=True)
    passport_copy_filename = fields.Char('Passport Copy Filename')

    # Timeframe
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    remarks = fields.Text('Remarks')

    declaration_accepted = fields.Boolean('Declaration Accepted')
    amount = fields.Float('Service Fee', default=765.0)
    payment_status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ], default='pending')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('spc.movement.report') or 'New'
        return super().create(vals)

    def action_submit(self): self.state = 'submitted'
    def action_in_review(self): self.state = 'in_review'
    def action_approve(self): self.state = 'approved'
    def action_reject(self): self.state = 'rejected'
