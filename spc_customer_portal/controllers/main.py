# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class SpcCustomerDashboard(http.Controller):

    def _check_access(self):
        """Check if user is logged in via spc_portal"""
        return request.session.get('spc_otp_verified') and request.session.get('spc_uid')

    def _get_customer(self):
        customer_id = request.session.get('spc_selected_customer_id')
        if not customer_id:
            return None
        try:
            rec = request.env['res.partner'].sudo().browse(customer_id)
            return rec if rec.exists() else None
        except Exception:
            return None

    @http.route('/spc/customer-dashboard', type='http', auth='public', website=True, csrf=True)
    def customer_dashboard(self, **kw):
        if not self._check_access():
            return request.redirect('/spc/login')

        customer = self._get_customer()
        uid = request.session.get('spc_uid')
        user = request.env['res.users'].sudo().browse(uid)

        # Get tasks
        task_count = 0
        try:
            task_count = request.env['project.task'].sudo().search_count([
                ('partner_id', '=', customer.id if customer else False),
            ])
        except Exception:
            pass

        # Get invoices
        invoice_count = 0
        try:
            invoice_count = request.env['account.move'].sudo().search_count([
                ('partner_id', '=', customer.id if customer else False),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
            ])
        except Exception:
            pass

        # Get recent account activity (messages/mail)
        activities = []
        try:
            activities = request.env['mail.message'].sudo().search([
                ('partner_ids', 'in', [customer.id] if customer else []),
                ('message_type', 'in', ['email', 'comment']),
            ], limit=10, order='date desc')
        except Exception:
            pass

        # Get open tasks list
        open_tasks = []
        try:
            open_tasks = request.env['project.task'].sudo().search([
                ('partner_id', '=', customer.id if customer else False),
                ('stage_id.fold', '=', False),
            ], limit=10)
        except Exception:
            pass

        return request.render('spc_customer_portal.template_customer_dashboard', {
            'customer': customer,
            'user': user,
            'company': user.company_id,
            'task_count': task_count,
            'invoice_count': invoice_count,
            'activities': activities,
            'open_tasks': open_tasks,
            'doc_count': 0,
            'employee_count': 0,
            'facility_count': 0,
        })

    @http.route('/spc/customer-dashboard/logout', type='http', auth='public', website=True, csrf=True)
    def dashboard_logout(self, **kw):
        request.session.pop('spc_email', None)
        request.session.pop('spc_uid', None)
        request.session.pop('spc_otp_verified', None)
        request.session.pop('spc_selected_customer_id', None)
        return request.redirect('/spc/login')
