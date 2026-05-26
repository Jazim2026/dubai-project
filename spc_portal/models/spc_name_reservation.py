from odoo import models, fields, api

class SpcNameReservation(models.Model):
    _name = 'spc.name.reservation'
    _description = 'SPC Name Reservation Application'
    _rec_name = 'reference'
    _order = 'create_date desc'

    reference = fields.Char(string='Reference', readonly=True, default='New')
    customer_id = fields.Many2one('res.partner', string='Customer')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('documents_approved', 'Documents Approved'),
        ('payment_approved', 'Payment Approved'),
        ('complaints_approved', 'Complaints Approved'),
        ('under_process', 'Under Process'),
        ('completed', 'Completed'),
    ], string='Status', default='submitted')

    # Step 1: Business Activities
    business_activity_ids = fields.Many2many(
        'spc.business.activity',
        'spc_nr_activity_rel',
        'nr_id', 'activity_id',
        string='Business Activities'
    )
    activity_names = fields.Text(string='Activity Names')

    # Step 2: Company Name
    name_reserved = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Name Already Reserved?')
    reserved_name = fields.Char(string='Reserved Name')
    name_preference_1 = fields.Char(string='First Preference')
    name_preference_2 = fields.Char(string='Second Preference')
    name_preference_3 = fields.Char(string='Third Preference')
    translation_method = fields.Selection([
        ('direct', 'Direct Translation'),
        ('phonetic', 'Phonetic Sound'),
        ('own', 'I will provide my own translations'),
    ], string='Arabic Translation Method')

    # Step 3: Declaration
    declaration_accepted = fields.Boolean(string='Declaration Accepted')
    declarant_name = fields.Char(string='Declarant Name')
    declaration_date = fields.Date(string='Declaration Date')

    # Payment
    fee = fields.Float(string='Fee', default=500.0)
    payment_status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ], string='Payment Status', default='pending')

    # Admin notes
    admin_notes = fields.Text(string='Admin Notes')
    rejection_reason = fields.Text(string='Rejection Reason')

    @api.model
    def create(self, vals):
        if vals.get('reference', 'New') == 'New':
            vals['reference'] = self.env['ir.sequence'].next_by_code('spc.name.reservation') or 'NR/0001'
        return super().create(vals)

    def action_approve(self):
        self.state = 'approved'

    def action_reject(self):
        self.state = 'rejected'

    def action_approve_documents(self):
        self.write({'state': 'documents_approved'})

    def action_approve_payment(self):
        self.write({'state': 'payment_approved'})

    def action_approve_complaints(self):
        self.write({'state': 'complaints_approved'})

    def action_under_process(self):
        self.write({'state': 'under_process'})

    def action_completed(self):
        self.write({'state': 'completed'})

    def action_under_review(self):
        self.state = 'under_review'
