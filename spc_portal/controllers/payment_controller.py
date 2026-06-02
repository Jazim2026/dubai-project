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
