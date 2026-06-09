# -*- coding: utf-8 -*-
import hmac
import hashlib
import json
import logging
import razorpay
from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

RAZORPAY_KEY_ID = "rzp_test_RkkzKbFGDqSWEJ"
RAZORPAY_KEY_SECRET = "pGm3aDmOrsWkFlkl0cU4sBeD"



def _save_facility_management(request):
    try:
        from odoo import fields as odoo_fields
        step1 = request.session.get('fm_step1', {})
        step1_files = request.session.get('fm_step1_files', {})
        step2 = request.session.get('fm_step2', {})
        customer_id = request.session.get('spc_selected_customer_id')
        company_id = request.session.get('spc_selected_company_id')
        if not customer_id:
            return None
        vals = {
            'partner_id': customer_id,
            'approved_company_id': company_id,
            'state': 'submitted',
            'submission_date': odoo_fields.Datetime.now(),
            'complaint_category': step1.get('complaint_category', '') or False,
            'incident_type': step1.get('incident_type', ''),
            'office_number': step1.get('office_number', ''),
            'contact_name': step1.get('contact_name', ''),
            'contact_number': step1.get('contact_number', ''),
            'complaint_description': step1.get('complaint_description', ''),
            'declaration_accepted': step2.get('declaration_accepted', False),
            'total_amount': 0.0,
        }
        if step1_files.get('doc_image'):
            vals['doc_image'] = step1_files['doc_image']
        if step1_files.get('doc_image_name'):
            vals['doc_image_name'] = step1_files['doc_image_name']
        record = request.env['spc.facility.management'].sudo().create(vals)
        for key in ['fm_step1', 'fm_step1_files', 'fm_step2']:
            request.session.pop(key, None)
        return record
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("FM save error: %s", str(e))
        return None


def _save_dam(request):
    try:
        from odoo import fields as odoo_fields
        step1 = request.session.get('dam_step1', {})
        step2 = request.session.get('dam_step2', {})
        step3 = request.session.get('dam_step3', {})
        customer_id = request.session.get('spc_selected_customer_id')
        company_id = request.session.get('spc_selected_company_id')
        if not customer_id:
            return None
        vals = {
            'partner_id': customer_id,
            'approved_company_id': company_id,
            'state': 'submitted',
            'submission_date': odoo_fields.Datetime.now(),
            'is_existing_stakeholder': step1.get('is_existing_stakeholder', '') or False,
            'employee_list': step1.get('employee_list', ''),
            'first_name': step1.get('first_name', ''),
            'last_name': step1.get('last_name', ''),
            'contact_number': step1.get('contact_number', ''),
            'email': step1.get('email', ''),
            'designation': step1.get('designation', ''),
            'language_preference': step1.get('language_preference', ''),
            'number_of_stakeholders': step2.get('number_of_stakeholders', '') or False,
            'number_of_years': step3.get('number_of_years', '') or False,
            'total_amount': 3000.0,
        }
        record = request.env['spc.dedicated.account.manager'].sudo().create(vals)
        for key in ['dam_step1', 'dam_step2', 'dam_step3']:
            request.session.pop(key, None)
        return record
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("DAM save error: %s", str(e))
        return None


def _save_change_of_status(request):
    try:
        from odoo import fields as odoo_fields
        step1 = request.session.get('cos_step1', {})
        step1_files = request.session.get('cos_step1_files', {})
        step2 = request.session.get('cos_step2', {})
        step3 = request.session.get('cos_step3', {})
        customer_id = request.session.get('spc_selected_customer_id')
        company_id = request.session.get('spc_selected_company_id')
        if not customer_id:
            return None
        vals = {
            'partner_id': customer_id,
            'approved_company_id': company_id,
            'state': 'submitted',
            'submission_date': odoo_fields.Datetime.now(),
            'applicant_name': step1.get('applicant_name', ''),
            'visa_status': step1.get('visa_status', '') or False,
            'remarks': step1.get('remarks', ''),
            'first_name': step2.get('first_name', ''),
            'last_name': step2.get('last_name', ''),
            'declaration_accepted': step3.get('declaration_accepted', False),
            'total_amount': 710.0,
        }
        for f in ['doc_cancelled_visa', 'doc_valid_visa']:
            if step1_files.get(f):
                vals[f] = step1_files[f]
            if step1_files.get(f + '_name'):
                vals[f + '_name'] = step1_files[f + '_name']
        record = request.env['spc.change.of.status'].sudo().create(vals)
        for key in ['cos_step1', 'cos_step1_files', 'cos_step2', 'cos_step3']:
            request.session.pop(key, None)
        return record
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("COS save error: %s", str(e))
        return None

class SpcPaymentController(http.Controller):

    @http.route('/spc/payment/<string:service_type>', 
                type='http', auth='user', website=True)
    def payment_page_no_record(self, service_type, **kwargs):
        return self.payment_page(service_type, 0, **kwargs)

    @http.route('/spc/payment/<string:service_type>/<int:record_id>',
                type='http', auth='user', website=True)
    def payment_page(self, service_type, record_id, **kwargs):
        # Get service price
        price = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', service_type),
            ('is_active', '=', True)
        ], limit=1)

        amount = price.amount if price else 0.0

        # Get customer info
        partner = request.env.user.partner_id
        company = request.env['spc.approved.company'].sudo().search([
            ('partner_id', '=', partner.id)
        ], limit=1)

        return request.render('spc_portal.template_payment_page', {
            'service_type': service_type,
            'record_id': record_id,
            'amount': amount,
            'amount_inr': int(amount * 23 * 100),  # AED to INR approx * 100 paise
            'razorpay_key_id': RAZORPAY_KEY_ID,
            'partner': partner,
            'company': company,
        })

    @http.route('/spc/payment/create-order',
                type='json', auth='user', methods=['POST'])
    def create_order(self, service_type, record_id, **kwargs):
        try:
            price = request.env['spc.service.price'].sudo().search([
                ('service_type', '=', service_type),
                ('is_active', '=', True)
            ], limit=1)

            amount = price.amount if price else 0.0
            amount_inr_paise = int(amount * 23 * 100)

            client = razorpay.Client(
                auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
            )
            order = client.order.create({
                'amount': amount_inr_paise,
                'currency': 'INR',
                'notes': {
                    'service_type': service_type,
                    'record_id': str(record_id),
                    'aed_amount': str(amount),
                }
            })

            partner = request.env.user.partner_id
            company = request.env['spc.approved.company'].sudo().search([
                ('partner_id', '=', partner.id)
            ], limit=1)

            payment_rec = request.env['spc.payment'].sudo().create({
                'customer_id': partner.id,
                'approved_company_id': company.id if company else False,
                'service_type': service_type,
                'source_model': 'spc.' + service_type.replace('_', '.'),
                'source_id': record_id,
                'amount': amount,
                'payment_method': 'razorpay',
                'razorpay_order_id': order['id'],
                'state': 'processing',
            })

            return {
                'success': True,
                'order_id': order['id'],
                'amount': amount_inr_paise,
                'payment_id': payment_rec.id,
            }
        except Exception as e:
            _logger.error("Razorpay order create error: %s", str(e))
            return {'success': False, 'error': str(e)}

    @http.route('/spc/payment/verify',
                type='json', auth='user', methods=['POST'])
    def verify_payment(self, razorpay_order_id, razorpay_payment_id,
                       razorpay_signature, payment_id, **kwargs):
        try:
            # Verify signature
            msg = f"{razorpay_order_id}|{razorpay_payment_id}"
            generated_sig = hmac.new(
                RAZORPAY_KEY_SECRET.encode(),
                msg.encode(),
                hashlib.sha256
            ).hexdigest()

            if generated_sig != razorpay_signature:
                return {'success': False, 'error': 'Invalid signature'}

            payment = request.env['spc.payment'].sudo().browse(payment_id)
            payment.write({
                'state': 'paid',
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature,
                'payment_date': fields.Datetime.now(),
            })
            payment._send_payment_notification('paid')
            if payment.service_type == 'facility_management':
                _save_facility_management(request)
            elif payment.service_type == 'dedicated_account_manager':
                _save_dam(request)
            elif payment.service_type == 'reentry_permit':
                rec = request.env['spc.reentry.permit'].sudo().browse(payment.source_id)
                if rec.exists():
                    rec.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
            elif payment.service_type == 'vip_medical_eid':
                rec = request.env['spc.vip.medical.eid'].sudo().browse(payment.source_id)
                if rec.exists():
                    rec.sudo().write({'state': 'submitted'})
            elif payment.service_type == 'lease_document':
                rec = request.env['spc.lease.document'].sudo().browse(payment.source_id)
                if rec.exists():
                    rec.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
            elif payment.service_type == 'banking_assistance':
                rec = request.env['spc.banking.assistance'].sudo().browse(payment.source_id)
                if rec.exists():
                    rec.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
            elif payment.service_type == 'banking_assistance_old':
                rec = request.env['spc.banking.assistance'].sudo().browse(payment.source_id)
                if rec.exists():
                    rec.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
            elif payment.service_type in ('medical_new', 'medical_renewal'):
                rec = request.env['spc.medical'].sudo().browse(payment.source_id)
                if rec.exists():
                    rec.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
            elif payment.service_type == 'meeting_room':
                rec = request.env['spc.meeting.room'].sudo().browse(payment.source_id)
                if rec.exists():
                    rec.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
            elif payment.service_type == 'company_stamp':
                rec = request.env['spc.company.stamp'].sudo().browse(payment.source_id)
                if rec.exists():
                    rec.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
            elif payment.service_type == 'phone_answering':
                rec = request.env['spc.phone.answering'].sudo().browse(payment.source_id)
                if rec.exists():
                    rec.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
            elif payment.service_type == 'movement_report':
                rec = request.env['spc.movement.report'].sudo().browse(payment.source_id)
                if rec.exists():
                    rec.sudo().write({'state': 'submitted'})
            elif payment.service_type == 'uid_merging':
                rec = request.env['spc.uid.merging'].sudo().browse(payment.source_id)
                if rec.exists():
                    rec.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
            elif payment.service_type == 'change_of_status':
                _save_change_of_status(request)
            elif payment.service_type == 'mofa':
                rec = request.env['spc.mofa'].sudo().browse(payment.source_id)
                if rec.exists():
                    rec.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
            elif payment.service_type == 'eid_appointment':
                rec = request.env['spc.eid.appointment'].sudo().browse(payment.source_id)
                if rec.exists():
                    rec.sudo().write({'state': 'submitted'})
            elif payment.service_type == 'driving_license':
                rec = request.env['spc.driving.license'].sudo().browse(payment.source_id)
                if rec.exists():
                    rec.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
            elif payment.service_type == 'dependent_visa':
                rec = request.env['spc.dependent.visa'].sudo().browse(payment.source_id)
                if rec.exists():
                    rec.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
            elif payment.service_type == 'po_box':
                rec = request.env['spc.po.box'].sudo().browse(payment.source_id)
                if rec.exists():
                    rec.sudo().write({'state': 'submitted'})

            return {'success': True}
        except Exception as e:
            _logger.error("Payment verify error: %s", str(e))
            return {'success': False, 'error': str(e)}

    @http.route('/spc/payment/bank-transfer',
                type='http', auth='user', methods=['POST'], csrf=True)
    def bank_transfer_upload(self, service_type, record_id,
                             proof_file=None, **kwargs):
        try:
            partner = request.env.user.partner_id
            company = request.env['spc.approved.company'].sudo().search([
                ('partner_id', '=', partner.id)
            ], limit=1)

            price = request.env['spc.service.price'].sudo().search([
                ('service_type', '=', service_type),
                ('is_active', '=', True)
            ], limit=1)

            proof_data = None
            proof_filename = None
            if proof_file:
                proof_data = proof_file.read()
                import base64
                proof_data = base64.b64encode(proof_data).decode()
                proof_filename = proof_file.filename

            payment = request.env['spc.payment'].sudo().create({
                'customer_id': partner.id,
                'approved_company_id': company.id if company else False,
                'service_type': service_type,
                'source_id': int(record_id),
                'amount': price.amount if price else 0.0,
                'payment_method': 'bank_transfer',
                'proof_data': proof_data,
                'proof_filename': proof_filename,
                'state': 'pending_approval',
            })
            payment._send_payment_notification('pending_approval')
            if service_type == 'facility_management':
                _save_facility_management(request)
            elif service_type == 'dedicated_account_manager':
                _save_dam(request)
            elif service_type == 'reentry_permit':
                rec = request.env['spc.reentry.permit'].sudo().search([('id', '=', int(record_id))], limit=1)
                if rec:
                    rec.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
            elif service_type == 'vip_medical_eid':
                rec = request.env['spc.vip.medical.eid'].sudo().search([('id', '=', int(record_id))], limit=1)
                if rec:
                    rec.sudo().write({'state': 'submitted'})
            elif service_type == 'lease_document':
                rec = request.env['spc.lease.document'].sudo().search([('id', '=', int(record_id))], limit=1)
                if rec:
                    rec.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
            elif service_type == 'banking_assistance':
                rec = request.env['spc.banking.assistance'].sudo().search([('id', '=', int(record_id))], limit=1)
                if rec:
                    rec.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
            elif service_type == 'banking_assistance_old':
                rec = request.env['spc.banking.assistance'].sudo().search([('id', '=', int(record_id))], limit=1)
                if rec:
                    rec.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
            elif service_type in ('medical_new', 'medical_renewal'):
                rec = request.env['spc.medical'].sudo().search([('id', '=', int(record_id))], limit=1)
                if rec:
                    rec.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
            elif service_type == 'meeting_room':
                rec = request.env['spc.meeting.room'].sudo().search([('id', '=', int(record_id))], limit=1)
                if rec:
                    rec.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
            elif service_type == 'company_stamp':
                rec = request.env['spc.company.stamp'].sudo().search([('id', '=', int(record_id))], limit=1)
                if rec:
                    rec.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
            elif service_type == 'phone_answering':
                rec = request.env['spc.phone.answering'].sudo().search([('id', '=', int(record_id))], limit=1)
                if rec:
                    rec.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
            elif service_type == 'movement_report':
                rec = request.env['spc.movement.report'].sudo().search([('id', '=', int(record_id))], limit=1)
                if rec:
                    rec.sudo().write({'state': 'submitted'})
            elif service_type == 'uid_merging':
                rec = request.env['spc.uid.merging'].sudo().search([('id', '=', int(record_id))], limit=1)
                if rec:
                    rec.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
            elif service_type == 'change_of_status':
                _save_change_of_status(request)
            elif service_type == 'mofa':
                rec = request.env['spc.mofa'].sudo().search([('id', '=', int(record_id))], limit=1)
                if rec:
                    rec.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
            elif service_type == 'eid_appointment':
                rec = request.env['spc.eid.appointment'].sudo().search([('id', '=', int(record_id))], limit=1)
                if rec:
                    rec.sudo().write({'state': 'submitted'})
            elif service_type == 'driving_license':
                rec = request.env['spc.driving.license'].sudo().search([('id', '=', int(record_id))], limit=1)
                if rec:
                    rec.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
            elif service_type == 'dependent_visa':
                rec = request.env['spc.dependent.visa'].sudo().search([('id', '=', int(record_id))], limit=1)
                if rec:
                    rec.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
            elif service_type == 'po_box':
                rec = request.env['spc.po.box'].sudo().search([('id', '=', int(record_id))], limit=1)
                if rec:
                    rec.sudo().write({'state': 'submitted'})

            return request.redirect(
                f'/spc/payment/success?method=bank_transfer'
            )
        except Exception as e:
            _logger.error("Bank transfer error: %s", str(e))
            return request.redirect('/spc/payment/failed')

    @http.route('/spc/payment/success',
                type='http', auth='user', website=True)
    def payment_success(self, method='razorpay', **kwargs):
        return request.render('spc_portal.template_payment_success', {
            'method': method,
        })

    @http.route('/spc/payment/failed',
                type='http', auth='user', website=True)
    def payment_failed(self, **kwargs):
        return request.render('spc_portal.template_payment_failed', {})

    @http.route('/spc/option-price/get',
                type='json', auth='public', methods=['POST'])
    def get_option_price(self, service_type, option_keys, **kwargs):
        """Fetch prices for selected options"""
        try:
            if not option_keys:
                return {'success': True, 'prices': {}, 'total_options': 0.0}

            groups = request.env['spc.option.group'].sudo().search([
                ('service_type', '=', service_type),
                ('is_active', '=', True),
            ])

            price_map = {}
            total = 0.0
            for group in groups:
                for line in group.option_line_ids:
                    if line.option_key in option_keys and line.is_active:
                        price_map[line.option_key] = line.amount
                        total += line.amount

            return {
                'success': True,
                'prices': price_map,
                'total_options': total,
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
