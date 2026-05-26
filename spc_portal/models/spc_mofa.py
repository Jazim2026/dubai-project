from odoo import models, fields, api

class SpcMofa(models.Model):
    _name = 'spc.mofa'
    _description = 'MOFA Attestation'
    _rec_name = 'name'
    _order = 'create_date desc'

    name = fields.Char('Reference', readonly=True, default='New')
    partner_id = fields.Many2one('res.partner', 'Customer')
    approved_company_id = fields.Many2one('spc.approved.company', string='Company')
    state = fields.Selection([
        ('draft','Draft'),('submitted','Submitted'),
        ('in_review','In Review'),('approved','Approved'),
        ('documents_approved', 'Documents Approved'),
        ('payment_approved', 'Payment Approved'),
        ('complaints_approved', 'Complaints Approved'),
        ('under_process', 'Under Process'),
        ('completed', 'Completed'),
        ('rejected','Rejected'),
    ], default='draft')
    # Request Tracking
    current_step = fields.Integer(string='Current Step', default=1)
    started_date = fields.Datetime(string='Started Date', readonly=True)

    doc_type_individual = fields.Boolean('Individual Affairs Documents')
    doc_type_commercial = fields.Boolean('Commercial Documents')
    doc_type_invoice = fields.Boolean('Invoice')

    individual_doc_count = fields.Integer('Individual Documents Count', default=0)
    commercial_doc_count = fields.Integer('Commercial Documents Count', default=0)
    invoice_doc_count = fields.Integer('Invoice Documents Count', default=0)

    origin_country_id = fields.Many2one('res.country', 'Document Origin Country')

    doc_individual_ids = fields.Many2many('ir.attachment','mofa_doc_ind_rel','mofa_id','att_id', string='Individual Documents')
    doc_commercial_ids = fields.Many2many('ir.attachment','mofa_doc_com_rel','mofa_id','att_id', string='Commercial Documents')
    doc_invoice_ids = fields.Many2many('ir.attachment','mofa_doc_inv_rel','mofa_id','att_id', string='Invoice Documents')

    declaration_accepted = fields.Boolean('Declaration Accepted')
    amount = fields.Float('Service Fee', default=10.0)
    payment_status = fields.Selection([('pending','Pending'),('paid','Paid')], default='pending')

    @api.model
    def create(self, vals):
        if vals.get('name','New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('spc.mofa') or 'New'
        return super().create(vals)

    def action_submit(self):    self.state = 'submitted'
    def action_approve(self):   self.state = 'approved'
    def action_reject(self):    self.state = 'rejected'
    def action_in_review(self): self.state = 'in_review'

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

