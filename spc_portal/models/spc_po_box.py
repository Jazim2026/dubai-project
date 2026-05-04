from odoo import models, fields, api

class SpcPoBox(models.Model):
    _name = 'spc.po.box'
    _description = 'PO Box Service'
    _rec_name = 'name'
    _order = 'create_date desc'

    name = fields.Char('Reference', readonly=True, default='New')
    partner_id = fields.Many2one('res.partner', 'Customer')
    service_type = fields.Selection([
        ('new', 'New'),
        ('renewal', 'Renewal'),
    ], string='Service Type', default='new')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('in_review', 'In Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='draft')

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
