from odoo import models, fields, api

class SpcLeaseDocument(models.Model):
    _name = 'spc.lease.document'
    _description = 'Lease Document'
    _rec_name = 'name'
    _order = 'create_date desc'

    name = fields.Char('Reference', readonly=True, default='New')
    partner_id = fields.Many2one('res.partner', 'Customer')
    lease_type = fields.Selection([
        ('new','Lease Documents'),
        ('cancel','ERP Lease document - Cancel'),
    ], 'Lease Type', default='new')
    state = fields.Selection([
        ('draft','Draft'),('submitted','Submitted'),
        ('in_review','In Review'),('approved','Approved'),
        ('rejected','Rejected'),('cancelled','Cancelled'),
    ], default='draft')

    # STEP 1
    company_name = fields.Char('Company Name in English')
    manager_first_name = fields.Char('Manager First Name')
    manager_last_name = fields.Char('Manager Last Name')
    full_name_arabic = fields.Char('Full Name in Arabic')
    nationality_id = fields.Many2one('res.country', 'Nationality')
    passport_number = fields.Char('Passport Number')
    description_en = fields.Text('Description in English')
    address_en = fields.Text('Address in English')
    lease_validity = fields.Selection([
        ('6m','6 Months'),('1y','1 Year'),('2y','2 Years'),
        ('3y','3 Years'),('4y','4 Years'),('5y','5 Years'),
        ('6y','6 Years'),('7y','7 Years'),('8y','8 Years'),
        ('9y','9 Years'),('10y','10 Years'),
    ], 'Lease Validity')
    annual_rent = fields.Float('Annual Rent')
    commencement_date = fields.Date('Commencement Date')
    lease_expiry_date = fields.Date('Lease Expiry Date')
    facility_type = fields.Selection([
        ('prime15_furnished','SQM in Prime 15 Furnished'),
        ('prime15_unfurnished','SQM in Prime 15 Unfurnished'),
        ('prime10_furnished','SQM in Prime 10 Furnished'),
        ('prime10_unfurnished','SQM in Prime 10 Unfurnished'),
    ], 'Facility Type')
    additional_lease = fields.Selection([('yes','Yes'),('no','No')], 'Additional Lease Required', default='no')
    additional_desc_en = fields.Text('Additional Description in English')
    additional_address_en = fields.Text('Additional Location/Address in English')
    additional_annual_rent = fields.Float('Additional Annual Rent')

    declaration_accepted = fields.Boolean('Declaration Accepted')
    amount = fields.Float('Service Fee', default=0.0)
    payment_status = fields.Selection([('pending','Pending'),('paid','Paid')], default='pending')

    @api.model
    def create(self, vals):
        if vals.get('name','New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('spc.lease.document') or 'New'
        return super().create(vals)

    def action_submit(self):    self.state = 'submitted'
    def action_approve(self):   self.state = 'approved'
    def action_reject(self):    self.state = 'rejected'
    def action_in_review(self): self.state = 'in_review'
    def action_cancel(self):    self.state = 'cancelled'
