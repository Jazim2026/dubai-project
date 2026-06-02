# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SpcServicePrice(models.Model):
    _name = 'spc.service.price'
    _description = 'SPC Service Price Configuration'
    _rec_name = 'service_type'

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
    ], string='Service Type', required=True)

    amount = fields.Float(string='Amount (AED)', required=True, default=0.0)
    is_active = fields.Boolean(string='Active', default=True)
    description = fields.Text(string='Description')

    _sql_constraints = [
        ('unique_service_type', 'unique(service_type)',
         'Service type already exists!'),
    ]
