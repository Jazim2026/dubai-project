from odoo import models, fields, api

class SpcCorporateLetter(models.Model):
    _name = 'spc.corporate.letter'
    _description = 'SPC Corporate Letter'
    _rec_name = 'reference'
    _order = 'create_date desc'

    reference = fields.Char(string='Reference', readonly=True, default='New')
    customer_id = fields.Many2one('res.partner', string='Customer')
    company_name = fields.Char(string='Company Name')
    fee = fields.Float(string='Fee')
    payment_method = fields.Char(string='Payment Method')
    payment_status = fields.Char(string='Payment Status')
    letter_type = fields.Char(string='Letter Type')
    other_letter_name = fields.Char(string='Other Letter Name')
    license_expiry_date = fields.Date(string='License Expiry Date')
    declaration = fields.Text(string='Declaration')
    remarks = fields.Text(string='Remarks')
    admin_notes = fields.Text(string='Admin Notes')

    # NOC fields
    noc_type = fields.Selection([
        ('police_report', 'Police Report'),
        ('establish_ded', 'Establish DED'),
        ('register_vehicle', 'Register Vehicle'),
        ('transfer_vehicle', 'Transfer Vehicle'),
    ], string='NOC Type')
    police_station_name = fields.Char(string='Police Station Name')
    police_emirate = fields.Char(string='Police Emirate')
    ded_emirate = fields.Char(string='DED Emirate')
    ded_office_location = fields.Char(string='DED Office Location')

    # Vehicle fields
    vehicle_type = fields.Char(string='Vehicle Type')
    vehicle_chassis = fields.Char(string='Vehicle Chassis')
    vehicle_engine = fields.Char(string='Vehicle Engine')
    vehicle_model_year = fields.Char(string='Vehicle Model Year')
    vehicle_color = fields.Char(string='Vehicle Color')
    vehicle_country_origin = fields.Char(string='Country of Origin')
    vehicle_name = fields.Char(string='Vehicle Name')
    vehicle_make_model = fields.Char(string='Make/Model')
    vehicle_authority = fields.Char(string='Authority')
    vehicle_reg_copy = fields.Binary(string='Vehicle Registration Copy')
    vehicle_reg_filename = fields.Char(string='Filename')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('in_progress', 'In Progress'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft')

    @api.model
    def create(self, vals):
        if vals.get('reference', 'New') == 'New':
            vals['reference'] = self.env['ir.sequence'].next_by_code('spc.corporate.letter') or 'New'
        return super().create(vals)

    def action_under_review(self):
        self.write({'state': 'in_progress'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_reject(self):
        self.write({'state': 'rejected'})
