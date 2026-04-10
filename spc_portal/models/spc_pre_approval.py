from odoo import models, fields, api

class SpcPreApproval(models.Model):
    _name = 'spc.pre.approval'
    _description = 'SPC Pre-Approval Application'
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
    ], string='Status', default='submitted')

    # Step 1: Business Activities
    business_activity_ids = fields.Many2many(
        'spc.business.activity',
        'spc_pa_activity_rel',
        'pa_id', 'activity_id',
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

    # Step 3: Shareholder Details
    sh_first_name = fields.Char(string='First Name')
    sh_last_name = fields.Char(string='Last Name')
    sh_nationality = fields.Char(string='Nationality')
    sh_email = fields.Char(string='Email')
    sh_mobile = fields.Char(string='Mobile')
    sh_passport = fields.Char(string='Passport Number')
    sh_uae_resident = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='UAE Resident')
    sh_percent = fields.Float(string='Shareholding (%)')

    # Step 4: Declaration
    declaration_accepted = fields.Boolean(string='Declaration Accepted')
    declarant_name = fields.Char(string='Declarant Name')
    declaration_date = fields.Date(string='Declaration Date')

    # Payment
    fee = fields.Float(string='Fee', default=640.0)
    payment_method = fields.Char(string='Payment Method')
    payment_status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ], string='Payment Status', default='pending')

    # Documents
    document_ids = fields.One2many('spc.pa.document', 'pa_id', string='Documents')

    # Admin notes
    admin_notes = fields.Text(string='Admin Notes')
    rejection_reason = fields.Text(string='Rejection Reason')

    @api.model
    def create(self, vals):
        if vals.get('reference', 'New') == 'New':
            vals['reference'] = self.env['ir.sequence'].next_by_code('spc.pre.approval') or 'PA/0001'
        return super().create(vals)

    def action_approve(self):
        self.state = 'approved'

    def action_reject(self):
        self.state = 'rejected'

    def action_under_review(self):
        self.state = 'under_review'


class SpcPaDocument(models.Model):
    _name = 'spc.pa.document'
    _description = 'Pre-Approval Document'

    pa_id = fields.Many2one('spc.pre.approval', string='Application', ondelete='cascade')
    document_name = fields.Char(string='Document Name')
    document_type = fields.Selection([
        ('passport', 'Passport'),
        ('visa', 'Visa'),
        ('emirates_id', 'Emirates ID'),
        ('other', 'Other'),
    ], string='Document Type')
    file_data = fields.Binary(string='File', attachment=True)
    file_name = fields.Char(string='File Name')
