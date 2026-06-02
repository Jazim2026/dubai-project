# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SpcOptionGroup(models.Model):
    _name = 'spc.option.group'
    _description = 'SPC Option Price Group'
    _rec_name = 'display_name'

    service_type = fields.Selection([
        ('facility_management', 'Facility Management'),
        ('eid_replacement', 'EID Replacement'),
        ('medical_new', 'Medical - New Residency'),
        ('medical_renewal', 'Medical - Renewal'),
        ('driving_license', 'Driving License'),
        ('reentry_permit', 'Re-Entry Permit'),
        ('lease_document', 'Lease Documents'),
        ('mofa', 'MOFA Attestation'),
        ('banking_assistance', 'Banking Assistance'),
        ('dedicated_account_manager', 'Dedicated Account Manager'),
        ('change_of_status', 'Change of Status'),
        ('meeting_room', 'Meeting Room Booking'),
        ('movement_report', 'Movement Report'),
        ('uid_merging', 'UID Merging'),
        ('eid_appointment', 'EID Appointment'),
        ('phone_answering', 'Phone Answering'),
        ('po_box', 'PO Box'),
        ('document_delivery', 'Document Delivery'),
        ('dependent_visa', 'Dependent Visa'),
        ('vip_medical_eid', 'VIP Medical EID'),
        ('company_stamp', 'Company Stamp'),
    ], string='Service', required=True)

    step_name = fields.Char(
        string='Step Name',
        required=True,
        help='e.g. complaint_category, incident_type'
    )
    step_label = fields.Char(
        string='Step Label',
        help='e.g. Complaint Category'
    )
    is_active = fields.Boolean(default=True)
    option_line_ids = fields.One2many(
        'spc.option.line',
        'group_id',
        string='Options'
    )

    display_name = fields.Char(
        compute='_compute_display_name',
        store=True
    )

    @api.depends('service_type', 'step_name')
    def _compute_display_name(self):
        for rec in self:
            service = dict(self._fields['service_type'].selection).get(
                rec.service_type, rec.service_type)
            rec.display_name = f"{service} - {rec.step_name}"


class SpcOptionLine(models.Model):
    _name = 'spc.option.line'
    _description = 'SPC Option Price Line'

    group_id = fields.Many2one(
        'spc.option.group',
        string='Group',
        ondelete='cascade'
    )
    option_key = fields.Char(
        string='Option Key',
        required=True,
        help='e.g. electrical, light_not_working'
    )
    option_label = fields.Char(
        string='Option Label',
        help='e.g. Electrical'
    )
    amount = fields.Float(
        string='Amount (AED)',
        required=True,
        default=0.0
    )
    is_active = fields.Boolean(default=True)
