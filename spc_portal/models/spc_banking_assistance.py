from odoo import models, fields, api

class SpcBankingAssistance(models.Model):
    _name = 'spc.banking.assistance'
    _description = 'Banking Assistance'
    _rec_name = 'name'
    _order = 'create_date desc'

    name = fields.Char('Reference', readonly=True, default='New')
    partner_id = fields.Many2one('res.partner', 'Customer')
    approved_company_id = fields.Many2one('spc.approved.company', string='Company')
    banking_type = fields.Selection([
        ('new', 'New'),
        ('old', 'New (old)'),
    ], 'Banking Type', default='new')
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

    # Step 1 - Account Information
    account_type = fields.Selection([
        ('personal','Personal'),
        ('corporate','Corporate'),
    ], 'Account Type')
    preferred_bank = fields.Selection([
        ('rak_bank','RAK Bank'),
        ('wio_bank','WIO Bank'),
        ('mashreq','Mashreq'),
        ('dubai_islamic','Dubai Islamic'),
        ('mashreq_psc','Mashreq Bank P.S.C'),
        ('bank_misr','Bank Misr'),
        ('adcb','ADCB'),
        ('fab','FAB'),
        ('enbd','Emirates NBD'),
        ('cbd','CBD'),
    ], 'Preferred Bank')

    # Step 2 Personal - Shareholder Documents
    doc_eid_ids = fields.Many2many('ir.attachment','bank_doc_eid_rel','bank_id','att_id', string='EID Copy')
    doc_passport_ids = fields.Many2many('ir.attachment','bank_doc_pass_rel','bank_id','att_id', string='Passport Copy')
    doc_salary_ids = fields.Many2many('ir.attachment','bank_doc_salary_rel','bank_id','att_id', string='Salary Certificate')

    # Step 2 Corporate - Company Information
    company_registered_spc = fields.Selection([('yes','Yes'),('no','No')], 'Company registered with SPC')
    company_name_spc = fields.Char('Company Name')
    multi_shareholder = fields.Selection([('yes','Yes'),('no','No')], 'Multi-shareholder entity')

    # Step 3 Corporate - Corporate Documents (uploaded)
    doc_trade_license_ids = fields.Many2many('ir.attachment','bank_doc_trade_rel','bank_id','att_id', string='Trade License')
    doc_formation_ids = fields.Many2many('ir.attachment','bank_doc_form_rel','bank_id','att_id', string='Formation Certificate')
    doc_memorandum_ids = fields.Many2many('ir.attachment','bank_doc_memo_rel','bank_id','att_id', string='Memorandum of Association')
    doc_share_cert_ids = fields.Many2many('ir.attachment','bank_doc_share_rel','bank_id','att_id', string='Share Certificate')

    # Step 3 Personal / Step 5 Corporate - Corporate Bank Account
    need_bank_account = fields.Selection([('yes','Yes'),('no','No')], 'Need Bank Account')
    preferred_financial_provider = fields.Selection([
        ('wio_bank','WIO Bank'),
        ('mashreq_psc','Mashreq Bank P.S.C'),
        ('rak_bank','RAK Bank'),
        ('bank_misr','Bank Misr'),
        ('adcb','ADCB'),
        ('fab','FAB'),
        ('enbd','Emirates NBD'),
    ], 'Preferred Financial Services Provider')

    # Corporate additional fields
    shareholder_count = fields.Integer('Shareholder Count', default=1)
    shareholder_1_name = fields.Char('Shareholder 1 Name')
    shareholder_2_name = fields.Char('Shareholder 2 Name')
    shareholder_3_name = fields.Char('Shareholder 3 Name')
    shareholder_4_name = fields.Char('Shareholder 4 Name')

    # Corporate docs
    doc_business_plan_ids = fields.Many2many('ir.attachment','bank_doc_bp_rel','bank_id','att_id', string='Business Plan')
    doc_business_license_ids = fields.Many2many('ir.attachment','bank_doc_bl_rel','bank_id','att_id', string='Business License')
    doc_formation_cert_ids = fields.Many2many('ir.attachment','bank_doc_fc_rel','bank_id','att_id', string='Formation Certificate')
    doc_share_cert2_ids = fields.Many2many('ir.attachment','bank_doc_sc2_rel','bank_id','att_id', string='Share Certificate')
    doc_tenancy_ids = fields.Many2many('ir.attachment','bank_doc_ten_rel','bank_id','att_id', string='Tenancy Contract')

    # Shareholder 1 docs
    doc_sh1_eid_ids = fields.Many2many('ir.attachment','bank_doc_sh1_eid_rel','bank_id','att_id', string='SH1 EID')
    doc_sh1_passport_ids = fields.Many2many('ir.attachment','bank_doc_sh1_pass_rel','bank_id','att_id', string='SH1 Passport')
    doc_sh1_bank_ids = fields.Many2many('ir.attachment','bank_doc_sh1_bank_rel','bank_id','att_id', string='SH1 Bank Statement')
    doc_sh1_cv_ids = fields.Many2many('ir.attachment','bank_doc_sh1_cv_rel','bank_id','att_id', string='SH1 CV')
    # Shareholder 2 docs
    doc_sh2_eid_ids = fields.Many2many('ir.attachment','bank_doc_sh2_eid_rel','bank_id','att_id', string='SH2 EID')
    doc_sh2_passport_ids = fields.Many2many('ir.attachment','bank_doc_sh2_pass_rel','bank_id','att_id', string='SH2 Passport')
    doc_sh2_bank_ids = fields.Many2many('ir.attachment','bank_doc_sh2_bank_rel','bank_id','att_id', string='SH2 Bank Statement')
    doc_sh2_cv_ids = fields.Many2many('ir.attachment','bank_doc_sh2_cv_rel','bank_id','att_id', string='SH2 CV')
    # Shareholder 3 docs
    doc_sh3_eid_ids = fields.Many2many('ir.attachment','bank_doc_sh3_eid_rel','bank_id','att_id', string='SH3 EID')
    doc_sh3_passport_ids = fields.Many2many('ir.attachment','bank_doc_sh3_pass_rel','bank_id','att_id', string='SH3 Passport')
    doc_sh3_bank_ids = fields.Many2many('ir.attachment','bank_doc_sh3_bank_rel','bank_id','att_id', string='SH3 Bank Statement')
    doc_sh3_cv_ids = fields.Many2many('ir.attachment','bank_doc_sh3_cv_rel','bank_id','att_id', string='SH3 CV')
    # Shareholder 4 docs
    doc_sh4_eid_ids = fields.Many2many('ir.attachment','bank_doc_sh4_eid_rel','bank_id','att_id', string='SH4 EID')
    doc_sh4_passport_ids = fields.Many2many('ir.attachment','bank_doc_sh4_pass_rel','bank_id','att_id', string='SH4 Passport')
    doc_sh4_bank_ids = fields.Many2many('ir.attachment','bank_doc_sh4_bank_rel','bank_id','att_id', string='SH4 Bank Statement')
    doc_sh4_cv_ids = fields.Many2many('ir.attachment','bank_doc_sh4_cv_rel','bank_id','att_id', string='SH4 CV')

    # ── OLD FLOW FIELDS ──
    doc_old_trade_license_ids = fields.Many2many('ir.attachment','bank_old_tl_rel','bank_id','att_id', string='Trade License (Old)')
    doc_old_formation_cert_ids = fields.Many2many('ir.attachment','bank_old_fc_rel','bank_id','att_id', string='Formation Certificate (Old)')
    doc_old_share_cert_ids = fields.Many2many('ir.attachment','bank_old_sc_rel','bank_id','att_id', string='Share Certificate (Old)')
    doc_old_lease_agreement_ids = fields.Many2many('ir.attachment','bank_old_la_rel','bank_id','att_id', string='Lease Agreement (Old)')
    doc_old_memorandum_ids = fields.Many2many('ir.attachment','bank_old_mo_rel','bank_id','att_id', string='Memorandum of Association (Old)')
    doc_old_good_standing_ids = fields.Many2many('ir.attachment','bank_old_gs_rel','bank_id','att_id', string='Certificate of Good Standing (Old)')
    doc_old_incumbency_ids = fields.Many2many('ir.attachment','bank_old_ic_rel','bank_id','att_id', string='Incumbency Certificate (Old)')
    old_remarks = fields.Text('Remarks (Old)')
    need_bank_account_old = fields.Selection([('yes','Yes'),('no','No')], 'Need Bank Account (Old)')
    preferred_financial_provider_old = fields.Selection([
        ('wio','WIO bank'),
        ('mashreq','Mashreq Bank P.S.C'),
        ('rak','RAK Bank'),
        ('bank_misr','Bank Misr'),
    ], 'Preferred Financial Provider (Old)')
    old_declaration_accepted = fields.Boolean('Old Declaration Accepted')

    declaration_accepted = fields.Boolean('Declaration Accepted')
    amount = fields.Float('Service Fee', default=1000.0)
    payment_status = fields.Selection([('pending','Pending'),('paid','Paid')], default='pending')

    @api.model
    def create(self, vals):
        if vals.get('name','New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('spc.banking.assistance') or 'New'
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

