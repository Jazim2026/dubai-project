# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SpcPayment(models.Model):
    _name = 'spc.payment'
    _description = 'SPC Payment Records'
    _order = 'id desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Payment Reference',
        readonly=True,
        default='New',
        copy=False
    )
    customer_id = fields.Many2one(
        'res.partner',
        string='Customer'
    )
    approved_company_id = fields.Many2one(
        'spc.approved.company',
        string='Company'
    )
    service_type = fields.Selection([
        ('facility_management', 'Facility Management'),
        ('eid_replacement', 'EID Replacement'),
        ('medical_new', 'Medical - New Residency'),
        ('medical_renewal', 'Medical - Renewal'),
        ('driving_license', 'Driving License'),
        ('change_of_status', 'Change of Status'),
        ('meeting_room', 'Meeting Room Booking'),
        ('reentry_permit', 'Re-Entry Permit'),
        ('lease_document', 'Lease Documents'),
        ('mofa', 'MOFA Attestation'),
        ('banking_assistance', 'Banking Assistance - New'),
        ('banking_assistance_old', 'Banking Assistance - Existing'),
        ('dedicated_account_manager', 'Dedicated Account Manager'),
        ('movement_report', 'Movement Report'),
        ('uid_merging', 'UID Merging'),
        ('eid_appointment', 'EID Appointment'),
        ('po_box', 'PO Box'),
        ('document_delivery', 'Document Delivery'),
        ('document_delivery_courier', 'Document Delivery - Courier'),
        ('phone_answering', 'Phone Answering'),
        ('vip_medical_eid', 'VIP Medical EID'),
        ('company_stamp', 'Company Stamp'),
        ('dependent_visa', 'Dependent Visa'),
        ('company_new', 'Company Formation - New'),
        ('renewal_only', 'Company Formation - Renewal Only'),
        ('renewal_amendment', 'Company Formation - Renewal with Amendment'),
        ('amendment', 'Company Formation - Amendment'),
        ('visa_allocation_amendment', 'Visa Allocation Amendment'),
        ('certify', 'Company Formation - Certify'),
        ('establishment_card_new', 'Establishment Card - New'),
        ('establishment_card_renewal', 'Establishment Card - Renewal'),
        ('business_license', 'Business License - Additional'),
        ('corporate_letters', 'Corporate Letters - New'),
        ('license_reissue', 'License Reissue'),
        ('nma_media_license', 'NMA Media License - New'),
        ('nma_permit', 'NMA Permit - New'),
        ('employee_list', 'Employee List'),
        ('dependent_visa_new', 'Dependent Visa - New'),
        ('po_box_new', 'PO Box - New'),
        ('po_box_renewal', 'PO Box - Renewal'),
        ('name_reservation', 'Name Reservation - New'),
        ('pre_approval', 'Pre-Approval'),
    ], string='Service Type')

    source_model = fields.Char(string='Source Model')
    source_id = fields.Integer(string='Source Record ID')
    amount = fields.Float(string='Amount (AED)', default=0.0)

    payment_method = fields.Selection([
        ('razorpay', 'Razorpay (Card)'),
        ('bank_transfer', 'Bank Transfer'),
    ], string='Payment Method', default='razorpay')

    # Razorpay fields
    razorpay_order_id = fields.Char(string='Razorpay Order ID')
    razorpay_payment_id = fields.Char(string='Razorpay Payment ID')
    razorpay_signature = fields.Char(string='Razorpay Signature')

    # Bank Transfer fields
    proof_filename = fields.Char(string='Proof Filename')
    proof_data = fields.Binary(string='Payment Proof')

    state = fields.Selection([
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('paid', 'Paid'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('failed', 'Failed'),
        ('rejected', 'Rejected'),
    ], string='Status', default='pending')

    payment_date = fields.Datetime(string='Payment Date')
    failure_reason = fields.Char(string='Failure Reason')
    admin_note = fields.Text(string='Admin Note')

    def action_approve(self):
        self.write({'state': 'approved'})
        self._send_payment_notification('approved')

    def action_reject(self):
        self.write({'state': 'rejected'})
        self._send_payment_notification('rejected')

    def _send_payment_notification(self, status):
        try:
            msg = f'Your payment of AED {self.amount} for {dict(self._fields["service_type"].selection).get(self.service_type, "")} has been {status}.'
            self.env['spc.notification'].sudo().create({
                'name': f'Payment {status.title()}',
                'message': msg,
                'partner_id': self.customer_id.id if self.customer_id else False,
                'is_read': False,
            })
        except Exception:
            pass

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'spc.payment') or 'PAY-001'
        return super().create(vals)
