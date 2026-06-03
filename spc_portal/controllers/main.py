# -*- coding: utf-8 -*-
import logging
import base64
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class SpcPortalController(http.Controller):

    def _check_spc_session(self):
        return bool(request.session.get('spc_otp_verified') and request.session.get('spc_uid'))

    def _spc_redirect(self):
        return request.redirect('/spc/login')

    # ── LOGIN ──
    @http.route('/spc/login', type='http', auth='public', website=True, csrf=False)
    def login_page(self, **kw):
        # Load approved companies for dropdown
        companies = []
        try:
            companies = request.env['spc.approved.company'].sudo().search(
                [('active', '=', True)], order='company_name asc'
            )
        except Exception:
            companies = []
        return request.render('spc_portal.template_spc_login', {
            'error': kw.get('error', ''),
            'email': kw.get('email', ''),
            'companies': companies,
        })

    @http.route('/spc/login/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def login_submit(self, email='', password='', **kw):
        if not email or not password:
            return request.redirect('/spc/login?error=Please+enter+email+and+password')
        try:
            uid = request.session.authenticate(request.db, email, password)
            if not uid:
                return request.redirect(f'/spc/login?error=Invalid+email+or+password&email={email}')
        except Exception:
            return request.redirect(f'/spc/login?error=Invalid+email+or+password&email={email}')
        try:
            request.env['spc.otp'].sudo().generate_otp(email)
        except Exception as e:
            _logger.error("OTP error: %s", e)
            # Skip OTP if email not configured — go direct
            request.session['spc_email'] = email
            request.session['spc_uid'] = uid
            request.session['spc_otp_verified'] = True
            return request.redirect('/spc/dashboard')
        request.session['spc_email'] = email
        request.session['spc_uid'] = uid
        return request.redirect('/spc/otp')

    # ── OTP ──
    @http.route('/spc/otp', type='http', auth='public', website=True, csrf=False)
    def otp_page(self, **kw):
        email = request.session.get('spc_email')
        if not email:
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_spc_otp', {
            'email': email,
            'error': kw.get('error', ''),
            'success': kw.get('success', ''),
        })

    @http.route('/spc/otp/verify', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def otp_verify(self, otp_code='', **kw):
        email = request.session.get('spc_email')
        if not email:
            return request.redirect('/spc/login')
        valid, msg = request.env['spc.otp'].sudo().verify_otp(email, otp_code.strip())
        if not valid:
            return request.redirect(f'/spc/otp?error={msg.replace(" ", "+")}')
        request.session['spc_otp_verified'] = True
        uid = request.session.get('spc_uid')
        if uid:
            user = request.env['res.users'].sudo().browse(uid)
            if user.partner_id:
                request.session['spc_selected_customer_id'] = user.partner_id.id
        return request.redirect('/spc/dashboard')

    @http.route('/spc/otp/resend', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def otp_resend(self, **kw):
        email = request.session.get('spc_email')
        if not email:
            return request.redirect('/spc/login')
        try:
            request.env['spc.otp'].sudo().generate_otp(email)
            return request.redirect('/spc/otp?success=OTP+resent+successfully')
        except Exception:
            return request.redirect('/spc/otp?error=Failed+to+resend+OTP')

    # ── DASHBOARD ──
    @http.route('/spc/dashboard', type='http', auth='public', website=True, csrf=False)
    def dashboard_page(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        uid = request.session.get('spc_uid')
        user = request.env['res.users'].sudo().browse(uid)
        selected_customer_id = request.session.get('spc_selected_customer_id')
        selected_customer = None
        approved_companies = []
        if selected_customer_id:
            rec = request.env['res.partner'].sudo().browse(selected_customer_id)
            if rec.exists():
                selected_customer = rec
                approved_companies = request.env['spc.approved.company'].sudo().search([
                    ('partner_id', '=', selected_customer.id),
                    ('active', '=', True),
                ], order='company_name asc')
        # Check if this user has any customers at all
        user_partner_id = user.partner_id.id
        existing_customers = request.env['res.partner'].sudo().search([
            ('is_company', '=', False),
            ('active', '=', True),
            ('id', '=', selected_customer_id),
        ], limit=1) if selected_customer_id else []
        no_customers = not bool(selected_customer_id)
        return request.render('spc_portal.template_spc_dashboard', {
            'company': user.company_id,
            'selected_customer': selected_customer,
            'approved_companies': approved_companies,
            'no_customers': no_customers,
            'error': kw.get('error', ''),
        })

    @http.route('/spc/dashboard/select', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def dashboard_select(self, customer_id='', **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        if customer_id:
            request.session['spc_selected_customer_id'] = int(customer_id)
        return request.redirect('/spc/dashboard')

    @http.route('/spc/dashboard/goto', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def dashboard_goto(self, customer_id='', **kw):
        if customer_id:
            request.session['spc_selected_customer_id'] = int(customer_id)
        approved_company_id = kw.get('approved_company_id', '')
        if approved_company_id:
            request.session['spc_selected_company_id'] = int(approved_company_id)
        redirect_to = kw.get("redirect_to") or "/spc/customer-dashboard"
        return request.redirect(redirect_to)

    @http.route('/spc/customer-dashboard', type='http', auth='public', website=True, csrf=False)
    def customer_dashboard(self, **kw):
        if False and not self._check_spc_session():
            return request.redirect('/spc/login')
        customer_id = request.session.get('spc_selected_customer_id')
        company_id = request.session.get('spc_selected_company_id')
        customer = None
        selected_company = None
        all_companies = []
        if customer_id:
            rec = request.env['res.partner'].sudo().browse(customer_id)
            if rec.exists():
                customer = rec
            all_companies = request.env['spc.approved.company'].sudo().search([
                ('partner_id', '=', customer_id),
                ('active', '=', True),
            ], order='company_name asc')
        if company_id:
            comp = request.env['spc.approved.company'].sudo().browse(company_id)
            if comp.exists():
                selected_company = comp
        qcontext = {
            'customer': customer,
            'selected_company': selected_company,
            'selected_company_id': company_id,
            'company_name': selected_company.company_name if selected_company else '',
            'all_companies': all_companies,
            'all_records': [],
            'service': {},
            'service_type': '',
            'fee': 0,
            'steps': [],
            'current_step': 1,
            'form_submit_url': '',
            'pending_docs': [],
        }
        return request.render('spc_portal.template_spc_customer_dashboard', qcontext)

    @http.route('/spc/switch-company', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def switch_company(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        company_id = kw.get('company_id', '')
        if company_id:
            request.session['spc_selected_company_id'] = int(company_id)
        return request.redirect('/spc/customer-dashboard')

    # ── ADD CUSTOMER ──
    @http.route('/spc/add-customer', type='http', auth='public', website=True, csrf=False)
    def add_customer_page(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_spc_add_customer', {
            'error': kw.get('error', ''),
        })

    @http.route('/spc/add-customer/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def add_customer_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        try:
            first_name = kw.get('first_name', '').strip()
            last_name = kw.get('last_name', '').strip()
            email = kw.get('email', '').strip()
            password = kw.get('password', '').strip()
            country_code = kw.get('country_code', '').strip()
            if not first_name or not last_name or not email or not password:
                return request.redirect('/spc/add-customer?error=Please+fill+all+required+fields')
            existing = request.env['res.partner'].sudo().search([('email', '=', email)], limit=1)
            if existing:
                return request.redirect('/spc/add-customer?error=Email+already+exists')
            country_id = False
            if country_code:
                country = request.env['res.country'].sudo().search([('code', '=', country_code)], limit=1)
                if country:
                    country_id = country.id
            vals = {
                'name': f"{first_name} {last_name}",
                'email': email,
                'is_company': False,
                'active': True,
            }
            if country_id:
                vals['country_id'] = country_id
            partner = request.env['res.partner'].sudo().create(vals)
            request.session['spc_selected_customer_id'] = partner.id
            return request.redirect('/spc/dashboard')
        except Exception as e:
            _logger.error("Add customer error: %s", e)
            return request.redirect('/spc/add-customer?error=Failed+to+create+customer')

    # ── LOGOUT ──
    # ── MY ACCOUNT ──
    @http.route('/spc/my-account', type='http', auth='public', website=True, csrf=False)
    def my_account(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        customer_id = request.session.get('spc_selected_customer_id')
        customer = None
        if customer_id:
            rec = request.env['res.partner'].sudo().browse(customer_id)
            if rec.exists():
                customer = rec
        tab = kw.get('tab', 'account_details')
        return request.render('spc_portal.template_spc_my_account', {
            'customer': customer,
            'tab': tab,
            'company_name': '',
            'all_companies': [],
            'selected_company_id': None,
        })

    @http.route('/spc/my-account/save', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def my_account_save(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        customer_id = request.session.get('spc_selected_customer_id')
        if customer_id:
            rec = request.env['res.partner'].sudo().browse(customer_id)
            if rec.exists():
                vals = {}
                first_name = kw.get('first_name', '').strip()
                last_name = kw.get('last_name', '').strip()
                if first_name or last_name:
                    vals['name'] = f"{first_name} {last_name}".strip()
                if kw.get('phone'):
                    vals['phone'] = kw.get('phone', '').strip()
                if kw.get('street'):
                    vals['street'] = kw.get('street', '').strip()
                if kw.get('building'):
                    vals['street2'] = kw.get('building', '').strip()
                if kw.get('city'):
                    vals['city'] = kw.get('city', '').strip()
                if kw.get('zip'):
                    vals['zip'] = kw.get('zip', '').strip()
                if kw.get('area'):
                    vals['comment'] = kw.get('area', '').strip()
                # Country
                country_name = kw.get('country', '').strip()
                if country_name:
                    country = request.env['res.country'].sudo().search([('name', 'ilike', country_name)], limit=1)
                    if country:
                        vals['country_id'] = country.id
                # Social
                if kw.get('twitter'):
                    vals['website'] = kw.get('twitter', '').strip()
                if kw.get('instagram'):
                    vals['instagram'] = kw.get('instagram', '').strip() if hasattr(rec, 'instagram') else None
                if kw.get('facebook'):
                    vals['facebook'] = kw.get('facebook', '').strip() if hasattr(rec, 'facebook') else None
                if kw.get('linkedin'):
                    vals['linkedin'] = kw.get('linkedin', '').strip() if hasattr(rec, 'linkedin') else None
                # Remove None values
                vals = {k: v for k, v in vals.items() if v is not None}
                if vals:
                    rec.write(vals)
        return request.redirect('/spc/my-account?tab=account_details')

    @http.route('/spc/my-account/upload-logo', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def my_account_upload_logo(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        company_id = request.session.get('spc_selected_company_id')
        logo_file = request.httprequest.files.get('company_logo')
        if logo_file and company_id:
            import base64
            comp = request.env['spc.approved.company'].sudo().browse(company_id)
            if comp.exists() and hasattr(comp, 'logo'):
                comp.write({'logo': base64.b64encode(logo_file.read()).decode('utf-8')})
        return request.redirect('/spc/my-account?tab=company_logo')

    @http.route('/spc/logout', type='http', auth='public', website=True, csrf=False)
    def logout(self, **kw):
        for key in ['spc_email', 'spc_uid', 'spc_otp_verified', 'spc_selected_customer_id']:
            request.session.pop(key, None)
        return request.redirect('/spc/login')

    # ── SETUP NEW COMPANY ──
    @http.route('/spc/setup-new-company', type='http', auth='public', website=True, csrf=False)
    def setup_new_company(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        customer_id = request.session.get('spc_selected_customer_id')
        customer = None
        if customer_id:
            rec = request.env['res.partner'].sudo().browse(customer_id)
            if rec.exists():
                customer = rec
        return request.render('spc_portal.template_setup_new_company', {'customer': customer})

    @http.route('/spc/setup-new-company/service/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def setup_company_service_detail(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        customer_id = request.session.get('spc_selected_customer_id')
        customer = None
        if customer_id:
            rec = request.env['res.partner'].sudo().browse(customer_id)
            if rec.exists():
                customer = rec
        services = {
            'company_new': {
                'name': 'Company New', 'tag': 'New', 'fee': 10,
                'category': 'Company Formation',
                'description': "The company's formation documents provide official proof of its establishment.",
                'requirements': ['Passport Copies of all Shareholders, Managers and Directors', 'UAE Visa Copy', 'Payment'],
                'output_documents': ['Trade License', 'Certificate of Incorporation', 'Share Certificate'],
                'output_collection': 'Electronic document',
                'timeline': '1-2 days',
                'steps': ['Legal type', 'Business activities', 'Company', 'Facility',
                          'Shareholder(s) information', 'Manager(s) information',
                          'Director(s) information', 'UBO information', 'Nature of business',
                          'Corporate bank account', 'Supporting document', 'Review application', 'Payment'],
            },
            'name_reservation': {
                'name': 'Name Reservation', 'tag': 'New', 'fee': 500,
                'category': 'Name Reservation',
                'description': "This service allows an investor to reserve a company name for a specific duration to prepare for company formation.",
                'requirements': ['Passport Copy of Applicant', 'Proposed Company Names (up to 3)', 'Payment'],
                'output_documents': ['Name Reservation Certificate'],
                'output_collection': 'Electronic document',
                'timeline': '1 day',
                'steps': ['Business Activities', 'Company Name', 'Review', 'Payment'],
            },
            'pre_approval': {
                'name': 'Pre-Approval', 'tag': 'New', 'fee': 640,
                'category': 'Pre-Approval',
                'description': "Business owners can initiate a pre-approval process to avoid potential immigration rejections.",
                'requirements': ['Passport Copy', 'Business Plan', 'Payment'],
                'output_documents': ['Pre-Approval Letter'],
                'output_collection': 'Electronic document',
                'timeline': '2-3 days',
                'steps': ['Details', 'Review', 'Payment'],
            },
        }
        service = services.get(service_type, {'name': service_type, 'tag': 'New', 'fee': 0,
                                               'category': '', 'description': '', 'requirements': [],
                                               'output_documents': [], 'output_collection': '', 'timeline': '',
                                               'steps': ['Details', 'Review', 'Payment']})
        return request.render('spc_portal.template_setup_company_service_detail', {
            'customer': customer, 'service_type': service_type, 'service': service,
        })

    @http.route('/spc/setup-new-company/apply/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def setup_company_apply(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        customer_id = request.session.get('spc_selected_customer_id')
        customer = None
        if customer_id:
            rec = request.env['res.partner'].sudo().browse(customer_id)
            if rec.exists():
                customer = rec
        return request.render('spc_portal.template_setup_company_apply', {
            'customer': customer, 'service_type': service_type, 'fee': 10,
            'steps': ['Legal type', 'Business activities', 'Company', 'Facility',
                      'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO',
                      'Nature of business', 'Bank account', 'Documents', 'Review', 'Payment'],
        })

    @http.route('/spc/setup-new-company/apply/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def setup_company_apply_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', '') or 'company_new'
        request.session['spc_apply_step1'] = {
            'service_type': service_type,
            'legal_type': kw.get('legal_type', ''),
            'package_type': kw.get('package_type', ''),
        }
        return request.redirect('/spc/setup-new-company/apply/step2/' + service_type)

    # ── STEP 2 ──
    @http.route('/spc/setup-new-company/apply/step2/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def setup_company_apply_step2(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        all_activities = request.env['spc.business.activity'].sudo().search([])
        fees_map = {'company_new': 10, 'name_reservation': 500, 'pre_approval': 640}

        # Build activities_data dict for template
        categories = [
            ('publishing_media', 'Publishing and Media'),
            ('wholesale_retail', 'Wholesale and Retail'),
            ('services_consultancy', 'Services and Consultancy'),
            ('electronic_publishing', 'Electronic Publishing'),
            ('real_publishing', 'Real Publishing'),
        ]
        activities_data = {}
        for cat_key, cat_label in categories:
            cat_acts = all_activities.filtered(lambda a: a.category == cat_key)
            divisions = {}
            for act in cat_acts:
                div = act.division or 'General'
                if div not in divisions:
                    divisions[div] = []
                divisions[div].append({
                    'id': act.id,
                    'code': act.code,
                    'name': act.name,
                })
            activities_data[cat_key] = {
                'label': cat_label,
                'divisions': divisions,
            }

        # If no category-based activities, build flat structure
        if not any(activities_data[k]['divisions'] for k in activities_data):
            divisions = {}
            for act in all_activities:
                div = act.division or act.category or 'General'
                if div not in divisions:
                    divisions[div] = []
                divisions[div].append({
                    'id': act.id,
                    'code': act.code or str(act.id),
                    'name': act.name,
                })
            activities_data['all'] = {
                'label': 'All Activities',
                'divisions': divisions,
            }
            categories = [('all', 'All Activities')]

        # NR flow: different steps
        if service_type == 'name_reservation':
            nr_steps = ['Business activities', 'Company name', 'Declaration', 'Review application', 'Payment']
        elif service_type == 'pre_approval':
            nr_steps = ['Business activities', 'Company name', 'Shareholder details', 'Declaration', 'Review application', 'Payment']
        else:
            nr_steps = ['Legal type', 'Business activities', 'Company', 'Facility', 'Visa allocation', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Bank account', 'Documents', 'Review', 'Payment']
        title_map = {
            'pre_approval': 'Pre-Approval - New',
            'name_reservation': 'Name Reservation - New',
        }
        return request.render('spc_portal.template_setup_company_step2', {
            'service_type': service_type,
            'activities_data': activities_data,
            'categories': categories,
            'fee': fees_map.get(service_type, 0),
            'steps': nr_steps,
            'current_step': 1 if service_type in ('name_reservation', 'pre_approval') else 2,
            'form_title': title_map.get(service_type, 'New Application'),
        })

    @http.route('/spc/setup-new-company/apply/step2/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def setup_company_apply_step2_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'company_new')
        activity_names = request.httprequest.form.getlist('business_activities')
        activity_ids = []
        if activity_names:
            acts = request.env['spc.business.activity'].sudo().search([('name', 'in', activity_names)])
            activity_ids = acts.ids
        request.session['spc_step2_data'] = {'activity_ids': activity_ids, 'activity_names': activity_names}
        if service_type == 'pre_approval':
            request.session['pa_step2_data'] = {'activity_ids': activity_ids, 'activity_names': activity_names}
            request.session.modified = True
            return request.redirect('/spc/setup-new-company/apply/pa-step3/' + service_type)
        if service_type == 'name_reservation':
            return request.redirect('/spc/setup-new-company/apply/nr-step2/' + service_type)
        return request.redirect('/spc/setup-new-company/apply/step3/' + service_type)

    # ── STEP 3 ──
    @http.route('/spc/setup-new-company/apply/step3/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def setup_company_apply_step3(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_setup_company_step3', {
            'service_type': service_type,
            'form_data': request.session.get('spc_step3_data', {}),
            'errors': [],
        
            'steps': ['Legal type', 'Business activities', 'Company', 'Facility', 'Visa allocation', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Bank account', 'Documents', 'Review', 'Payment'],
            'current_step': 3,
        })

    @http.route('/spc/setup-new-company/apply/step3/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def setup_company_apply_step3_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'company_new')
        files = request.httprequest.files
        data = {
            'license_years': kw.get('license_years', ''),
            'name_reserved': kw.get('name_reserved', ''),
            'reserved_name': kw.get('reserved_name', ''),
            'name_preference_1': kw.get('name_preference_1', ''),
            'name_preference_2': kw.get('name_preference_2', ''),
            'name_preference_3': kw.get('name_preference_3', ''),
            'arabic_translation': kw.get('arabic_translation', ''),
        }
        if 'reservation_doc' in files and files['reservation_doc'].filename:
            f = files['reservation_doc']
            data['reservation_doc_filename'] = f.filename
            data['reservation_doc_data'] = base64.b64encode(f.read()).decode()
        request.session['spc_step3_data'] = data
        return request.redirect('/spc/setup-new-company/apply/step4/' + service_type)

    # ── STEP 4 ──
    @http.route('/spc/setup-new-company/apply/step4/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def setup_company_apply_step4(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_setup_company_step4', {
            'service_type': service_type, 'form_data': {}, 'errors': [],
        
            'steps': ['Legal type', 'Business activities', 'Company', 'Facility', 'Visa allocation', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Bank account', 'Documents', 'Review', 'Payment'],
            'current_step': 4,
        })

    @http.route('/spc/setup-new-company/apply/step4/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def setup_company_apply_step4_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'company_new')
        request.session['spc_step4_data'] = {
            'facility_type': kw.get('facility_type', ''),
            'coworking_location_en': kw.get('coworking_location_en', ''),
            'coworking_location_ar': kw.get('coworking_location_ar', ''),
        }
        return request.redirect('/spc/setup-new-company/apply/step5/' + service_type)

    # ── STEP 5 ──
    @http.route('/spc/setup-new-company/apply/step5/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def setup_company_apply_step5(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_setup_company_step5', {
            'service_type': service_type, 'form_data': {}, 'errors': [],
        
            'steps': ['Legal type', 'Business activities', 'Company', 'Facility', 'Visa allocation', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Bank account', 'Documents', 'Review', 'Payment'],
            'current_step': 5,
        })

    @http.route('/spc/setup-new-company/apply/step5/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def setup_company_apply_step5_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'company_new')
        request.session['spc_step5_data'] = {'visa_count': kw.get('visa_count', 0)}
        return request.redirect('/spc/setup-new-company/apply/step6/' + service_type)

    # ── STEP 6 ──
    @http.route('/spc/setup-new-company/apply/step6/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def setup_company_apply_step6(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        customer_info = {}
        customer_id = request.session.get('spc_selected_customer_id')
        if customer_id:
            partner = request.env['res.partner'].sudo().browse(customer_id)
            if partner.exists():
                name_parts = (partner.name or '').split(' ', 1)
                customer_info = {
                    'first_name': name_parts[0] if name_parts else '',
                    'last_name': name_parts[1] if len(name_parts) > 1 else '',
                    'email': partner.email or '',
                    'mobile': partner.mobile or partner.phone or '',
                    'nationality': partner.country_id.code if partner.country_id else '',
                }
        existing_data = request.session.get('spc_step6_data', {})
        # URL param takes priority over session
        # If coming fresh (no URL param), default to 1
        url_count = request.params.get('shareholder_count') or kw.get('shareholder_count')
        if url_count:
            sh_count = max(1, min(int(url_count), 20))
        else:
            sh_count = 1
        sh_count = max(1, min(sh_count, 20))
        return request.render('spc_portal.template_setup_company_step6', {
            'service_type': service_type, 'form_data': existing_data, 'errors': [],
            'customer_info': customer_info,
            'sh_count': sh_count,
            'sh_range': list(range(1, sh_count + 1)),
            'steps': ['Legal type', 'Business activities', 'Company', 'Facility', 'Visa allocation', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Bank account', 'Documents', 'Review', 'Payment'],
            'current_step': 6,
            'form_submit_url': '/spc/setup-new-company/apply/step6/submit',
            'step_base_url': '/spc/setup-new-company/apply/step6/',
        })


    @http.route('/spc/setup-new-company/apply/step6/update-count', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def setup_company_step6_update_count(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'company_new')
        sh_count = kw.get('shareholder_count', 1)
        # Save to session
        existing = request.session.get('spc_step6_data', {})
        existing['shareholder_count'] = sh_count
        request.session['spc_step6_data'] = existing
        return request.redirect(f'/spc/setup-new-company/apply/step6/{service_type}?shareholder_count={sh_count}')

    @http.route('/spc/setup-new-company/apply/step6/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def setup_company_apply_step6_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'company_new')
        sh_count = int(kw.get('shareholder_count', 1) or 1)
        files = request.httprequest.files
        shareholders = []
        for i in range(1, sh_count + 1):
            sh_type = kw.get(f'sh_{i}_type', 'individual')
            sh = {
                'type': sh_type,
                'shares_allocated': kw.get(f'sh_{i}_shares', 0),
                'share_value': kw.get(f'sh_{i}_share_value', 0),
            }
            if sh_type == 'individual':
                sh.update({
                    'first_name': kw.get(f'sh_{i}_first_name', ''),
                    'last_name': kw.get(f'sh_{i}_last_name', ''),
                    'passport_no': kw.get(f'sh_{i}_passport_no', ''),
                    'nationality': kw.get(f'sh_{i}_nationality', ''),
                    'dob': kw.get(f'sh_{i}_dob', ''),
                    'email': kw.get(f'sh_{i}_email_id', ''),
                    'mobile': kw.get(f'sh_{i}_mobile', ''),
                    'address': kw.get(f'sh_{i}_address', ''),
                    'city': kw.get(f'sh_{i}_city', ''),
                    'country': kw.get(f'sh_{i}_country', ''),
                    'joining_date': kw.get(f'sh_{i}_joining_date', ''),
                    'uae_visa': kw.get(f'sh_{i}_uae_visa', ''),
                    'visa_no': kw.get(f'sh_{i}_visa_no', ''),
                    'eid_no': kw.get(f'sh_{i}_eid_no', ''),
                    'uid': kw.get(f'sh_{i}_uid', ''),
                })
            else:
                sh.update({
                    'entity_name': kw.get(f'sh_{i}_entity_name', ''),
                    'entity_reg_no': kw.get(f'sh_{i}_entity_reg_no', ''),
                    'entity_country': kw.get(f'sh_{i}_entity_country', ''),
                    'first_name': kw.get(f'sh_{i}_ent_first_name', ''),
                    'last_name': kw.get(f'sh_{i}_ent_last_name', ''),
                    'passport_no': kw.get(f'sh_{i}_ent_passport_no', ''),
                    'nationality': kw.get(f'sh_{i}_ent_nationality', ''),
                    'email': kw.get(f'sh_{i}_ent_email', ''),
                    'mobile': kw.get(f'sh_{i}_ent_mobile', ''),
                })
            for fname in [f'sh_{i}_passport_file', f'sh_{i}_passport_special',
                          f'sh_{i}_visa_file', f'sh_{i}_eid_file']:
                if fname in files and files[fname].filename:
                    f = files[fname]
                    sh[fname + '_filename'] = f.filename
                    sh[fname + '_data'] = base64.b64encode(f.read()).decode()
            shareholders.append(sh)
        request.session['spc_step6_data'] = {
            'shareholder_count': sh_count,
            'total_shares': kw.get('total_shares', 0),
            'value_per_share': kw.get('value_per_share', 0),
            'shareholders': shareholders,
        }
        return request.redirect('/spc/setup-new-company/apply/step7/' + service_type)

    # ── STEP 7 ──
    @http.route('/spc/setup-new-company/apply/step7/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def setup_company_apply_step7(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        url_count = request.params.get('manager_count') or kw.get('manager_count')
        if url_count:
            mgr_count = max(1, min(int(url_count), 20))
        else:
            mgr_count = 1
        return request.render('spc_portal.template_setup_company_step7', {
            'service_type': service_type,
            'mgr_count': mgr_count,
            'mgr_range': list(range(1, mgr_count + 1)),
            'steps': ['Legal type', 'Business activities', 'Company', 'Facility', 'Visa allocation', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Bank account', 'Documents', 'Review', 'Payment'],
            'current_step': 7,
        })

    @http.route('/spc/setup-new-company/apply/step7/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def setup_company_apply_step7_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'company_new')
        mgr_count = int(kw.get('manager_count', 1) or 1)
        files = request.httprequest.files
        managers = []
        for i in range(1, mgr_count + 1):
            mgr = {
                'define': kw.get(f'mgr_{i}_define', 'add_new'),
                'first_name': kw.get(f'mgr_{i}_first_name', ''),
                'last_name': kw.get(f'mgr_{i}_last_name', ''),
                'nationality': kw.get(f'mgr_{i}_nationality', ''),
                'email': kw.get(f'mgr_{i}_email', ''),
                'mobile': kw.get(f'mgr_{i}_mobile', ''),
                'uae_resident': kw.get(f'mgr_{i}_uae_resident', ''),
                'visa_no': kw.get(f'mgr_{i}_visa_no', ''),
                'eid_no': kw.get(f'mgr_{i}_eid_no', ''),
                'uid': kw.get(f'mgr_{i}_uid', ''),
            }
            for fname in [f'mgr_{i}_passport_file', f'mgr_{i}_passport_sp',
                          f'mgr_{i}_res_visa', f'mgr_{i}_eid', f'mgr_{i}_entry_visa']:
                if fname in files and files[fname].filename:
                    f = files[fname]
                    mgr[fname + '_filename'] = f.filename
                    mgr[fname + '_data'] = base64.b64encode(f.read()).decode()
            managers.append(mgr)
        request.session['spc_step7_data'] = {'manager_count': mgr_count, 'managers': managers}
        _logger.info('=== STEP7 SAVED: count=%s managers=%s', mgr_count, [m.get('first_name') for m in managers])
        return request.redirect('/spc/setup-new-company/apply/step8/' + service_type)

    # ── STEP 8 ──
    @http.route('/spc/setup-new-company/apply/step8/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def setup_company_apply_step8(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_setup_company_step8', {
            'service_type': service_type,
            'steps': ['Legal type', 'Business activities', 'Company', 'Facility', 'Visa allocation', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Bank account', 'Documents', 'Review', 'Payment'],
            'current_step': 8,
            'form_submit_url': '/spc/setup-new-company/apply/step8/submit',
        })
    @http.route('/spc/setup-new-company/apply/step8/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def setup_company_apply_step8_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'company_new')
        dir_count = int(kw.get('director_count', 1) or 1)
        files = request.httprequest.files
        directors = []
        for i in range(1, dir_count + 1):
            d = {
                'define': kw.get(f'dir_{i}_def', 'new'),
                'first_name': kw.get(f'dir_{i}_fn', ''),
                'last_name': kw.get(f'dir_{i}_ln', ''),
                'nationality': kw.get(f'dir_{i}_nat', ''),
                'email': kw.get(f'dir_{i}_email', ''),
                'mobile': kw.get(f'dir_{i}_mob', ''),
                'uae_resident': kw.get(f'dir_{i}_ures', ''),
                'visa_no': kw.get(f'dir_{i}_vno', ''),
                'eid_no': kw.get(f'dir_{i}_eino', ''),
                'uid': kw.get(f'dir_{i}_uid', ''),
            }
            for fname in [f'dir_{i}_pf', f'dir_{i}_spf', f'dir_{i}_rvf', f'dir_{i}_eidf']:
                if fname in files and files[fname].filename:
                    f = files[fname]
                    d[fname + '_filename'] = f.filename
                    d[fname + '_data'] = base64.b64encode(f.read()).decode()
            directors.append(d)
        request.session['spc_step8_data'] = {'director_count': dir_count, 'directors': directors}
        _logger.info('=== STEP8 SAVED: count=%s', dir_count)
        return request.redirect('/spc/setup-new-company/apply/step9/' + service_type)

    # ── STEP 9 ──
    @http.route('/spc/setup-new-company/apply/step9/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def setup_company_apply_step9(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_setup_company_step9', {'service_type': service_type, 'steps': ['Legal type', 'Business activities', 'Company', 'Facility', 'Visa allocation', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Bank account', 'Documents', 'Review', 'Payment'], 'current_step': 9})

    @http.route('/spc/setup-new-company/apply/step9/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def setup_company_apply_step9_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'company_new')
        ubo_count = int(kw.get('ubo_count', 1) or 1)
        files = request.httprequest.files
        ubos = []
        for i in range(1, ubo_count + 1):
            u = {
                'define': kw.get(f'ubo_{i}_def', 'new'),
                'ubo_type': kw.get(f'ubo_{i}_type', 'individual'),
                'first_name': kw.get(f'ubo_{i}_fn', ''),
                'last_name': kw.get(f'ubo_{i}_ln', ''),
                'nationality': kw.get(f'ubo_{i}_nat', ''),
                'stakeholder_type': kw.get(f'ubo_{i}_stake', 'shareholder'),
                'uae_resident': kw.get(f'ubo_{i}_ures', ''),
            }
            for fname in [f'ubo_{i}_pf', f'ubo_{i}_spf']:
                if fname in files and files[fname].filename:
                    f = files[fname]
                    u[fname + '_filename'] = f.filename
                    u[fname + '_data'] = base64.b64encode(f.read()).decode()
            ubos.append(u)
        request.session['spc_step9_data'] = {'ubo_count': ubo_count, 'ubos': ubos}
        _logger.info('=== STEP9 SAVED: count=%s', ubo_count)
        return request.redirect('/spc/setup-new-company/apply/step10/' + service_type)

    # ── STEP 10 ──
    @http.route('/spc/setup-new-company/apply/step10/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def setup_company_apply_step10(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_setup_company_step10', {'service_type': service_type, 'steps': ['Legal type', 'Business activities', 'Company', 'Facility', 'Visa allocation', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Bank account', 'Documents', 'Review', 'Payment'], 'current_step': 10})

    @http.route('/spc/setup-new-company/apply/step10/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def setup_company_apply_step10_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'company_new')
        customer_markets = [kw.get(f'customer_market_{i}', '') for i in range(1, 6) if kw.get(f'customer_market_{i}')]
        supplier_markets = [kw.get(f'supplier_market_{i}', '') for i in range(1, 6) if kw.get(f'supplier_market_{i}')]
        request.session['spc_step10_data'] = {
            'annual_turnover': kw.get('annual_turnover', 0),
            'customer_markets': ', '.join(customer_markets),
            'supplier_markets': ', '.join(supplier_markets),
            'paid_up_capital': kw.get('paid_up_capital', ''),
            'capital_range': kw.get('capital_range', ''),
            'corporate_service_provider': kw.get('corporate_service_provider', ''),
            'has_website': kw.get('has_website', ''),
            'website_url': kw.get('website_url', ''),
            'multinational_group': kw.get('multinational_group', ''),
            'terms_agreed': kw.get('terms_agreed', ''),
            'remarks': kw.get('remarks', ''),
        }
        return request.redirect('/spc/setup-new-company/apply/step11/' + service_type)

    # ── STEP 11 ──
    @http.route('/spc/setup-new-company/apply/step11/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def setup_company_apply_step11(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_setup_company_step11', {'service_type': service_type, 'steps': ['Legal type', 'Business activities', 'Company', 'Facility', 'Visa allocation', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Bank account', 'Documents', 'Review', 'Payment'], 'current_step': 11})

    @http.route('/spc/setup-new-company/apply/step11/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def setup_company_apply_step11_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'company_new')
        request.session['spc_step11_data'] = {
            'need_bank': kw.get('need_bank', ''),
            'bank_provider': kw.get('bank_provider', ''),
        }
        return request.redirect('/spc/setup-new-company/apply/step12/' + service_type)

    # ── STEP 12 ──
    @http.route('/spc/setup-new-company/apply/step12/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def setup_company_apply_step12(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_setup_company_step12', {'service_type': service_type, 'steps': ['Legal type', 'Business activities', 'Company', 'Facility', 'Visa allocation', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Bank account', 'Documents', 'Review', 'Payment'], 'current_step': 12})

    @http.route('/spc/setup-new-company/apply/step12/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def setup_company_apply_step12_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'company_new')
        files = request.httprequest.files
        docs = []
        for field_name, file_obj in files.items():
            if file_obj and file_obj.filename:
                docs.append({
                    'doc_type': field_name,
                    'filename': file_obj.filename,
                    'data': base64.b64encode(file_obj.read()).decode(),
                
            'steps': ['Legal type', 'Business activities', 'Company', 'Facility', 'Visa allocation', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Bank account', 'Documents', 'Review', 'Payment'],
            'current_step': 7,
        })
        request.session['spc_step12_data'] = {'documents': docs}
        return request.redirect('/spc/setup-new-company/apply/step13/' + service_type)

    # ── STEP 13 — REVIEW & DB SAVE ──
    @http.route('/spc/setup-new-company/apply/step13/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def setup_company_apply_step13(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_setup_company_step13', {
            'service_type': service_type,
            's1': request.session.get('spc_apply_step1', {}),
            's2': request.session.get('spc_step2_data', {}),
            's3': request.session.get('spc_step3_data', {}),
            's4': request.session.get('spc_step4_data', {}),
            's5': request.session.get('spc_step5_data', {}),
            's6': request.session.get('spc_step6_data', {}),
            's7': request.session.get('spc_step7_data', {}),
            's8': request.session.get('spc_step8_data', {}),
            's9': request.session.get('spc_step9_data', {}),
            's10': request.session.get('spc_step10_data', {}),
            's11': request.session.get('spc_step11_data', {}),
            's12': request.session.get('spc_step12_data', {}),
            # Also pass with original key names for template compatibility
            'step1': request.session.get('spc_apply_step1', {}),
            'step3': request.session.get('spc_step3_data', {}),
            'step4': request.session.get('spc_step4_data', {}),
            'step5': request.session.get('spc_step5_data', {}),
            'step6': request.session.get('spc_step6_data', {}),
            'step7': request.session.get('spc_step7_data', {}),
            'step10': request.session.get('spc_step10_data', {}),
            'step11': request.session.get('spc_step11_data', {}),
        
            'steps': ['Legal type', 'Business activities', 'Company', 'Facility', 'Visa allocation', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Bank account', 'Documents', 'Review', 'Payment'],
            'current_step': 13,
        })

    @http.route('/spc/setup-new-company/apply/step13/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def setup_company_apply_step13_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'company_new')
        customer_id = request.session.get('spc_selected_customer_id')
        if not customer_id:
            return request.redirect('/spc/dashboard')

        s1  = request.session.get('spc_apply_step1', {})
        s2  = request.session.get('spc_step2_data', {})
        s3  = request.session.get('spc_step3_data', {})
        _logger.info("=== SPC DEBUG s1: %s", s1)
        _logger.info("=== SPC DEBUG s2: %s", s2)
        _logger.info("=== SPC DEBUG s6: %s", request.session.get('spc_step6_data', {}))
        _logger.info("=== SPC DEBUG s7: %s", request.session.get('spc_step7_data', {}))
        _logger.info("=== SPC DEBUG s8: %s", request.session.get('spc_step8_data', {}))
        _logger.info("=== SPC DEBUG s9: %s", request.session.get('spc_step9_data', {}))
        s4  = request.session.get('spc_step4_data', {})
        s5  = request.session.get('spc_step5_data', {})
        s6  = request.session.get('spc_step6_data', {})
        s7  = request.session.get('spc_step7_data', {})
        s8  = request.session.get('spc_step8_data', {})
        s9  = request.session.get('spc_step9_data', {})
        s10 = request.session.get('spc_step10_data', {})
        s11 = request.session.get('spc_step11_data', {})
        s12 = request.session.get('spc_step12_data', {})

        _logger.info('=== COMPANY ID AT SUBMIT: %s', request.session.get('spc_selected_company_id'))
        try:
            app = request.env['spc.company.application'].sudo().create({
                'partner_id': customer_id,
                'approved_company_id': request.session.get('spc_selected_company_id'),
                'service_type': service_type,
                'state': 'submitted',
                'current_step': 13,
                'legal_type': s1.get('legal_type', ''),
                'package_type': s1.get('package_type', ''),
                'license_years': s3.get('license_years', ''),
                'name_reserved': s3.get('name_reserved', ''),
                'reserved_name': s3.get('reserved_name', ''),
                'name_preference_1': s3.get('name_preference_1', ''),
                'name_preference_2': s3.get('name_preference_2', ''),
                'name_preference_3': s3.get('name_preference_3', ''),
                'arabic_translation': s3.get('arabic_translation', ''),
                'facility_type': s4.get('facility_type', ''),
                'visa_count': int(s5.get('visa_count', 0) or 0),
                'shareholder_count': int(s6.get('shareholder_count', 0) or 0),
                'total_shares': int(s6.get('total_shares', 0) or 0),
                'value_per_share': float(s6.get('value_per_share', 0) or 0),
                'manager_count': int(s7.get('manager_count', 0) or 0),
                'director_count': int(s8.get('director_count', 0) or 0),
                'annual_turnover': float(s10.get('annual_turnover', 0) or 0),
                'customer_markets': s10.get('customer_markets', ''),
                'supplier_markets': s10.get('supplier_markets', ''),
                'paid_up_capital': s10.get('paid_up_capital', ''),
                'capital_range': s10.get('capital_range', ''),
                'has_website': s10.get('has_website', ''),
                'website_url': s10.get('website_url', ''),
                'multinational_group': s10.get('multinational_group', ''),
                'corporate_service_provider': s10.get('corporate_service_provider', ''),
                'terms_agreed': bool(s10.get('terms_agreed')),
                'remarks': s10.get('remarks', ''),
                'need_bank': s11.get('need_bank', ''),
                'bank_provider': s11.get('bank_provider', ''),
            })

            # Business Activities
            if s2.get('activity_ids'):
                app.write({'business_activity_ids': [(6, 0, s2['activity_ids'])]})

            # Shareholders
            for sh in s6.get('shareholders', []):
                full_name = (sh.get('first_name', '') + ' ' + sh.get('last_name', '')).strip() or sh.get('entity_name', '')
                sh_rec = request.env['spc.app.shareholder'].sudo().create({
                    'application_id': app.id,
                    'shareholder_type': sh.get('type', 'individual'),
                    'full_name': full_name,
                    'first_name': sh.get('first_name', ''),
                    'last_name': sh.get('last_name', ''),
                    'passport_no': sh.get('passport_no', ''),
                    'nationality': sh.get('nationality', ''),
                    'email': sh.get('email', ''),
                    'mobile': sh.get('mobile', ''),
                    'entity_name': sh.get('entity_name', ''),
                    'entity_reg_no': sh.get('entity_reg_no', ''),
                    'shares_allocated': int(sh.get('shares_allocated', 0) or 0),
                    'total_share_value': float(sh.get('share_value', 0) or 0),
                })
                doc_type_names = {
                    'passport_file': 'Passport Copy',
                    'passport_special': 'Passport Special Page',
                    'visa_file': 'UAE Resident Visa',
                    'eid_file': 'Emirates ID',
                }
                for key in sh:
                    if key.endswith('_filename') and sh.get(key):
                        data_key = key.replace('_filename', '_data')
                        if sh.get(data_key):
                            # key example: sh_1_passport_file_filename → parts[2:] = passport_file
                            parts = key.replace('_filename', '').split('_')
                            doc_key = '_'.join(parts[2:])
                            request.env['spc.app.document'].sudo().create({
                                'application_id': app.id,
                                'doc_type': doc_type_names.get(doc_key, doc_key),
                                'related_to': f'Shareholder: {full_name}',
                                'step': 6,
                                'filename': sh[key],
                                'file': sh[data_key],
                            })

            # Managers
            define_map = {'add_new': 'new', 'shareholder': 'shareholder', 'spc_shareholder': 'spc_entity', 'new': 'new'}
            for mgr in s7.get('managers', []):
                full_name = (mgr.get('first_name', '') + ' ' + mgr.get('last_name', '')).strip()
                request.env['spc.app.manager'].sudo().create({
                    'application_id': app.id,
                    'define_from': {'add_new': 'new', 'shareholder': 'shareholder', 'spc_shareholder': 'spc_entity', 'new': 'new'}.get(mgr.get('define', 'new'), 'new'),
                    'full_name': full_name,
                    'nationality': mgr.get('nationality', ''),
                    'email': mgr.get('email', ''),
                    'mobile': mgr.get('mobile', ''),
                    'has_uae_residence': mgr.get('uae_resident', 'no'),
                })
                mgr_doc_names = {
                    'passport_file': 'Passport Copy',
                    'passport_sp': 'Passport Special Page',
                    'res_visa': 'UAE Resident Visa',
                    'eid': 'Emirates ID',
                    'entry_visa': 'UAE Entry Visa',
                }
                for key in mgr:
                    if key.endswith('_filename') and mgr.get(key):
                        data_key = key.replace('_filename', '_data')
                        if mgr.get(data_key):
                            parts = key.replace('_filename', '').split('_')
                            doc_key = '_'.join(parts[2:])
                            request.env['spc.app.document'].sudo().create({
                                'application_id': app.id,
                                'doc_type': mgr_doc_names.get(doc_key, doc_key),
                                'related_to': f'Manager: {full_name}',
                                'step': 7,
                                'filename': mgr[key],
                                'file': mgr[data_key],
                            })

            # Directors
            dir_define_map = {'add_new': 'new', 'sh': 'shareholder', 'spc': 'spc_entity', 'new': 'new', 'shareholder': 'shareholder'}
            for d in s8.get('directors', []):
                full_name = (d.get('first_name', '') + ' ' + d.get('last_name', '')).strip()
                request.env['spc.app.director'].sudo().create({
                    'application_id': app.id,
                    'define_from': {'add_new': 'new', 'sh': 'shareholder', 'spc': 'spc_entity', 'new': 'new'}.get(d.get('define', 'new'), 'new'),
                    'full_name': full_name,
                    'nationality': d.get('nationality', ''),
                    'email': d.get('email', ''),
                    'mobile': d.get('mobile', ''),
                    'has_uae_residence': d.get('uae_resident', 'no'),
                })
                dir_doc_names = {
                    'pf': 'Passport Copy',
                    'spf': 'Passport Special Page',
                    'rvf': 'UAE Resident Visa',
                    'eidf': 'Emirates ID',
                }
                for key in d:
                    if key.endswith('_filename') and d.get(key):
                        data_key = key.replace('_filename', '_data')
                        if d.get(data_key):
                            parts = key.replace('_filename', '').split('_')
                            doc_key = '_'.join(parts[2:])
                            request.env['spc.app.document'].sudo().create({
                                'application_id': app.id,
                                'doc_type': dir_doc_names.get(doc_key, doc_key),
                                'related_to': f'Director: {full_name}',
                                'step': 8,
                                'filename': d[key],
                                'file': d[data_key],
                            })

            # UBOs
            for u in s9.get('ubos', []):
                full_name = (u.get('first_name', '') + ' ' + u.get('last_name', '')).strip()
                request.env['spc.app.ubo'].sudo().create({
                    'application_id': app.id,
                    'full_name': full_name,
                    'ubo_type': u.get('ubo_type', 'individual'),
                    'nationality': u.get('nationality', ''),
                    'stakeholder_type': u.get('stakeholder_type', 'shareholder'),
                    'has_uae_residence': u.get('uae_resident', 'no'),
                })
                for key in u:
                    if key.endswith('_filename') and u.get(key):
                        data_key = key.replace('_filename', '_data')
                        if u.get(data_key):
                            parts = key.replace('_filename', '').split('_')
                            doc_key = '_'.join(parts[2:])
                            ubo_doc_names = {'pf': 'Passport Copy', 'spf': 'Passport Special Page'}
                            request.env['spc.app.document'].sudo().create({
                                'application_id': app.id,
                                'doc_type': ubo_doc_names.get(doc_key, doc_key),
                                'related_to': f'UBO: {full_name}',
                                'step': 9,
                                'filename': u[key],
                                'file': u[data_key],
                            })

            # Documents (Step 12 - Supporting Documents)
            step_labels = {
                3: 'Step 3: Company Name',
                6: 'Step 6: Shareholders',
                7: 'Step 7: Managers',
                8: 'Step 8: Directors',
                9: 'Step 9: UBO',
                12: 'Step 12: Supporting Documents',
            }
            for doc in s12.get('documents', []):
                request.env['spc.app.document'].sudo().create({
                    'application_id': app.id,
                    'doc_type': doc.get('doc_type', 'supporting_doc'),
                    'related_to': 'Supporting Document',
                    'step': 12,
                    'filename': doc.get('filename', ''),
                    'file': doc.get('data', ''),
                })

            # Reservation doc (Step 3)
            if s3.get('reservation_doc_data'):
                request.env['spc.app.document'].sudo().create({
                    'application_id': app.id,
                    'doc_type': 'Name Reservation Document',
                    'related_to': 'Company Name Reservation',
                    'step': 3,
                    'filename': s3.get('reservation_doc_filename', ''),
                    'file': s3.get('reservation_doc_data', ''),
                })

            # Clear session
            for key in ['spc_apply_step1', 'spc_step2_data', 'spc_step3_data',
                        'spc_step4_data', 'spc_step5_data', 'spc_step6_data',
                        'spc_step7_data', 'spc_step8_data', 'spc_step9_data',
                        'spc_step10_data', 'spc_step11_data', 'spc_step12_data']:
                request.session.pop(key, None)

            request.session['spc_last_application_id'] = app.id
            _logger.info("SPC Application %s created for partner %s", app.reference, customer_id)

        except Exception as e:
            _logger.error("SPC Application create error: %s", str(e), exc_info=True)

        return request.redirect('/spc/setup-new-company/apply/step14/' + service_type)

    # ── STEP 14 ──
    @http.route('/spc/setup-new-company/apply/step14/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def setup_company_apply_step14(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_setup_company_step14', {'service_type': service_type, 'steps': ['Legal type', 'Business activities', 'Company', 'Facility', 'Visa allocation', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Bank account', 'Documents', 'Review', 'Payment'], 'current_step': 14})

    @http.route('/spc/setup-new-company/apply/step14/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def setup_company_apply_step14_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'company_new')
        return request.redirect('/spc/payment/' + service_type)

    # ── COMPANY MANAGEMENT ──
    @http.route('/spc/company-management', type='http', auth='public', website=True, csrf=False)
    def company_management(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        customer_id = request.session.get('spc_selected_customer_id')
        customer = None
        if customer_id:
            rec = request.env['res.partner'].sudo().browse(customer_id)
            if rec.exists():
                customer = rec
        company_id = request.session.get('spc_selected_company_id')
        selected_company = None
        all_companies = []
        if company_id:
            comp = request.env['spc.approved.company'].sudo().browse(company_id)
            if comp.exists():
                selected_company = comp
        if customer_id:
            all_companies = request.env['spc.approved.company'].sudo().search([
                ('partner_id', '=', customer_id), ('active', '=', True),
            ], order='company_name asc')
        return request.render('spc_portal.template_company_management', {
            'customer': customer,
            'allocated_visa': 1, 'available_visa': 1,
            'used_visa': 0, 'in_progress_visa': 0,
            'employees': 0, 'documents': 27, 'key_stakeholders': 3,
            'service_requests': [],
            'steps': ['Legal type', 'Business activities', 'Company', 'Facility', 'Visa allocation', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Bank account', 'Documents', 'Review', 'Payment'],
            'current_step': 14,
            'company_name': selected_company.company_name if selected_company else '',
            'all_companies': all_companies,
            'selected_company_id': company_id,
        })

    # ── NEW REQUEST TRACKING ──
    @http.route('/spc/request-tracking', type='http', auth='public', website=True, csrf=False)
    def request_tracking(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        partner = request.env.user.partner_id
        customer_id = request.session.get('spc_selected_customer_id')
        customer = None
        if customer_id:
            rec = request.env['res.partner'].sudo().browse(customer_id)
            if rec.exists():
                customer = rec
        target_partner = customer or partner

        CUSTOMER_ID_MODELS = [
            'spc.license.reissue', 'spc.renewal', 'spc.renewal.amendment',
            'spc.amendment', 'spc.visa.allocation.amendment',
            'spc.establishment.card', 'spc.certify', 'spc.business.license',
            'spc.corporate.letter',
        ]
        selected_company_id = request.session.get('spc_selected_company_id')
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info(f"DEBUG company_id from session: {selected_company_id}, target_partner_id: {target_partner.id if target_partner else None}")
        def fetch(model):
            try:
                selected_company_id = request.session.get('spc_selected_company_id')
                if model in CUSTOMER_ID_MODELS:
                    domain = [('customer_id', '=', target_partner.id)]
                else:
                    fields_list = request.env[model].sudo().fields_get()
                    if 'partner_id' in fields_list:
                        domain = [('partner_id', '=', target_partner.id)]
                    elif 'customer_id' in fields_list:
                        domain = [('customer_id', '=', target_partner.id)]
                    else:
                        return []
                if 'approved_company_id' in request.env[model].sudo().fields_get() and model != 'spc.document.delivery':
                    if selected_company_id:
                        domain.append(('approved_company_id', '=', int(selected_company_id)))
                    else:
                        domain.append(('approved_company_id', '=', False))
                return request.env[model].sudo().search(domain, order='id desc')
            except Exception as e:
                _logger.error('FETCH ERROR model=%s error=%s', model, e)
                return []

        all_records = []

        service_map = [
            ('spc.company.application',          'Company Formation',          'company',   '/spc/setup-new-company/apply/'),
            ('spc.nma.media.license',            'NMA Media License',          'company',   '/spc/apply/nma_media_license/'),
            ('spc.nma.permit',                   'NMA Permit',                 'company',   '/spc/apply/nma_permit/step1'),
            ('spc.employee.list',                'Employee List',              'employee',  '/spc/apply/employee_list/step1'),
            ('spc.change.of.status',             'Change of Status',           'employee',  '/spc/apply/change_of_status/step1'),
            ('spc.facility.management',          'Facility Management',        'facility',  '/spc/facility-management/apply/new'),
            ('spc.dedicated.account.manager',    'Dedicated Account Manager',  'concierge', '/spc/apply/dam/step1'),
            ('spc.banking.assistance',           'Banking Assistance',         'concierge', '/spc/apply/banking/step1'),
            ('spc.driving.license',              'Driving License',            'concierge', '/spc/concierge/driving-license'),
            ('spc.eid.appointment',              'EID Appointment',            'employee',  '/spc/employee-management/eid-appointment/step1'),
            ('spc.eid.replacement',              'EID Replacement',            'concierge', '/spc/apply/eid_replacement/step1'),
            ('spc.lease.document',               'Lease Document',             'concierge', '/spc/apply/lease_document/step1'),
            ('spc.medical',                      'Medical Service',            'concierge', '/spc/apply/medical/step1'),
            ('spc.meeting.room',                 'Meeting Room Booking',       'facility',  '/spc/apply/meeting_room/step1'),
            ('spc.mofa',                         'MOFA Attestation',           'concierge', '/spc/apply/mofa/step1'),
            ('spc.movement.report',              'Movement Report',            'employee',  '/spc/employee-management/movement-report/step1'),
            ('spc.phone.answering',              'Phone Answering',            'concierge', '/spc/concierge/phone-answering/step1'),
            ('spc.po.box',                       'PO Box',                     'concierge', '/spc/concierge/po-box/step1'),
            ('spc.reentry.permit',               'Re-Entry Permit',            'concierge', '/spc/apply/reentry_permit/step1'),
            ('spc.vip.medical.eid',              'VIP Medical EID',            'concierge', '/spc/concierge/vip-medical-eid/step1'),
            ('spc.company.stamp',                'Company Stamp',              'concierge', '/spc/concierge/company-stamp/step1'),
            ('spc.dependent.visa',               'Dependent Visa',             'concierge', '/spc/concierge/dependent-visa/step1'),
            ('spc.corporate.letter',             'Corporate Letter',           'company',   '/spc/company-management/corporate-letters/step1'),
            ('spc.business.license',             'Business License',           'company',   '/spc/company-management/business-license/bl-step1'),
            ('spc.certify',                      'Certify Document',           'company',   '/spc/company-management/apply/certify-step1/new'),
            ('spc.license.reissue',              'License Reissue',            'company',   '/spc/company-management/apply/lr-step1/new'),
            ('spc.renewal',                      'License Renewal',            'company',   '/spc/company-management/apply/rn-step1/new'),
            ('spc.amendment',                    'Amendment',                  'company',   '/spc/company-management/apply/amd-step1/new'),
            ('spc.renewal.amendment',            'Renewal Amendment',          'company',   '/spc/company-management/apply/ra-step1/new'),
            ('spc.visa.allocation.amendment',    'Visa Allocation Amendment',  'company',   '/spc/company-management/apply/va-step1/new'),
            ('spc.establishment.card',           'Establishment Card',         'company',   '/spc/company-management/apply/ec-new-step1/new'),
            ('spc.name.reservation',             'Name Reservation',           'company',   '/spc/setup-new-company/apply/name_reservation'),
            ('spc.pre.approval',                 'Pre Approval',               'company',   '/spc/setup-new-company/apply/pre_approval'),
            ('spc.uid.merging',                  'UID Merging',                'employee',  '/spc/apply/uid_merging/step1'),
            ('spc.document.delivery',              'Document Delivery',          'concierge', '/spc/concierge/doc-delivery/courier/step1'),
        ]

        for model, label, category, resume_url in service_map:
            for rec in fetch(model):
                state = getattr(rec, 'state', 'draft')
                submission_date = getattr(rec, 'submission_date', None)
                started_date = getattr(rec, 'started_date', None) or getattr(rec, 'create_date', None)
                current_step = getattr(rec, 'current_step', 1)
                name = getattr(rec, 'name', '') or label

                # Build resume URL
                if state == 'draft':
                    if model == 'spc.nma.media.license':
                        lt = getattr(rec, 'license_type', 'new')
                        step = current_step or 1
                        if step <= 1:
                            url = '/spc/apply/nma_media_license/%s?resume_id=%d' % (lt, rec.id)
                        elif step >= 6:
                            url = '/spc/apply/nma_media_license/%s/step6?resume_id=%d' % (lt, rec.id)
                        else:
                            url = '/spc/apply/nma_media_license/%s/step%d?resume_id=%d' % (lt, step, rec.id)
                    elif model == 'spc.service.request':
                        step = current_step or 1
                        service = getattr(rec, 'service_type', 'company_new') or 'company_new'
                        if step <= 1:
                            url = '/spc/setup-new-company/apply/%s' % service
                        else:
                            url = '/spc/setup-new-company/apply/step%d/%s' % (step, service)
                    elif model == 'spc.license.reissue':
                        step = current_step or 2
                        st = getattr(rec, 'service_type', 'license_reissue') or 'license_reissue'
                        url = '/spc/company-management/apply/lr-step%d/%s?resume_id=%d' % (min(step, 4), st, rec.id)
                    elif model == 'spc.renewal':
                        step = current_step or 2
                        st = getattr(rec, 'service_type', 'renewal') or 'renewal'
                        url = '/spc/company-management/apply/rn-step%d/%s?resume_id=%d' % (min(step, 4), st, rec.id)
                    elif model == 'spc.renewal.amendment':
                        step = current_step or 2
                        st = getattr(rec, 'service_type', 'renewal_amendment') or 'renewal_amendment'
                        url = '/spc/company-management/apply/ra-step%d/%s?resume_id=%d' % (min(step, 4), st, rec.id)
                    elif model == 'spc.amendment':
                        step = current_step or 2
                        st = getattr(rec, 'service_type', 'amendment') or 'amendment'
                        url = '/spc/company-management/apply/amd-step%d/%s?resume_id=%d' % (min(step, 4), st, rec.id)
                    elif model == 'spc.visa.allocation.amendment':
                        step = current_step or 2
                        st = getattr(rec, 'service_type', 'visa_allocation_amendment') or 'visa_allocation_amendment'
                        url = '/spc/company-management/apply/va-step%d/%s?resume_id=%d' % (min(step, 4), st, rec.id)
                    elif model == 'spc.establishment.card':
                        url = '/spc/company-management/apply/ec-new-step1/new?resume_id=%d' % rec.id
                    elif model == 'spc.certify':
                        step = current_step or 2
                        st = getattr(rec, 'service_type', 'certify') or 'certify'
                        url = '/spc/company-management/apply/certify-step%d/%s?resume_id=%d' % (min(step, 2), st, rec.id)
                    elif model == 'spc.business.license':
                        url = '/spc/company-management/business-license/bl-step%d?resume_id=%d' % (min(current_step or 2, 10), rec.id)
                    elif model == 'spc.corporate.letter':
                        url = '/spc/company-management/corporate-letters/step%d?resume_id=%d' % (min(current_step or 2, 2), rec.id)
                    elif model == 'spc.license.reissue':
                        step = current_step or 2
                        st = getattr(rec, 'service_type', 'license_reissue') or 'license_reissue'
                        url = '/spc/company-management/apply/lr-step%d/%s?resume_id=%d' % (min(step, 4), st, rec.id)
                    elif model == 'spc.renewal':
                        step = current_step or 2
                        st = getattr(rec, 'service_type', 'renewal') or 'renewal'
                        url = '/spc/company-management/apply/rn-step%d/%s?resume_id=%d' % (min(step, 4), st, rec.id)
                    elif model == 'spc.renewal.amendment':
                        step = current_step or 2
                        st = getattr(rec, 'service_type', 'renewal_amendment') or 'renewal_amendment'
                        url = '/spc/company-management/apply/ra-step%d/%s?resume_id=%d' % (min(step, 4), st, rec.id)
                    elif model == 'spc.amendment':
                        step = current_step or 2
                        st = getattr(rec, 'service_type', 'amendment') or 'amendment'
                        url = '/spc/company-management/apply/amd-step%d/%s?resume_id=%d' % (min(step, 4), st, rec.id)
                    elif model == 'spc.visa.allocation.amendment':
                        step = current_step or 2
                        st = getattr(rec, 'service_type', 'visa_allocation_amendment') or 'visa_allocation_amendment'
                        url = '/spc/company-management/apply/va-step%d/%s?resume_id=%d' % (min(step, 4), st, rec.id)
                    elif model == 'spc.establishment.card':
                        url = '/spc/company-management/apply/ec-new-step1/new?resume_id=%d' % rec.id
                    elif model == 'spc.certify':
                        step = current_step or 2
                        st = getattr(rec, 'service_type', 'certify') or 'certify'
                        url = '/spc/company-management/apply/certify-step%d/%s?resume_id=%d' % (min(step, 2), st, rec.id)
                    elif model == 'spc.business.license':
                        url = '/spc/company-management/business-license/bl-step%d?resume_id=%d' % (min(current_step or 2, 10), rec.id)
                    elif model == 'spc.corporate.letter':
                        url = '/spc/company-management/corporate-letters/step%d?resume_id=%d' % (min(current_step or 2, 2), rec.id)
                    elif model == 'spc.change.of.status':
                        url = '/spc/apply/change_of_status/step%d?resume_id=%d' % (min(current_step or 1, 4), rec.id)
                    else:
                        url = resume_url
                else:
                    url = None

                all_records.append({
                    'id': rec.id,
                    'name': name,
                    'label': label,
                    'category': category,
                    'state': state,
                    'submission_date': submission_date,
                    'started_date': started_date,
                    'current_step': current_step,
                    'resume_url': url,
                    'fees': getattr(rec, 'total_amount', 0.0) or 0.0,
                    'detail_url': '/spc/request-tracking/detail/%s/%d' % (model.replace('.', '_'), rec.id) if state != 'draft' else None,
                })

        # Sort by started_date desc
        all_records.sort(key=lambda x: x['started_date'] or '', reverse=True)

        pending_docs = request.env['spc.pending.details.doc'].sudo().search([
            ('partner_id', '=', target_partner.id),
            ('state', 'in', ['sent', 'submitted']),
        ], order='create_date desc')

        company_id = request.session.get('spc_selected_company_id')
        selected_company = None
        all_companies = []
        if customer_id:
            all_companies = request.env['spc.approved.company'].sudo().search([
                ('partner_id', '=', customer_id), ('active', '=', True),
            ], order='company_name asc')
        if company_id:
            comp = request.env['spc.approved.company'].sudo().browse(company_id)
            if comp.exists():
                selected_company = comp
        return request.render('spc_portal.template_request_tracking', {
            'customer': target_partner,
            'all_records': all_records,
            'pending_docs': pending_docs,
            'company_name': selected_company.company_name if selected_company else '',
            'all_companies': all_companies,
            'selected_company_id': company_id,
        })

    # ── OLD REQUEST TRACKING (commented out - replaced by new system) ──
    # @http.route('/spc/request-tracking', type='http', auth='public', website=True, csrf=False)
    # def request_tracking(self, **kw):
    #     if not self._check_spc_session():
    #         return request.redirect('/spc/login')
    #     customer_id = request.session.get('spc_selected_customer_id')
    #     customer = None
    #     requests_list = []
    #     if customer_id:
    #         rec = request.env['res.partner'].sudo().browse(customer_id)
    #         if rec.exists():
    #             customer = rec
    #             requests_list = request.env['spc.service.request'].sudo().search([
    #                 ('partner_id', '=', customer.id)
    #             ], order='create_date desc')
    #     pending_docs = []
    #     if customer:
    #         pending_docs = request.env['spc.pending.details.doc'].sudo().search([
    #             ('partner_id', '=', customer.id),
    #             ('state', 'in', ['sent', 'submitted']),
    #         ], order='create_date desc')
    #     return request.render('spc_portal.template_request_tracking', {
    #         'customer': customer,
    #         'requests': requests_list,
    #         'pending_docs': pending_docs,
    #     })

    # ── NR STEPS ──
    @http.route('/spc/setup-new-company/apply/nr-step2/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def nr_step2(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        customer_id = request.session.get('spc_selected_customer_id')
        customer = None
        if customer_id:
            rec = request.env['res.partner'].sudo().browse(customer_id)
            if rec.exists():
                customer = rec
        return request.render('spc_portal.template_nr_step2', {'service_type': service_type, 'form_data': {}, 'errors': [], 'customer': customer})

    @http.route('/spc/pending-docs/submit/<int:doc_id>', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def pending_doc_submit(self, doc_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        pending = request.env['spc.pending.details.doc'].sudo().browse(doc_id)
        if not pending.exists():
            return request.redirect('/spc/request-tracking')

        # Block resubmission
        if pending.is_submitted:
            return request.redirect('/spc/request-tracking?already_submitted=1')

        pending_details = kw.get('pending_details', '')

        received = request.env['spc.received.details'].sudo().create({
            'pending_id': pending.id,
            'pending_details': pending_details,
        })

        import base64
        files = request.httprequest.files
        for line in pending.document_line_ids:
            file_key = 'doc_%d' % line.id
            if file_key in files:
                f = files[file_key]
                if f.filename:
                    data = base64.b64encode(f.read())
                    request.env['spc.received.doc.line'].sudo().create({
                        'received_id': received.id,
                        'sequence': line.sequence,
                        'name': line.name,
                        'document': data,
                        'document_filename': f.filename,
                    })

        pending.sudo().write({'is_submitted': True, 'state': 'submitted'})
        return request.redirect('/spc/request-tracking?submitted=1')

    @http.route('/spc/setup-new-company/apply/nr-step2/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def nr_step2_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'name_reservation')
        request.session['nr_step2_data'] = kw
        return request.redirect(f'/spc/setup-new-company/apply/nr-step3/{service_type}')

    @http.route('/spc/setup-new-company/apply/nr-step3/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def nr_step3(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_nr_step3', {'service_type': service_type})

    @http.route('/spc/setup-new-company/apply/nr-step3/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def nr_step3_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'name_reservation')
        request.session['nr_step3_data'] = kw
        return request.redirect(f'/spc/setup-new-company/apply/nr-step4/{service_type}')

    @http.route('/spc/setup-new-company/apply/nr-step4/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def nr_step4(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_nr_step4', {
            'service_type': service_type,
            'step2': request.session.get('nr_step2_data', {}),
            'step3': request.session.get('nr_step3_data', {}),
        })

    @http.route('/spc/setup-new-company/apply/nr-step4/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def nr_step4_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'name_reservation')
        # Save to DB
        try:
            customer_id = request.session.get('spc_selected_customer_id')
            step2_data = request.session.get('nr_step2_data', {})
            step3_data = request.session.get('nr_step3_data', {})
            activity_data = request.session.get('spc_step2_data', {})
            activity_ids = activity_data.get('activity_ids', [])
            activity_names = activity_data.get('activity_names', [])
            vals = {
                'customer_id': customer_id,
                'approved_company_id': request.session.get('spc_selected_company_id'),
                'state': 'submitted',
                'activity_names': ', '.join(activity_names) if activity_names else '',
                'name_reserved': step2_data.get('name_reserved', 'no'),
                'reserved_name': step2_data.get('reserved_name', ''),
                'name_preference_1': step2_data.get('name_preference_1', ''),
                'name_preference_2': step2_data.get('name_preference_2', ''),
                'name_preference_3': step2_data.get('name_preference_3', ''),
                'translation_method': step2_data.get('translation_method', ''),
                'declaration_accepted': bool(step3_data.get('declaration_accepted')),
                'declarant_name': step3_data.get('declarant_name', ''),
                'approved_company_id': request.session.get('spc_selected_company_id'),
                'fee': 500.0,
                'payment_status': 'pending',
            }
            nr = request.env['spc.name.reservation'].sudo().create(vals)
            if activity_ids:
                nr.business_activity_ids = [(6, 0, activity_ids)]
            # Clear session
            for key in ['nr_step2_data', 'nr_step3_data', 'spc_step2_data']:
                request.session.pop(key, None)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"NR save error: {e}")
        return request.redirect(f'/spc/setup-new-company/apply/nr-step5/{service_type}')

    @http.route('/spc/setup-new-company/apply/nr-step5/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def nr_step5(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.redirect('/spc/payment/' + service_type)

    # ══ PRE-APPROVAL FLOW ══

    @http.route('/spc/setup-new-company/apply/pa-step2/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def pa_step2(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        all_activities = request.env['spc.business.activity'].sudo().search([])
        fees_map = {'pre_approval': 640}
        categories = [
            ('publishing_media', 'Publishing and Media'),
            ('wholesale_retail', 'Wholesale and Retail'),
            ('services_consultancy', 'Services and Consultancy'),
            ('electronic_publishing', 'Electronic Publishing'),
            ('real_publishing', 'Real Publishing'),
        ]
        activities_data = {}
        for cat_key, cat_label in categories:
            cat_acts = all_activities.filtered(lambda a: a.category == cat_key)
            divisions = {}
            for act in cat_acts:
                div = act.division or 'General'
                if div not in divisions:
                    divisions[div] = []
                divisions[div].append({'id': act.id, 'code': act.code, 'name': act.name})
            activities_data[cat_key] = {'label': cat_label, 'divisions': divisions}
        if not any(activities_data[k]['divisions'] for k in activities_data):
            divisions = {}
            for act in all_activities:
                div = act.division or act.category or 'General'
                if div not in divisions:
                    divisions[div] = []
                divisions[div].append({'id': act.id, 'code': act.code or str(act.id), 'name': act.name})
            activities_data['all'] = {'label': 'All Activities', 'divisions': divisions}
            categories = [('all', 'All Activities')]
        pa_steps = ['Business activities', 'Company name', 'Shareholder details', 'Declaration', 'Review application', 'Payment']
        return request.render('spc_portal.template_setup_company_step2', {
            'service_type': service_type,
            'activities_data': activities_data,
            'categories': categories,
            'fee': fees_map.get(service_type, 640),
            'steps': pa_steps,
            'current_step': 1,
        })

    @http.route('/spc/setup-new-company/apply/pa-step2/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def pa_step2_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'pre_approval')
        activity_names = request.httprequest.form.getlist('business_activities')
        activity_ids = []
        if activity_names:
            acts = request.env['spc.business.activity'].sudo().search([('name', 'in', activity_names)])
            activity_ids = acts.ids
        request.session['pa_step2_data'] = {'activity_ids': activity_ids, 'activity_names': activity_names}
        return request.redirect('/spc/setup-new-company/apply/pa-step3/' + service_type)

    @http.route('/spc/setup-new-company/apply/pa-step3/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def pa_step3(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_pa_step3', {
            'service_type': service_type,
            'form_data': request.session.get('pa_step3_data', {}),
        })

    @http.route('/spc/setup-new-company/apply/pa-step3/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def pa_step3_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'pre_approval')
        request.session['pa_step3_data'] = dict(kw)
        return request.redirect('/spc/setup-new-company/apply/pa-step4/' + service_type)

    @http.route('/spc/setup-new-company/apply/pa-step4/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def pa_step4(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        customer_id = request.session.get('spc_selected_customer_id')
        customer = None
        if customer_id:
            rec = request.env['res.partner'].sudo().browse(customer_id)
            if rec.exists():
                customer = rec
        countries = request.env['res.country'].sudo().search([])
        existing_data = request.session.get('pa_step4_data', {})
        url_count = request.params.get('shareholder_count') or kw.get('shareholder_count')
        sh_count = max(1, min(int(url_count), 20)) if url_count else 1
        name_parts = (customer.name or '').split(' ', 1) if customer else ['', '']
        customer_info = {
            'first_name': name_parts[0] if name_parts else '',
            'last_name': name_parts[1] if len(name_parts) > 1 else '',
            'email': customer.email or '' if customer else '',
            'mobile': (customer.mobile or customer.phone or '') if customer else '',
            'nationality': customer.country_id.code if customer and customer.country_id else '',
        }
        return request.render('spc_portal.template_setup_company_step6', {
            'service_type': service_type,
            'form_data': existing_data,
            'errors': [],
            'customer_info': customer_info,
            'sh_count': sh_count,
            'sh_range': list(range(1, sh_count + 1)),
            'steps': ['Business activities', 'Company name', 'Shareholder details', 'Declaration', 'Review application', 'Payment'],
            'current_step': 3,
            'form_submit_url': '/spc/setup-new-company/apply/pa-step4/submit',
            'step_base_url': '/spc/setup-new-company/apply/pa-step4/',
        })

    @http.route('/spc/setup-new-company/apply/pa-step4/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def pa_step4_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'pre_approval')
        # Save only text fields, skip file uploads
        safe_data = {k: v for k, v in kw.items() if isinstance(v, str)}
        request.session['pa_step4_data'] = safe_data
        # Save uploaded files to temp session as base64
        import base64
        file_docs = []
        files = request.httprequest.files
        for field_name in files:
            f = files[field_name]
            if f and f.filename:
                file_data = base64.b64encode(f.read()).decode('utf-8')
                file_docs.append({
                    'name': field_name,
                    'filename': f.filename,
                    'data': file_data,
                })
        request.session['pa_step4_files'] = file_docs
        return request.redirect('/spc/setup-new-company/apply/pa-step5/' + service_type)

    @http.route('/spc/setup-new-company/apply/pa-step5/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def pa_step5(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_pa_step5', {
            'service_type': service_type,
            'form_data': request.session.get('pa_step5_data', {}),
            'steps': ['Business activities', 'Company name', 'Shareholder details', 'Declaration', 'Review application', 'Payment'],
            'current_step': 4,
        })

    @http.route('/spc/setup-new-company/apply/pa-step5/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def pa_step5_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'pre_approval')
        request.session['pa_step5_data'] = dict(kw)
        return request.redirect('/spc/setup-new-company/apply/pa-step6/' + service_type)

    @http.route('/spc/setup-new-company/apply/pa-step6/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def pa_step6(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        step2 = request.session.get('pa_step2_data') or {}
        step3 = request.session.get('pa_step3_data') or {}
        step4 = request.session.get('pa_step4_data') or {}
        step5 = request.session.get('pa_step5_data') or {}
        # Ensure dicts
        if not isinstance(step2, dict): step2 = {}
        if not isinstance(step3, dict): step3 = {}
        if not isinstance(step4, dict): step4 = {}
        if not isinstance(step5, dict): step5 = {}
        return request.render('spc_portal.template_pa_step6', {
            'service_type': service_type,
            'step2': step2, 'step3': step3, 'step4': step4, 'step5': step5,
        })

    @http.route('/spc/setup-new-company/apply/pa-step6/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def pa_step6_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'pre_approval')
        return request.redirect('/spc/setup-new-company/apply/pa-payment/' + service_type)

    @http.route('/spc/setup-new-company/apply/pa-payment/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def pa_payment(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.redirect('/spc/setup-new-company/apply/pa-payment/submit?service_type=' + service_type)

    @http.route('/spc/setup-new-company/apply/pa-payment/submit', type='http', auth='public', website=True, csrf=False, methods=['POST', 'GET'])
    def pa_payment_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'pre_approval')
        pa = None
        try:
            customer_id = request.session.get('spc_selected_customer_id')
            step2_data = request.session.get('pa_step2_data') or {}
            step3_data = request.session.get('pa_step3_data') or {}
            step4_data = request.session.get('pa_step4_data') or {}
            activity_data = request.session.get('pa_step2_data') or {}
            activity_ids = activity_data.get('activity_ids', [])
            import logging
            _logger = logging.getLogger(__name__)
            _logger.info(f"PA SAVE DEBUG: activity_ids={activity_ids}, step3={step3_data}, step4_keys={list(step4_data.keys())}")
            activity_names = activity_data.get('activity_names', [])
            # step6 shareholder form field names
            step5_data = request.session.get('pa_step5_data') or {}
            vals = {
                'customer_id': customer_id,
                'approved_company_id': request.session.get('spc_selected_company_id'),
                'state': 'submitted',
                'activity_names': ', '.join(activity_names) if activity_names else '',
                'name_reserved': step3_data.get('name_reserved', 'no'),
                'reserved_name': step3_data.get('reserved_name', ''),
                'name_preference_1': step3_data.get('name_preference_1', ''),
                'name_preference_2': step3_data.get('name_preference_2', ''),
                'name_preference_3': step3_data.get('name_preference_3', ''),
                'translation_method': step3_data.get('translation_method', ''),
                # step6 shareholder fields use sh_1_ prefix
                'sh_first_name': step4_data.get('sh_1_first_name', ''),
                'sh_last_name': step4_data.get('sh_1_last_name', ''),
                'sh_nationality': step4_data.get('sh_1_nationality', ''),
                'sh_email': step4_data.get('sh_1_email_id', '') or step4_data.get('sh_1_email', ''),
                'sh_mobile': step4_data.get('sh_1_mobile', ''),
                'sh_passport': step4_data.get('sh_1_passport_no', '') or step4_data.get('sh_1_passport_search', ''),
                'sh_uae_resident': 'yes' if step4_data.get('sh_1_uae_visa') else 'no',
                'sh_percent': float(step4_data.get('sh_1_percent', 0) or 0),
                'declaration_accepted': bool(step5_data.get('declaration_accepted')),
                'declarant_name': step5_data.get('declarant_name', ''),
                'approved_company_id': request.session.get('spc_selected_company_id'),
                'fee': 640.0,

                'payment_method': kw.get('payment_method', ''),
                'payment_status': 'paid',
                'fee': float(kwargs.get('amount', 0)) or 0.0,
            }
            pa = request.env['spc.pre.approval'].sudo().create(vals)
            if activity_ids:
                pa.business_activity_ids = [(6, 0, activity_ids)]
            # Save uploaded documents
            file_docs = request.session.get('pa_step4_files', [])
            import base64
            for doc in file_docs:
                if doc.get('data'):
                    field_name = doc.get('name', '')
                    if 'passport' in field_name:
                        doc_type = 'passport'
                    elif 'visa' in field_name:
                        doc_type = 'visa'
                    elif 'eid' in field_name:
                        doc_type = 'emirates_id'
                    else:
                        doc_type = 'other'
                    doc_display_name = field_name.replace('sh_1_', '').replace('_', ' ').title()
                    request.env['spc.pa.document'].sudo().create({
                        'pa_id': pa.id,
                        'document_name': doc_display_name,
                        'document_type': doc_type,
                        'file_name': doc.get('filename', ''),
                        'file_data': doc.get('data', ''),
                    })
            for key in ['pa_step2_data', 'pa_step3_data', 'pa_step4_data', 'pa_step5_data', 'pa_step4_files']:
                request.session.pop(key, None)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"PA save error: {e}")
        return request.redirect('/spc/payment/' + service_type + '/' + str(pa.id if pa else 0))

    @http.route('/spc/setup-new-company/apply/pa-success/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def pa_success(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.redirect('/spc/payment/' + service_type)

    # ══ LICENSE REISSUE FLOW ══
    @http.route('/spc/company-management/service/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def company_mgmt_service_detail(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        services = {
            'license_reissue': {
                'name': 'Company Formation - License Reissue',
                'description': 'License Reissue',
                'tag': 'New',
                'title': 'License Reissue',
            },
            'renewal': {
                'name': 'Company Formation - Renewal only',
                'description': 'Renewal only',
                'tag': 'Renew',
                'title': 'Renewal',
            },
            'amendment': {
                'name': 'Company Formation - Amendment',
                'description': 'Amendment',
                'tag': 'Amend',
                'title': 'Amendment',
                'banner_style': 'background:linear-gradient(135deg,#2d3a5a,#4a4a4a);',
                'banner_html': '<div style="background:#1a2340;padding:8px 24px;border-radius:4px;font-size:20px;margin-bottom:16px">Amend</div><div style="font-size:64px;font-weight:900">Formation</div>',
                'desc_html': '''<div class="desc-text"><p style="margin-bottom:12px">An amendment updates a company&#39;s details to reflect changes in name, business activity, shareholders, managers, director details, or other relevant information.</p><p style="margin-bottom:8px"><strong>Requirements</strong></p><ol style="margin-left:20px;margin-top:8px;margin-bottom:16px"><li>Amendment Form and Renewal form (if applicable)</li><li>Board Resolution</li><li>Original Company Documents (If applicable)</li><li>Authorization Form (If applicable)</li><li>Pre-Approval (If applicable)</li><li>Passport Copies of all Managers (If applicable)</li><li>UAE Visa Copy or UAE Entry Stamp Copy of all Managers (if applicable)</li><li>Parent Company Documents (If corporate shareholder) (BOR, COI, COGS, Memorandum, etc)</li><li>Passport Copy of Authorized Person (If applicable)</li><li>Power of Attorney (If applicable)</li><li>Payment</li></ol><p style="margin-bottom:8px"><strong>Output documents</strong></p><ol style="margin-left:20px;margin-top:8px;margin-bottom:16px"><li>Trade License (If applicable)</li><li>Certificate of Incorporation (if applicable)</li><li>Share Certificate (if applicable)</li><li>Lease Agreement (If applicable)</li><li>Memorandum (If applicable)</li><li>Visa Allocation Certificate (If Applicable)</li><li>Payment Receipt</li></ol><p style="margin-bottom:8px"><strong>Output documents (Collection)</strong></p><p style="margin-bottom:16px">Electronic Documents are to be collected</p><p style="margin-bottom:8px"><strong>Timeline</strong></p><p style="margin-bottom:16px">1 to 2 business days</p><p style="margin-bottom:8px"><strong>Fees</strong></p><p>AED 2,200 + Applicable Activity + Applicable Visa Allocation Fee (if applicable)</p></div>''',
            },
            'renewal_amendment': {
                'name': 'Company Formation - Renewal with Amendment',
                'description': 'Renewal with Amendments',
                'tag': 'Renew',
                'title': 'Renewal with Amendments',
                'banner_style': 'background:linear-gradient(135deg,#1a7a6e,#1a2340);',
                'banner_html': '<div style="background:#1a2340;padding:8px 24px;border-radius:4px;font-size:20px;margin-bottom:16px">Renew</div><div style="font-size:48px;font-weight:900">Renewal with</div><div style="font-size:48px;font-weight:900">Amendments</div>',
                'desc_html': '''<div class="desc-text"><p style="margin-bottom:16px"><strong>Renewal</strong></p><p style="margin-bottom:12px">A renewal extends the validity of a company&#39;s business license within SPC Free Zone.</p><p style="margin-bottom:8px"><strong>Requirements</strong></p><ol style="margin-left:20px;margin-top:8px;margin-bottom:16px"><li>Renewal Form</li><li>Authorized Signatory Form (if applicable)</li><li>Authorization Form (if applicable)</li><li>Pre-Approval (if applicable)</li><li>Passport Copies of all Managers (if expired)</li><li>UAE Visa Copy or UAE Entry Stamp Copy of all Managers (if applicable)</li><li>Parent Company Documents (If corporate Manager) (BOR, COI, COGS, Memorandum etc)</li><li>Passport Copy of Authorized Person (If applicable)</li><li>Two (2) Passport-sized Photos of all Managers (if applicable)</li><li>Declaration for Activities (If applicable)</li><li>Declaration of Legal and Regulatory (if applicable)</li><li>CV/Degree of Manager (If applicable)</li><li>Payment</li></ol><p style="margin-bottom:8px"><strong>Output documents</strong></p><ol style="margin-left:20px;margin-top:8px;margin-bottom:16px"><li>Trade License</li><li>Lease Agreement (If applicable)</li><li>Payment Receipt</li></ol><p style="margin-bottom:8px"><strong>Output documents (Collection)</strong></p><p style="margin-bottom:16px">Electronic Documents are not required to be collected.</p><p style="margin-bottom:8px"><strong>Timeline</strong></p><p style="margin-bottom:16px">1 to 2 business days</p><p style="margin-bottom:8px"><strong>Fees</strong></p><p>As per package</p></div>''',
            },
        }
        from markupsafe import Markup
        service = services.get(service_type, {})
        if service.get('banner_html'):
            service['banner_html'] = Markup(service['banner_html'])
        if service.get('desc_html'):
            service['desc_html'] = Markup(service['desc_html'])
        return request.render('spc_portal.template_company_mgmt_service_detail', {
            'service_type': service_type,
            'service': service,
        })

    @http.route('/spc/company-management/apply/lr-step1/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def lr_step1(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        customer_id = request.session.get('spc_selected_customer_id')
        companies = []
        if customer_id:
            partner = request.env['res.partner'].sudo().browse(customer_id)
            if partner.exists() and partner.child_ids:
                companies = partner.child_ids.filtered(lambda c: c.active).mapped(lambda c: {'id': c.id, 'name': c.name})
        return request.render('spc_portal.template_lr_step1', {
            'service_type': service_type,
            'companies': companies,
        })

    @http.route('/spc/company-management/apply/lr-step1/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def lr_step1_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'license_reissue')
        request.session['lr_step1_data'] = {
            'idn_company_id': kw.get('idn_company_id', ''),
            'idn_number': kw.get('idn_number', ''),
        }
        try:
            from odoo.fields import Datetime
            _cid = request.session.get('spc_selected_customer_id')
            _vals = {'customer_id': _cid, 'approved_company_id': request.session.get('spc_selected_company_id'), 'state': 'draft', 'idn_number': kw.get('idn_number', '')}
            if kw.get('idn_company_id'):
                try: _vals['idn_company_id'] = int(kw.get('idn_company_id'))
                except: pass
            _lr = request.env['spc.license.reissue'].sudo().create(_vals)
            request.session['lr_draft_id'] = _lr.id
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"LR draft create error: {e}", exc_info=True)
        return request.redirect('/spc/company-management/apply/lr-step2/' + service_type)

    @http.route('/spc/company-management/apply/lr-step2/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def lr_step2(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_lr_step2', {
            'service_type': service_type,
        })

    @http.route('/spc/company-management/apply/lr-step2/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def lr_step2_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'license_reissue')
        request.session['lr_step2_data'] = {k: v for k, v in kw.items() if isinstance(v, str)}
        return request.redirect('/spc/company-management/apply/lr-step3/' + service_type)

    @http.route('/spc/company-management/apply/lr-step3/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def lr_step3(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        all_activities = request.env['spc.business.activity'].sudo().search([])
        categories = [
            ('publishing_media', 'Publishing and Media'),
            ('wholesale_retail', 'Wholesale and Retail'),
            ('services_consultancy', 'Services and Consultancy'),
            ('electronic_publishing', 'Electronic Publishing'),
            ('real_publishing', 'Real Publishing'),
        ]
        activities_data = {}
        for cat_key, cat_label in categories:
            cat_acts = all_activities.filtered(lambda a: a.category == cat_key)
            divisions = {}
            for act in cat_acts:
                div = act.division or 'General'
                if div not in divisions:
                    divisions[div] = []
                divisions[div].append({'id': act.id, 'code': act.code or str(act.id), 'name': act.name})
            activities_data[cat_key] = {'label': cat_label, 'divisions': divisions}
        if not any(activities_data[k]['divisions'] for k in activities_data):
            divisions = {}
            for act in all_activities:
                div = act.division or act.category or 'General'
                if div not in divisions:
                    divisions[div] = []
                divisions[div].append({'id': act.id, 'code': act.code or str(act.id), 'name': act.name})
            activities_data['all'] = {'label': 'All Activities', 'divisions': divisions}
            categories = [('all', 'All Activities')]
        return request.render('spc_portal.template_lr_step3', {
            'service_type': service_type,
            'activities_data': activities_data,
            'categories': categories,
            'fee': 0,
            'steps': ['IDN details', 'Legal type', 'Business activities', 'Review application', 'Payment'],
            'current_step': 3,
        })

    @http.route('/spc/company-management/apply/lr-step3/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def lr_step3_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'license_reissue')
        activity_names = request.httprequest.form.getlist('business_activities')
        activity_ids = []
        if activity_names:
            acts = request.env['spc.business.activity'].sudo().search([('name', 'in', activity_names)])
            activity_ids = acts.ids
        request.session['lr_step3_data'] = {'activity_ids': activity_ids, 'activity_names': activity_names}
        return request.redirect('/spc/company-management/apply/lr-step4/' + service_type)

    @http.route('/spc/company-management/apply/lr-step4/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def lr_step4(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        step1 = request.session.get('lr_step1_data', {})
        step2 = request.session.get('lr_step2_data', {})
        step3 = request.session.get('lr_step3_data', {})
        return request.render('spc_portal.template_lr_step4', {
            'service_type': service_type,
            'step1': step1, 'step2': step2, 'step3': step3,
        })

    @http.route('/spc/company-management/apply/lr-step4/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def lr_step4_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'license_reissue')
        return request.redirect('/spc/company-management/apply/lr-payment/' + service_type)

    @http.route('/spc/company-management/apply/lr-payment/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def lr_payment(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_lr_payment', {
            'service_type': service_type,
            'steps': ['IDN details', 'Legal type', 'Business activities', 'Review application', 'Payment'],
            'current_step': 5,
        })

    @http.route('/spc/company-management/apply/lr-payment/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def lr_payment_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'license_reissue')
        try:
            customer_id = request.session.get('spc_selected_customer_id')
            step1 = request.session.get('lr_step1_data', {})
            step2 = request.session.get('lr_step2_data', {})
            step3 = request.session.get('lr_step3_data', {})
            activity_ids = step3.get('activity_ids', [])
            idn_company_id = step1.get('idn_company_id')
            vals = {
                'customer_id': customer_id,
                'approved_company_id': request.session.get('spc_selected_company_id'),
                'state': 'submitted',
                'idn_number': step1.get('idn_number', ''),
                'legal_type': step2.get('legal_type', ''),
                'package_type': step2.get('package_type', ''),
                'activity_names': ', '.join(step3.get('activity_names', [])),

                'payment_method': kw.get('payment_method', ''),
                'payment_status': 'paid',
                'fee': float(kw.get('amount', 0)) or 0.0,
            }
            if idn_company_id:
                try:
                    vals['idn_company_id'] = int(idn_company_id)
                except:
                    pass
            draft_id = request.session.get('lr_draft_id')
            if draft_id:
                lr = request.env['spc.license.reissue'].sudo().browse(draft_id)
                if lr.exists():
                    lr.sudo().write(vals)
                else:
                    lr = request.env['spc.license.reissue'].sudo().create(vals)
            else:
                lr = request.env['spc.license.reissue'].sudo().create(vals)
            if activity_ids:
                lr.business_activity_ids = [(6, 0, activity_ids)]
            for key in ['lr_step1_data', 'lr_step2_data', 'lr_step3_data', 'lr_draft_id']:
                request.session.pop(key, None)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"LR save error: {e}")
        return request.redirect('/spc/payment/' + service_type)

    # ══ RENEWAL FLOW ══
    @http.route('/spc/company-management/apply/rn-step1/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def rn_step1(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        customer_id = request.session.get('spc_selected_customer_id')
        companies = []
        if customer_id:
            partner = request.env['res.partner'].sudo().browse(customer_id)
            if partner.exists():
                companies = [{'id': partner.id, 'name': partner.name}]
                if partner.child_ids:
                    companies += partner.child_ids.filtered(lambda c: c.active).mapped(lambda c: {'id': c.id, 'name': c.name})
        return request.render('spc_portal.template_rn_step1', {
            'service_type': service_type,
            'companies': companies,
        })

    @http.route('/spc/company-management/apply/rn-step1/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def rn_step1_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'renewal')
        request.session['rn_step1_data'] = {
            'company_id': kw.get('company_id', ''),
            'company_name': kw.get('company_name', ''),
        }
        try:
            from odoo.fields import Datetime
            _cid = request.session.get('spc_selected_customer_id')
            _vals = {'customer_id': _cid, 'approved_company_id': request.session.get('spc_selected_company_id'), 'state': 'draft'}
            if kw.get('company_id'):
                try: _vals['license_company_id'] = int(kw.get('company_id'))
                except: pass
            _rn = request.env['spc.renewal'].sudo().create(_vals)
            request.session['rn_draft_id'] = _rn.id
        except Exception as e:
            import logging; logging.getLogger(__name__).error("RN CREATE ERROR: %s", e)
        return request.redirect('/spc/company-management/apply/rn-step2/' + service_type)

    @http.route('/spc/company-management/apply/rn-step2/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def rn_step2(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        customer_id = request.session.get('spc_selected_customer_id')
        customer = None
        if customer_id:
            rec = request.env['res.partner'].sudo().browse(customer_id)
            if rec.exists():
                customer = rec
        return request.render('spc_portal.template_setup_company_apply', {
            'customer': customer,
            'service_type': service_type,
            'fee': 0,
            'steps': ['Choose license', 'Legal details', 'Business activities', 'Application details', 'Review application', 'Payment'],
            'form_submit_url': '/spc/company-management/apply/rn-step2/submit',
        })

    @http.route('/spc/company-management/apply/rn-step2/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def rn_step2_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'renewal')
        request.session['rn_step2_data'] = {k: v for k, v in kw.items() if isinstance(v, str)}
        return request.redirect('/spc/company-management/apply/rn-step3/' + service_type)

    @http.route('/spc/company-management/apply/rn-step3/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def rn_step3(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        all_activities = request.env['spc.business.activity'].sudo().search([])
        categories = [
            ('publishing_media', 'Publishing and Media'),
            ('wholesale_retail', 'Wholesale and Retail'),
            ('services_consultancy', 'Services and Consultancy'),
            ('electronic_publishing', 'Electronic Publishing'),
            ('real_publishing', 'Real Publishing'),
        ]
        activities_data = {}
        for cat_key, cat_label in categories:
            cat_acts = all_activities.filtered(lambda a: a.category == cat_key)
            divisions = {}
            for act in cat_acts:
                div = act.division or 'General'
                if div not in divisions:
                    divisions[div] = []
                divisions[div].append({'id': act.id, 'code': act.code or str(act.id), 'name': act.name})
            activities_data[cat_key] = {'label': cat_label, 'divisions': divisions}
        if not any(activities_data[k]['divisions'] for k in activities_data):
            divisions = {}
            for act in all_activities:
                div = act.division or act.category or 'General'
                if div not in divisions:
                    divisions[div] = []
                divisions[div].append({'id': act.id, 'code': act.code or str(act.id), 'name': act.name})
            activities_data['all'] = {'label': 'All Activities', 'divisions': divisions}
            categories = [('all', 'All Activities')]
        return request.render('spc_portal.template_rn_step3', {
            'service_type': service_type,
            'activities_data': activities_data,
            'categories': categories,
            'fee': 0,
            'steps': ['Choose license', 'Legal details', 'Business activities', 'Application details', 'Review application', 'Payment'],
            'current_step': 3,
        })

    @http.route('/spc/company-management/apply/rn-step3/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def rn_step3_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'renewal')
        activity_names = request.httprequest.form.getlist('business_activities')
        activity_ids = []
        if activity_names:
            acts = request.env['spc.business.activity'].sudo().search([('name', 'in', activity_names)])
            activity_ids = acts.ids
        request.session['rn_step3_data'] = {'activity_ids': activity_ids, 'activity_names': activity_names}
        return request.redirect('/spc/company-management/apply/rn-step4/' + service_type)

    @http.route('/spc/company-management/apply/rn-step4/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def rn_step4(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_rn_step4', {
            'service_type': service_type,
            'steps': ['Choose license', 'Legal details', 'Business activities', 'Application details', 'Review application', 'Payment'],
            'current_step': 4,
        })

    @http.route('/spc/company-management/apply/rn-step4/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def rn_step4_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'renewal')
        safe_data = {k: v for k, v in kw.items() if isinstance(v, str)}
        request.session['rn_step4_data'] = safe_data
        import base64
        files = request.httprequest.files
        if 'renewal_doc' in files:
            f = files['renewal_doc']
            if f and f.filename:
                request.session['rn_doc'] = {
                    'filename': f.filename,
                    'data': base64.b64encode(f.read()).decode('utf-8'),
                }
        return request.redirect('/spc/company-management/apply/rn-step5/' + service_type)

    @http.route('/spc/company-management/apply/rn-step5/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def rn_step5(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        step1 = request.session.get('rn_step1_data', {})
        step2 = request.session.get('rn_step2_data', {})
        step3 = request.session.get('rn_step3_data', {})
        step4 = request.session.get('rn_step4_data', {})
        return request.render('spc_portal.template_rn_step5', {
            'service_type': service_type,
            'step1': step1, 'step2': step2, 'step3': step3, 'step4': step4,
        })

    @http.route('/spc/company-management/apply/rn-step5/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def rn_step5_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'renewal')
        return request.redirect('/spc/company-management/apply/rn-payment/' + service_type)

    @http.route('/spc/company-management/apply/rn-payment/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def rn_payment(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_rn_payment', {
            'service_type': service_type,
            'steps': ['Choose license', 'Legal details', 'Business activities', 'Application details', 'Review application', 'Payment'],
            'current_step': 6,
        })

    @http.route('/spc/company-management/apply/rn-payment/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def rn_payment_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'renewal')
        try:
            customer_id = request.session.get('spc_selected_customer_id')
            step1 = request.session.get('rn_step1_data', {}) or {}
            step2 = request.session.get('rn_step2_data', {}) or {}
            step3 = request.session.get('rn_step3_data', {}) or {}
            step4 = request.session.get('rn_step4_data', {}) or {}
            doc = request.session.get('rn_doc', {}) or {}
            activity_ids = step3.get('activity_ids', [])
            import base64
            vals = {
                'customer_id': customer_id,
                'approved_company_id': request.session.get('spc_selected_company_id'),
                'state': 'submitted',
                'license_company_name': step1.get('company_name', ''),
                'legal_type': step2.get('legal_type', ''),
                'package_type': step2.get('package_type', ''),
                'activity_names': ', '.join(step3.get('activity_names', [])),
                'license_validity': step4.get('license_validity', ''),
                'facility_type': step4.get('facility_type', ''),
                'visa_allocation': int(step4.get('visa_allocation', 0) or 0),

                'payment_method': kw.get('payment_method', ''),
                'payment_status': 'paid',
                'fee': float(kw.get('amount', 0)) or 0.0,
            }
            if step1.get('company_id'):
                try:
                    vals['license_company_id'] = int(step1['company_id'])
                except:
                    pass
            if doc.get('data'):
                vals['document_file'] = doc['data']
                vals['document_filename'] = doc.get('filename', '')
                vals['document_name'] = doc.get('filename', '')
            draft_id = request.session.get('rn_draft_id')
            if draft_id:
                rn = request.env['spc.renewal'].sudo().browse(draft_id)
                if rn.exists():
                    rn.sudo().write(vals)
                else:
                    rn = request.env['spc.renewal'].sudo().create(vals)
            else:
                rn = request.env['spc.renewal'].sudo().create(vals)
            if activity_ids:
                rn.business_activity_ids = [(6, 0, activity_ids)]
            for key in ['rn_step1_data', 'rn_step2_data', 'rn_step3_data', 'rn_step4_data', 'rn_doc', 'rn_draft_id']:
                request.session.pop(key, None)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"RN save error: {e}")
        return request.redirect('/spc/payment/' + service_type)

    @http.route('/spc/company-management/apply/success/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def company_mgmt_success(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_company_mgmt_success', {'service_type': service_type})

    # ══ RENEWAL WITH AMENDMENT FLOW ══
    @http.route('/spc/company-management/apply/ra-step1/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def ra_step1(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        customer_id = request.session.get('spc_selected_customer_id')
        companies = []
        if customer_id:
            partner = request.env['res.partner'].sudo().browse(customer_id)
            if partner.exists():
                companies = [{'id': partner.id, 'name': partner.name}]
                if partner.child_ids:
                    companies += partner.child_ids.filtered(lambda c: c.active).mapped(lambda c: {'id': c.id, 'name': c.name})
        return request.render('spc_portal.template_ra_step1', {
            'service_type': service_type,
            'companies': companies,
        })

    @http.route('/spc/company-management/apply/ra-step1/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def ra_step1_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'renewal_amendment')
        request.session['ra_step1_data'] = {
            'company_id': kw.get('company_id', ''),
            'company_name': kw.get('company_name', ''),
        }
        try:
            from odoo.fields import Datetime
            _cid = request.session.get('spc_selected_customer_id')
            _vals = {'customer_id': _cid, 'approved_company_id': request.session.get('spc_selected_company_id'), 'state': 'draft'}
            if kw.get('company_id'):
                try: _vals['company_id'] = int(kw.get('company_id'))
                except: pass
            _ra = request.env['spc.renewal.amendment'].sudo().create(_vals)
            request.session['ra_draft_id'] = _ra.id
        except Exception as _e:
            import logging; logging.getLogger(__name__).error("DRAFT CREATE ERROR [%d]: %s", 1, _e)
        return request.redirect('/spc/company-management/apply/ra-step2/' + service_type)


    def _ra_next_route(self, current, service_type):
        """Get next route in RA flow based on selected amendments."""
        amendments = request.session.get('ra_amendments', [])
        order = [
            'legal_type',
            'business_activities',
            'company_info',
            'nature_of_business',
            'visa_allocation',
            'facility_type',
            'shareholder',
            'manager',
            'director',
        ]
        route_map = {
            'legal_type':           '/spc/company-management/apply/ra-step3/',
            'business_activities':  '/spc/company-management/apply/ra-step4/',
            'company_info':         '/spc/company-management/apply/ra-company-info/',
            'nature_of_business':   '/spc/company-management/apply/ra-nature/',
            'visa_allocation':      '/spc/company-management/apply/ra-visa/',
            'facility_type':        '/spc/company-management/apply/ra-facility/',
            'shareholder':          '/spc/company-management/apply/ra-step5/',
            'manager':              '/spc/company-management/apply/ra-step6/',
            'director':             '/spc/company-management/apply/ra-step7/',
        }
        found = (current is None)
        for key in order:
            if found and key in amendments:
                return request.redirect(route_map[key] + service_type)
            if key == current:
                found = True
        return request.redirect('/spc/company-management/apply/ra-supporting-docs/' + service_type)

    @http.route('/spc/company-management/apply/ra-step2/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def ra_step2(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_ra_step2', {
            'service_type': service_type,
        })

    @http.route('/spc/company-management/apply/ra-step2/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def ra_step2_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'renewal_amendment')
        safe_data = {k: v for k, v in kw.items() if isinstance(v, str)}
        request.session['ra_step2_data'] = safe_data
        import base64
        files = request.httprequest.files
        if 'board_resolution' in files:
            f = files['board_resolution']
            if f and f.filename:
                request.session['ra_board_doc'] = {
                    'filename': f.filename,
                    'data': base64.b64encode(f.read()).decode('utf-8'),
                }
        import logging
        _logger = logging.getLogger(__name__)
        _logger.warning("RA STEP2 SUBMIT KW: %s", list(kw.keys()))
        amendments = []
        if kw.get('amendment_legal_type'): amendments.append('legal_type')
        if kw.get('amendment_business_activities'): amendments.append('business_activities')
        if kw.get('amendment_company_info'): amendments.append('company_info')
        if kw.get('amendment_capital_structure'): amendments.append('nature_of_business')
        if kw.get('amendment_visa_allocation'): amendments.append('visa_allocation')
        if kw.get('amendment_facility_type'): amendments.append('facility_type')
        if kw.get('amendment_shareholder'): amendments.append('shareholder')
        if kw.get('amendment_manager'): amendments.append('manager')
        if kw.get('amendment_director'): amendments.append('director')
        request.session['ra_amendments'] = amendments
        step_list = ['Company', 'Renewal type']
        if 'legal_type' in amendments: step_list.append('Legal type')
        if 'business_activities' in amendments: step_list.append('Business activities')
        if 'company_info' in amendments: step_list.append('Company information')
        if 'nature_of_business' in amendments: step_list.append('Nature of business')
        if 'visa_allocation' in amendments: step_list.append('Visa allocation')
        if 'facility_type' in amendments: step_list.append('Facility type')
        if 'shareholder' in amendments: step_list.append('Shareholder(s)')
        if 'manager' in amendments: step_list.append('Manager(s)')
        if 'director' in amendments: step_list.append('Director(s)')
        step_list += ['Supporting documents', 'Review application', 'Payment']
        request.session['ra_steps'] = step_list
        return self._ra_next_route(None, service_type)

    @http.route('/spc/company-management/apply/ra-step3/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def ra_step3(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        customer_id = request.session.get('spc_selected_customer_id')
        customer = None
        if customer_id:
            rec = request.env['res.partner'].sudo().browse(customer_id)
            if rec.exists():
                customer = rec
        steps = request.session.get('ra_steps', ['Company','Renewal type','Legal type','Supporting documents','Review application','Payment'])
        current = steps.index('Legal type') + 1 if 'Legal type' in steps else 3
        return request.render('spc_portal.template_ra_step3', {
            'customer': customer,
            'service_type': service_type,
            'fee': 0,
            'steps': steps,
            'current_step': current,
            'form_submit_url': '/spc/company-management/apply/ra-step3/submit',
        })

    @http.route('/spc/company-management/apply/ra-step3/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def ra_step3_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'renewal_amendment')
        request.session['ra_step3_data'] = {k: v for k, v in kw.items() if isinstance(v, str)}
        return self._ra_next_route('legal_type', service_type)
    @http.route('/spc/company-management/apply/ra-step4/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def ra_step4(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        all_activities = request.env['spc.business.activity'].sudo().search([])
        categories = [
            ('publishing_media', 'Publishing and Media'),
            ('wholesale_retail', 'Wholesale and Retail'),
            ('services_consultancy', 'Services and Consultancy'),
            ('electronic_publishing', 'Electronic Publishing'),
            ('real_publishing', 'Real Publishing'),
        ]
        activities_data = {}
        for cat_key, cat_label in categories:
            cat_acts = all_activities.filtered(lambda a: a.category == cat_key)
            divisions = {}
            for act in cat_acts:
                div = act.division or 'General'
                if div not in divisions:
                    divisions[div] = []
                divisions[div].append({'id': act.id, 'code': act.code or str(act.id), 'name': act.name})
            activities_data[cat_key] = {'label': cat_label, 'divisions': divisions}
        if not any(activities_data[k]['divisions'] for k in activities_data):
            divisions = {}
            for act in all_activities:
                div = act.division or act.category or 'General'
                if div not in divisions:
                    divisions[div] = []
                divisions[div].append({'id': act.id, 'code': act.code or str(act.id), 'name': act.name})
            activities_data['all'] = {'label': 'All Activities', 'divisions': divisions}
            categories = [('all', 'All Activities')]
        steps = request.session.get('ra_steps', ['Company','Renewal type','Business activities','Supporting documents','Review application','Payment'])
        current = steps.index('Business activities') + 1 if 'Business activities' in steps else 3
        return request.render('spc_portal.template_ra_step4', {
            'service_type': service_type,
            'activities_data': activities_data,
            'categories': categories,
            'fee': 0,
            'steps': steps,
            'current_step': current,
            'form_submit_url': '/spc/company-management/apply/ra-step4/submit',
        })

    @http.route('/spc/company-management/apply/ra-step4/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def ra_step4_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'renewal_amendment')
        activity_names = request.httprequest.form.getlist('business_activities')
        activity_ids = []
        if activity_names:
            acts = request.env['spc.business.activity'].sudo().search([('name', 'in', activity_names)])
            activity_ids = acts.ids
        request.session['ra_step4_data'] = {'activity_ids': activity_ids, 'activity_names': activity_names}
        return self._ra_next_route('business_activities', service_type)


    @http.route('/spc/company-management/apply/ra-company-info/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def ra_company_info(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        steps = request.session.get('ra_steps', ['Company','Renewal type','Company information','Supporting documents','Review application','Payment'])
        current = steps.index('Company information') + 1 if 'Company information' in steps else 3
        return request.render('spc_portal.template_ra_company_info', {
            'service_type': service_type,
            'steps': steps,
            'current_step': current,
            'form_submit_url': '/spc/company-management/apply/ra-company-info/submit',
        })

    @http.route('/spc/company-management/apply/ra-company-info/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def ra_company_info_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'renewal_amendment')
        request.session['ra_company_info_data'] = {k: v for k, v in kw.items() if isinstance(v, str)}
        return self._ra_next_route('company_info', service_type)

    @http.route('/spc/company-management/apply/ra-nature/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def ra_nature(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        steps = request.session.get('ra_steps', ['Company','Renewal type','Nature of business','Supporting documents','Review application','Payment'])
        current = steps.index('Nature of business') + 1 if 'Nature of business' in steps else 3
        return request.render('spc_portal.template_setup_company_step10', {
            'service_type': service_type,
            'steps': steps,
            'current_step': current,
            'form_submit_url': '/spc/company-management/apply/ra-nature/submit',
        })

    @http.route('/spc/company-management/apply/ra-nature/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def ra_nature_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'renewal_amendment')
        request.session['ra_nature_data'] = {k: v for k, v in kw.items() if isinstance(v, str)}
        return self._ra_next_route('nature_of_business', service_type)

    @http.route('/spc/company-management/apply/ra-visa/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def ra_visa(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        steps = request.session.get('ra_steps', ['Company','Renewal type','Visa allocation','Supporting documents','Review application','Payment'])
        current = steps.index('Visa allocation') + 1 if 'Visa allocation' in steps else 3
        return request.render('spc_portal.template_setup_company_step5', {
            'service_type': service_type,
            'form_data': {},
            'errors': [],
            'steps': steps,
            'current_step': current,
            'form_submit_url': '/spc/company-management/apply/ra-visa/submit',
        })

    @http.route('/spc/company-management/apply/ra-visa/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def ra_visa_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'renewal_amendment')
        request.session['ra_visa_data'] = {k: v for k, v in kw.items() if isinstance(v, str)}
        return self._ra_next_route('visa_allocation', service_type)

    @http.route('/spc/company-management/apply/ra-facility/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def ra_facility(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        steps = request.session.get('ra_steps', ['Company','Renewal type','Facility type','Supporting documents','Review application','Payment'])
        current = steps.index('Facility type') + 1 if 'Facility type' in steps else 3
        return request.render('spc_portal.template_setup_company_step4', {
            'service_type': service_type,
            'steps': steps,
            'current_step': current,
            'form_submit_url': '/spc/company-management/apply/ra-facility/submit',
        })

    @http.route('/spc/company-management/apply/ra-facility/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def ra_facility_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'renewal_amendment')
        request.session['ra_facility_data'] = {k: v for k, v in kw.items() if isinstance(v, str)}
        return self._ra_next_route('facility_type', service_type)

    @http.route('/spc/company-management/apply/ra-supporting-docs/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def ra_supporting_docs(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        steps = request.session.get('ra_steps', ['Company','Renewal type','Supporting documents','Review application','Payment'])
        current = steps.index('Supporting documents') + 1 if 'Supporting documents' in steps else len(steps) - 2
        return request.render('spc_portal.template_ra_supporting_docs', {
            'service_type': service_type,
            'steps': steps,
            'current_step': current,
            'form_submit_url': '/spc/company-management/apply/ra-supporting-docs/submit',
        })

    @http.route('/spc/company-management/apply/ra-supporting-docs/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def ra_supporting_docs_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'renewal_amendment')
        return request.redirect('/spc/payment/' + service_type)

    @http.route('/spc/company-management/apply/ra-step5/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def ra_step5(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        customer_info = {}
        customer_id = request.session.get('spc_selected_customer_id')
        if customer_id:
            partner = request.env['res.partner'].sudo().browse(customer_id)
            if partner.exists():
                name_parts = (partner.name or '').split(' ', 1)
                customer_info = {
                    'first_name': name_parts[0] if name_parts else '',
                    'last_name': name_parts[1] if len(name_parts) > 1 else '',
                    'email': partner.email or '',
                    'mobile': partner.mobile or partner.phone or '',
                    'nationality': partner.country_id.code if partner.country_id else '',
                }
        existing_data = request.session.get('ra_step5_data', {})
        url_count = request.params.get('shareholder_count') or kw.get('shareholder_count')
        sh_count = max(1, min(int(url_count), 20)) if url_count else 1
        steps = request.session.get('ra_steps', ['Company','Renewal type','Shareholder(s)','Supporting documents','Review application','Payment'])
        current = steps.index('Shareholder(s)') + 1 if 'Shareholder(s)' in steps else 3
        return request.render('spc_portal.template_setup_company_step6', {
            'service_type': service_type,
            'form_data': existing_data,
            'errors': [],
            'customer_info': customer_info,
            'sh_count': sh_count,
            'sh_range': list(range(1, sh_count + 1)),
            'steps': steps,
            'current_step': current,
            'form_submit_url': '/spc/company-management/apply/ra-step5/submit',
            'step_base_url': '/spc/company-management/apply/ra-step5/',
        })

    @http.route('/spc/company-management/apply/ra-step5/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def ra_step5_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'renewal_amendment')
        import base64
        sh_count = int(kw.get('shareholder_count', 1) or 1)
        files = request.httprequest.files
        shareholders = []
        for i in range(1, sh_count + 1):
            sh = {
                'type': kw.get(f'sh_{i}_type', 'individual'),
                'first_name': kw.get(f'sh_{i}_first_name', ''),
                'last_name': kw.get(f'sh_{i}_last_name', ''),
                'passport_no': kw.get(f'sh_{i}_passport_no', ''),
                'nationality': kw.get(f'sh_{i}_nationality', ''),
                'email': kw.get(f'sh_{i}_email', ''),
                'mobile': kw.get(f'sh_{i}_mobile', ''),
                'dob': kw.get(f'sh_{i}_dob', ''),
                'address': kw.get(f'sh_{i}_address', ''),
                'city': kw.get(f'sh_{i}_city', ''),
                'country': kw.get(f'sh_{i}_country', ''),
                'has_uae_visa': kw.get(f'sh_{i}_uae_visa', ''),
                'visa_no': kw.get(f'sh_{i}_visa_no', ''),
                'shares_allocated': kw.get(f'sh_{i}_shares', '0'),
                'entity_name': kw.get(f'sh_{i}_entity_name', ''),
                'entity_reg_no': kw.get(f'sh_{i}_entity_reg_no', ''),
            }
            for fname in [f'sh_{i}_passport_file', f'sh_{i}_passport_special', f'sh_{i}_visa_file', f'sh_{i}_eid_file']:
                if fname in files and files[fname].filename:
                    f = files[fname]
                    sh[fname + '_filename'] = f.filename
                    sh[fname + '_data'] = base64.b64encode(f.read()).decode()
            shareholders.append(sh)
        request.session['ra_step5_data'] = {
            'shareholder_count': sh_count,
            'total_shares': kw.get('total_shares', '0'),
            'value_per_share': kw.get('value_per_share', '0'),
            'shareholders': shareholders,
        }
        return self._ra_next_route('shareholder', service_type)

    @http.route('/spc/company-management/apply/ra-step6/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def ra_step6(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        url_count = request.params.get('manager_count') or kw.get('manager_count')
        mgr_count = max(1, min(int(url_count), 20)) if url_count else 1
        steps = request.session.get('ra_steps', ['Company','Renewal type','Manager(s)','Supporting documents','Review application','Payment'])
        current = steps.index('Manager(s)') + 1 if 'Manager(s)' in steps else 3
        return request.render('spc_portal.template_setup_company_step7', {
            'service_type': service_type,
            'mgr_count': mgr_count,
            'mgr_range': list(range(1, mgr_count + 1)),
            'steps': steps,
            'current_step': current,
            'form_submit_url': '/spc/company-management/apply/ra-step6/submit',
            'step_base_url': '/spc/company-management/apply/ra-step6/',
        })
    @http.route('/spc/company-management/apply/ra-step6/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def ra_step6_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'renewal_amendment')
        import base64
        mgr_count = int(kw.get('manager_count', 1) or 1)
        files = request.httprequest.files
        managers = []
        for i in range(1, mgr_count + 1):
            mgr = {
                'define': kw.get(f'mgr_{i}_define', 'add_new'),
                'sh_val': kw.get(f'mgr_{i}_sh_val', ''),
                'spc_email': kw.get(f'mgr_{i}_spc_email', ''),
                'spc_pass': kw.get(f'mgr_{i}_spc_pass', ''),
                'first_name': kw.get(f'mgr_{i}_first_name', ''),
                'last_name': kw.get(f'mgr_{i}_last_name', ''),
                'nationality': kw.get(f'mgr_{i}_nationality', ''),
                'email': kw.get(f'mgr_{i}_email', ''),
                'mobile': kw.get(f'mgr_{i}_mobile', ''),
                'uae_resident': kw.get(f'mgr_{i}_uae_resident', ''),
                'visa_no': kw.get(f'mgr_{i}_visa_no', ''),
                'eid_no': kw.get(f'mgr_{i}_eid_no', ''),
                'uid': kw.get(f'mgr_{i}_uid', ''),
                'dob': kw.get(f'mgr_{i}_dob', ''),
                'passport_no': kw.get(f'mgr_{i}_passport_no', ''),
            }
            for fname in [f'mgr_{i}_passport_file', f'mgr_{i}_passport_sp', f'mgr_{i}_res_visa', f'mgr_{i}_eid', f'mgr_{i}_entry_visa']:
                if fname in files and files[fname].filename:
                    f = files[fname]
                    mgr[fname + '_filename'] = f.filename
                    mgr[fname + '_data'] = base64.b64encode(f.read()).decode()
            managers.append(mgr)
        request.session['ra_step6_data'] = {'manager_count': mgr_count, 'managers': managers}
        return self._ra_next_route('manager', service_type)

    @http.route('/spc/company-management/apply/ra-step7/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def ra_step7(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        steps = request.session.get('ra_steps', ['Company','Renewal type','Director(s)','Supporting documents','Review application','Payment'])
        current = steps.index('Director(s)') + 1 if 'Director(s)' in steps else 3
        return request.render('spc_portal.template_setup_company_step8', {
            'service_type': service_type,
            'steps': steps,
            'current_step': current,
            'form_submit_url': '/spc/company-management/apply/ra-step7/submit',
        })
    @http.route('/spc/company-management/apply/ra-step7/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def ra_step7_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'renewal_amendment')
        import base64
        dir_count = int(kw.get('director_count', 1) or 1)
        files = request.httprequest.files
        directors = []
        for i in range(1, dir_count + 1):
            d = {
                'define': kw.get(f'dir_{i}_def', 'new'),
                'sh_val': kw.get(f'dir_{i}_sh_val', ''),
                'spc_email': kw.get(f'dir_{i}_spc_email', ''),
                'spc_pass': kw.get(f'dir_{i}_spc_pass', ''),
                'first_name': kw.get(f'dir_{i}_fn', ''),
                'last_name': kw.get(f'dir_{i}_ln', ''),
                'nationality': kw.get(f'dir_{i}_nat', ''),
                'email': kw.get(f'dir_{i}_email', ''),
                'mobile': kw.get(f'dir_{i}_mob', ''),
                'uae_resident': kw.get(f'dir_{i}_ures', ''),
                'visa_no': kw.get(f'dir_{i}_vno', ''),
                'eid_no': kw.get(f'dir_{i}_eino', ''),
                'uid': kw.get(f'dir_{i}_uid', ''),
                'passport_no': kw.get(f'dir_{i}_passport_no', ''),
            }
            for fname in [f'dir_{i}_pf', f'dir_{i}_spf', f'dir_{i}_rvf', f'dir_{i}_eidf']:
                if fname in files and files[fname].filename:
                    f = files[fname]
                    d[fname + '_filename'] = f.filename
                    d[fname + '_data'] = base64.b64encode(f.read()).decode()
            directors.append(d)
        request.session['ra_step7_data'] = {'director_count': dir_count, 'directors': directors}
        return request.redirect('/spc/company-management/apply/ra-supporting-docs/' + service_type)

    @http.route('/spc/company-management/apply/ra-step8/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def ra_step8(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_setup_company_step9', {
            'service_type': service_type,
            'steps': ['Company', 'Renewal type', 'Legal type', 'Business activities', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Supporting documents', 'Review application', 'Payment'],
            'current_step': 8,
            'form_submit_url': '/spc/company-management/apply/ra-step8/submit',
        
            'steps': ['Legal type', 'Business activities', 'Company', 'Facility', 'Visa allocation', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Bank account', 'Documents', 'Review', 'Payment'],
            'current_step': 9,
        })

    @http.route('/spc/company-management/apply/ra-step8/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def ra_step8_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'renewal_amendment')
        import base64
        ubo_count = int(kw.get('ubo_count', 1) or 1)
        files = request.httprequest.files
        ubos = []
        for i in range(1, ubo_count + 1):
            u = {
                'define': kw.get(f'ubo_{i}_def', 'new'),
                'sh_val': kw.get(f'ubo_{i}_sh_val', ''),
                'spc_email': kw.get(f'ubo_{i}_spc_email', ''),
                'spc_pass': kw.get(f'ubo_{i}_spc_pass', ''),
                'work_entity': kw.get(f'ubo_{i}_work_entity', ''),
                'work_addr': kw.get(f'ubo_{i}_work_addr', ''),
                'ubo_type': kw.get(f'ubo_{i}_type', 'individual'),
                'first_name': kw.get(f'ubo_{i}_fn', ''),
                'last_name': kw.get(f'ubo_{i}_ln', ''),
                'nationality': kw.get(f'ubo_{i}_nat', ''),
                'stakeholder_type': kw.get(f'ubo_{i}_stake', 'shareholder'),
                'uae_resident': kw.get(f'ubo_{i}_ures', ''),
                'date_of_shares': kw.get(f'ubo_{i}_dos', ''),
                'date_of_ownership': kw.get(f'ubo_{i}_dow', ''),
                'voting_rights': kw.get(f'ubo_{i}_vote', ''),
            }
            for fname in [f'ubo_{i}_pf', f'ubo_{i}_spf']:
                if fname in files and files[fname].filename:
                    f = files[fname]
                    u[fname + '_filename'] = f.filename
                    u[fname + '_data'] = base64.b64encode(f.read()).decode()
            ubos.append(u)
        request.session['ra_step8_data'] = {'ubo_count': ubo_count, 'ubos': ubos}
        return request.redirect('/spc/company-management/apply/ra-step9/' + service_type)

    @http.route('/spc/company-management/apply/ra-step9/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def ra_step9(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_setup_company_step10', {
            'service_type': service_type,
            'steps': ['Company', 'Renewal type', 'Legal type', 'Business activities', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Supporting documents', 'Review application', 'Payment'],
            'current_step': 9,
            'form_submit_url': '/spc/company-management/apply/ra-step9/submit',
        
            'steps': ['Legal type', 'Business activities', 'Company', 'Facility', 'Visa allocation', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Bank account', 'Documents', 'Review', 'Payment'],
            'current_step': 10,
        })

    @http.route('/spc/company-management/apply/ra-step9/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def ra_step9_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'renewal_amendment')
        customer_market_list = [kw.get(f'customer_market_{i}', '') for i in range(1, 21) if kw.get(f'customer_market_{i}', '')]
        supplier_market_list = [kw.get(f'supplier_market_{i}', '') for i in range(1, 21) if kw.get(f'supplier_market_{i}', '')]
        request.session['ra_step9_data'] = {
            'annual_turnover': kw.get('annual_turnover', ''),
            'customer_markets': ', '.join(customer_market_list),
            'supplier_markets': ', '.join(supplier_market_list),
            'paid_up_capital': kw.get('paid_up_capital', ''),
            'capital_range': kw.get('capital_range', ''),
            'has_website': kw.get('has_website', ''),
            'website_url': kw.get('website_url', ''),
            'multinational_group': kw.get('multinational_group', ''),
        }
        return request.redirect('/spc/company-management/apply/ra-step10/' + service_type)

    @http.route('/spc/company-management/apply/ra-step10/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def ra_step10(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_setup_company_step12', {
            'service_type': service_type,
            'steps': ['Company', 'Renewal type', 'Legal type', 'Business activities', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Supporting documents', 'Review application', 'Payment'],
            'current_step': 10,
            'form_submit_url': '/spc/company-management/apply/ra-step10/submit',
        
            'steps': ['Legal type', 'Business activities', 'Company', 'Facility', 'Visa allocation', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Bank account', 'Documents', 'Review', 'Payment'],
            'current_step': 12,
        })

    @http.route('/spc/company-management/apply/ra-step10/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def ra_step10_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'renewal_amendment')
        import base64
        files = request.httprequest.files
        safe_data = {k: v for k, v in kw.items() if isinstance(v, str)}
        if 'documents' in files:
            f = files['documents']
            if f and f.filename:
                request.session['ra_doc'] = {
                    'filename': f.filename,
                    'data': base64.b64encode(f.read()).decode('utf-8'),
                }
        request.session['ra_step10_data'] = safe_data
        return request.redirect('/spc/company-management/apply/ra-step11/' + service_type)

    @http.route('/spc/company-management/apply/ra-step11/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def ra_step11(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        step1 = request.session.get('ra_step3_data', {}) or {}
        step2 = request.session.get('ra_step4_data', {}) or {}
        step3 = request.session.get('ra_step5_data', {}) or {}
        step4 = request.session.get('ra_step6_data', {}) or {}
        step5 = request.session.get('ra_step1_data', {}) or {}
        step6 = request.session.get('ra_step2_data', {}) or {}
        step7 = request.session.get('ra_step6_data', {}) or {}
        step8 = request.session.get('ra_step7_data', {}) or {}
        step9 = request.session.get('ra_step8_data', {}) or {}
        step10 = request.session.get('ra_step9_data', {}) or {}
        step11 = request.session.get('ra_step10_data', {}) or {}
        return request.render('spc_portal.template_setup_company_step13', {
            'service_type': service_type,
            'steps': ['Company', 'Renewal type', 'Legal type', 'Business activities', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Supporting documents', 'Review application', 'Payment'],
            'current_step': 11,
            'form_submit_url': '/spc/company-management/apply/ra-step11/submit',
            'step1': step1,
            'step2': step2,
            'step3': step3,
            'step4': step4,
            'step5': step5,
            'step6': step6,
            'step7': step7,
            'step8': step8,
            'step9': step9,
            'step10': step10,
            'step11': step11,
            'fee': 0,
        
            'steps': ['Legal type', 'Business activities', 'Company', 'Facility', 'Visa allocation', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Bank account', 'Documents', 'Review', 'Payment'],
            'current_step': 13,
        })

    @http.route('/spc/company-management/apply/ra-step11/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def ra_step11_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'renewal_amendment')
        return request.redirect('/spc/company-management/apply/ra-payment/' + service_type)

    @http.route('/spc/company-management/apply/ra-payment/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def ra_payment(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_setup_company_step14', {
            'service_type': service_type,
            'steps': ['Company', 'Renewal type', 'Legal type', 'Business activities', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Supporting documents', 'Review application', 'Payment'],
            'current_step': 12,
            'payment_action': '/spc/company-management/apply/ra-payment/submit',
        
            'steps': ['Legal type', 'Business activities', 'Company', 'Facility', 'Visa allocation', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Bank account', 'Documents', 'Review', 'Payment'],
            'current_step': 14,
        })

    @http.route('/spc/company-management/apply/ra-payment/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def ra_payment_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'renewal_amendment')
        try:
            customer_id = request.session.get('spc_selected_customer_id')
            step1 = request.session.get('ra_step1_data', {}) or {}
            step2 = request.session.get('ra_step2_data', {}) or {}
            step3 = request.session.get('ra_step3_data', {}) or {}
            step4 = request.session.get('ra_step4_data', {}) or {}
            step5 = request.session.get('ra_step5_data', {}) or {}
            step6 = request.session.get('ra_step6_data', {}) or {}
            step7 = request.session.get('ra_step7_data', {}) or {}
            step8 = request.session.get('ra_step8_data', {}) or {}
            step9 = request.session.get('ra_step9_data', {}) or {}
            step10 = request.session.get('ra_step10_data', {}) or {}
            board_doc = request.session.get('ra_board_doc', {}) or {}
            doc = request.session.get('ra_doc', {}) or {}
            activity_ids = step4.get('activity_ids', [])
            amendment_list = [k.replace('amendment_', '') for k, v in step2.items() if k.startswith('amendment_') and v == 'yes']
            vals = {
                'customer_id': customer_id,
                'approved_company_id': request.session.get('spc_selected_company_id'),
                'state': 'submitted',
                'company_name': step1.get('company_name', ''),
                'renewal_type': 'with_amendment',
                'amendment_types': ', '.join(amendment_list),
                'acknowledgement': bool(step2.get('acknowledgement')),
                'legal_type': step3.get('legal_type', ''),
                'package_type': step3.get('package_type', ''),
                'activity_names': ', '.join(step4.get('activity_names', [])),
                'shareholder_count': int(step5.get('shareholder_count', 0) or 0),
                'total_shares': int(step5.get('total_shares', 0) or 0),
                'value_per_share': float(step5.get('value_per_share', 0) or 0),
                'manager_count': int(step6.get('manager_count', 0) or 0),
                'director_count': int(step7.get('director_count', 0) or 0),
                'annual_turnover': float(step9.get('annual_turnover', 0) or 0),
                'customer_markets': step9.get('customer_markets', ''),
                'supplier_markets': step9.get('supplier_markets', ''),
                'paid_up_capital': step9.get('paid_up_capital', ''),
                'capital_range': step9.get('capital_range', ''),
                'has_website': step9.get('has_website', ''),
                'website_url': step9.get('website_url', ''),
                'multinational_group': step9.get('multinational_group', ''),
                'payment_method': kw.get('payment_method', ''),
                'payment_status': 'paid',
                'fee': float(kw.get('amount', 0)) or 0.0,
            }
            if step1.get('company_id'):
                try:
                    vals['company_id'] = int(step1['company_id'])
                except:
                    pass
            if board_doc.get('data'):
                vals['board_resolution_file'] = board_doc['data']
                vals['board_resolution_filename'] = board_doc.get('filename', '')
            draft_id = request.session.get('ra_draft_id')
            if draft_id:
                ra = request.env['spc.renewal.amendment'].sudo().browse(draft_id)
                if not ra.exists():
                    ra = request.env['spc.renewal.amendment'].sudo().create(vals)
                else:
                    ra.sudo().write(vals)
            else:
                ra = request.env['spc.renewal.amendment'].sudo().create(vals)
            if activity_ids:
                ra.business_activity_ids = [(6, 0, activity_ids)]

            # Board Resolution Document
            if board_doc.get('data'):
                request.env['spc.ra.document'].sudo().create({
                    'ra_id': ra.id, 'stage': 2,
                    'document_type': 'Board Resolution',
                    'related_to': step1.get('company_name', ''),
                    'file_name': board_doc.get('filename', ''),
                    'file_data': board_doc['data'],
                })

            # Shareholders
            sh_doc_names = {'passport_file': 'Passport Copy', 'passport_special': 'Passport Special Page', 'visa_file': 'UAE Resident Visa', 'eid_file': 'Emirates ID'}
            for sh in step5.get('shareholders', []):
                full_name = (sh.get('first_name', '') + ' ' + sh.get('last_name', '')).strip() or sh.get('entity_name', '')
                request.env['spc.ra.shareholder'].sudo().create({
                    'ra_id': ra.id,
                    'shareholder_type': sh.get('type', 'individual'),
                    'full_name': full_name,
                    'first_name': sh.get('first_name', ''),
                    'last_name': sh.get('last_name', ''),
                    'passport_no': sh.get('passport_no', ''),
                    'nationality': sh.get('nationality', ''),
                    'email': sh.get('email', ''),
                    'mobile': sh.get('mobile', ''),
                    'address': sh.get('address', ''),
                    'city': sh.get('city', ''),
                    'country': sh.get('country', ''),
                    'has_uae_visa': sh.get('has_uae_visa', ''),
                    'shares_allocated': int(sh.get('shares_allocated', 0) or 0),
                    'entity_name': sh.get('entity_name', ''),
                    'entity_reg_no': sh.get('entity_reg_no', ''),
                })
                for key in sh:
                    if key.endswith('_filename') and sh.get(key):
                        data_key = key.replace('_filename', '_data')
                        if sh.get(data_key):
                            parts = key.replace('_filename', '').split('_')
                            doc_key = '_'.join(parts[2:])
                            request.env['spc.ra.document'].sudo().create({
                                'ra_id': ra.id, 'stage': 5,
                                'document_type': sh_doc_names.get(doc_key, doc_key),
                                'related_to': f'Shareholder: {full_name}',
                                'file_name': sh[key], 'file_data': sh[data_key],
                            })

            # Managers
            mgr_doc_names = {'passport_file': 'Passport Copy', 'passport_sp': 'Passport Special Page', 'res_visa': 'UAE Resident Visa', 'eid': 'Emirates ID', 'entry_visa': 'UAE Entry Visa'}
            for mgr in step6.get('managers', []):
                define = mgr.get('define', 'add_new')
                if define == 'shareholder':
                    full_name = mgr.get('sh_val', '')
                elif define == 'spc':
                    full_name = mgr.get('spc_email', '')
                else:
                    full_name = (mgr.get('first_name', '') + ' ' + mgr.get('last_name', '')).strip()
                request.env['spc.ra.manager'].sudo().create({
                    'ra_id': ra.id,
                    'define_from': define,
                    'sh_val': mgr.get('sh_val', ''),
                    'spc_email': mgr.get('spc_email', ''),
                    'spc_pass': mgr.get('spc_pass', ''),
                    'full_name': full_name,
                    'first_name': mgr.get('first_name', ''),
                    'last_name': mgr.get('last_name', ''),
                    'passport_no': mgr.get('passport_no', ''),
                    'nationality': mgr.get('nationality', ''),
                    'email': mgr.get('email', ''),
                    'mobile': mgr.get('mobile', ''),
                    'has_uae_residence': mgr.get('uae_resident', ''),
                    'visa_no': mgr.get('visa_no', ''),
                    'eid_no': mgr.get('eid_no', ''),
                    'uid': mgr.get('uid', ''),
                    'dob': mgr.get('dob', ''),
                })
                for key in mgr:
                    if key.endswith('_filename') and mgr.get(key):
                        data_key = key.replace('_filename', '_data')
                        if mgr.get(data_key):
                            parts = key.replace('_filename', '').split('_')
                            doc_key = '_'.join(parts[2:])
                            request.env['spc.ra.document'].sudo().create({
                                'ra_id': ra.id, 'stage': 6,
                                'document_type': mgr_doc_names.get(doc_key, doc_key),
                                'related_to': f'Manager: {full_name}',
                                'file_name': mgr[key], 'file_data': mgr[data_key],
                            })

            # Directors
            dir_doc_names = {'pf': 'Passport Copy', 'spf': 'Passport Special Page', 'rvf': 'UAE Resident Visa', 'eidf': 'Emirates ID'}
            for d in step7.get('directors', []):
                define = d.get('define', 'new')
                if define in ('sh', 'shareholder'):
                    full_name = d.get('sh_val', '')
                elif define == 'spc':
                    full_name = d.get('spc_email', '')
                else:
                    full_name = (d.get('first_name', '') + ' ' + d.get('last_name', '')).strip()
                request.env['spc.ra.director'].sudo().create({
                    'ra_id': ra.id,
                    'define_from': define,
                    'sh_val': d.get('sh_val', ''),
                    'spc_email': d.get('spc_email', ''),
                    'spc_pass': d.get('spc_pass', ''),
                    'full_name': full_name,
                    'first_name': d.get('first_name', ''),
                    'last_name': d.get('last_name', ''),
                    'passport_no': d.get('passport_no', ''),
                    'nationality': d.get('nationality', ''),
                    'email': d.get('email', ''),
                    'mobile': d.get('mobile', ''),
                    'has_uae_residence': d.get('uae_resident', ''),
                    'visa_no': d.get('visa_no', ''),
                    'eid_no': d.get('eid_no', ''),
                    'uid': d.get('uid', ''),
                })
                for key in d:
                    if key.endswith('_filename') and d.get(key):
                        data_key = key.replace('_filename', '_data')
                        if d.get(data_key):
                            parts = key.replace('_filename', '').split('_')
                            doc_key = '_'.join(parts[2:])
                            request.env['spc.ra.document'].sudo().create({
                                'ra_id': ra.id, 'stage': 7,
                                'document_type': dir_doc_names.get(doc_key, doc_key),
                                'related_to': f'Director: {full_name}',
                                'file_name': d[key], 'file_data': d[data_key],
                            })

            # UBOs
            ubo_doc_names = {'pf': 'Passport Copy', 'spf': 'Passport Special Page'}
            for u in step8.get('ubos', []):
                define = u.get('define', 'new')
                if define == 'sh':
                    full_name = u.get('sh_val', '')
                elif define == 'spc':
                    full_name = u.get('spc_email', '')
                else:
                    full_name = (u.get('first_name', '') + ' ' + u.get('last_name', '')).strip()
                request.env['spc.ra.ubo'].sudo().create({
                    'ra_id': ra.id,
                    'define_from': define,
                    'sh_val': u.get('sh_val', ''),
                    'spc_email': u.get('spc_email', ''),
                    'spc_pass': u.get('spc_pass', ''),
                    'work_entity': u.get('work_entity', ''),
                    'work_addr': u.get('work_addr', ''),
                    'full_name': full_name,
                    'ubo_type': u.get('ubo_type', 'individual'),
                    'first_name': u.get('first_name', ''),
                    'last_name': u.get('last_name', ''),
                    'nationality': u.get('nationality', ''),
                    'stakeholder_type': u.get('stakeholder_type', 'shareholder'),
                    'has_uae_residence': u.get('uae_resident', ''),
                    'date_of_shares': u.get('date_of_shares', ''),
                    'date_of_ownership': u.get('date_of_ownership', ''),
                    'voting_rights': u.get('voting_rights', ''),
                })
                for key in u:
                    if key.endswith('_filename') and u.get(key):
                        data_key = key.replace('_filename', '_data')
                        if u.get(data_key):
                            parts = key.replace('_filename', '').split('_')
                            doc_key = '_'.join(parts[2:])
                            request.env['spc.ra.document'].sudo().create({
                                'ra_id': ra.id, 'stage': 8,
                                'document_type': ubo_doc_names.get(doc_key, doc_key),
                                'related_to': f'UBO: {full_name}',
                                'file_name': u[key], 'file_data': u[data_key],
                            })

            # Supporting Document (Step 10)
            if doc.get('data'):
                request.env['spc.ra.document'].sudo().create({
                    'ra_id': ra.id, 'stage': 10,
                    'document_type': 'Supporting Document',
                    'related_to': step1.get('company_name', ''),
                    'file_name': doc.get('filename', ''),
                    'file_data': doc['data'],
                })
            for key in ['ra_step1_data', 'ra_step2_data', 'ra_step3_data', 'ra_step4_data',
                        'ra_step5_data', 'ra_step6_data', 'ra_step7_data', 'ra_step8_data',
                        'ra_step9_data', 'ra_step10_data', 'ra_doc', 'ra_board_doc', 'ra_draft_id']:
                request.session.pop(key, None)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"RA save error: {e}")
        return request.redirect('/spc/payment/renewal_amendment')


    # ══ AMENDMENT FLOW ══
    def _amd_next_dynamic_step(self, step_list, current):
        step_routes = {
            'Legal Type': 'legal_type',
            'Business Activities': 'business_activities',
            'Shareholder Information': 'shareholder',
            'Manager Information': 'manager',
            'Director Information': 'director',
            'Company Information': 'company_info',
            'Facility Type': 'facility_type',
            'Nature of business': 'nature',
            'Supporting Document': 'docs',
            'Review application': 'review',
            'Payment': 'payment',
        }
        try:
            idx = step_list.index(current)
            next_name = step_list[idx + 1]
            return step_routes.get(next_name, 'nature')
        except:
            return 'nature'


    @http.route('/spc/company-management/apply/amd-step1/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def amd_step1(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        customer_id = request.session.get('spc_selected_customer_id')
        companies = []
        if customer_id:
            partner = request.env['res.partner'].sudo().browse(customer_id)
            companies = request.env['res.partner'].sudo().search([
                ('parent_id', '=', customer_id), ('is_company', '=', True)
            ])
        return request.render('spc_portal.template_amd_step1', {
            'service_type': service_type,
            'companies': companies,
            'steps': ['Company', 'Company amendment(s)', 'Nature of business', 'Supporting Document', 'Review application', 'Payment'],
            'current_step': 1,
        })

    @http.route('/spc/company-management/apply/amd-step1/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def amd_step1_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'amendment')
        request.session['amd_step1_data'] = {
            'company_id': kw.get('company_id', ''),
            'company_name': kw.get('company_name', ''),
        }
        try:
            from odoo.fields import Datetime
            _cid = request.session.get('spc_selected_customer_id')
            _vals = {'customer_id': _cid, 'approved_company_id': request.session.get('spc_selected_company_id'), 'state': 'draft'}
            if kw.get('company_id'):
                try: _vals['company_id'] = int(kw.get('company_id'))
                except: pass
            _amd = request.env['spc.amendment'].sudo().create(_vals)
            request.session['amd_draft_id'] = _amd.id
        except Exception as e:
            import logging; logging.getLogger(__name__).error('AMD CREATE ERROR: %s', e)
        return request.redirect('/spc/company-management/apply/amd-step2/' + service_type)

    @http.route('/spc/company-management/apply/amd-step2/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def amd_step2(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_amd_step2', {
            'service_type': service_type,
            'steps': ['Company', 'Company amendment(s)', 'Nature of business', 'Supporting Document', 'Review application', 'Payment'],
        })

    @http.route('/spc/company-management/apply/amd-step2/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def amd_step2_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        import base64, logging
        _log = logging.getLogger(__name__)
        _log.warning("AMD STEP2 KW keys: %s", list(kw.keys()))
        _log.warning("AMD STEP2 selected_steps: %s", kw.get('selected_steps'))
        service_type = kw.get('service_type', 'amendment')
        files = request.httprequest.files
        safe_data = {k: v for k, v in kw.items() if isinstance(v, str)}
        if 'board_resolution' in files:
            f = files['board_resolution']
            if f and f.filename:
                request.session['amd_board_doc'] = {
                    'filename': f.filename,
                    'data': base64.b64encode(f.read()).decode('utf-8'),
                }
        # Determine dynamic steps
        selected_steps = kw.get('selected_steps', '')
        step_list = ['Company', 'Company amendment(s)']
        if 'Legal Type' in selected_steps:
            step_list.append('Legal Type')
        if 'Business Activities' in selected_steps:
            step_list.append('Business Activities')
        if 'Shareholder Information' in selected_steps:
            step_list.append('Shareholder Information')
        if 'Manager Information' in selected_steps:
            step_list.append('Manager Information')
        if 'Director Information' in selected_steps:
            step_list.append('Director Information')
        if 'Company Information' in selected_steps:
            step_list.append('Company Information')
        if 'Facility Type' in selected_steps:
            step_list.append('Facility Type')
        step_list += ['Nature of business', 'Supporting Document', 'Review application', 'Payment']
        safe_data['selected_steps'] = selected_steps
        safe_data['step_list'] = ','.join(step_list)
        request.session['amd_step2_data'] = safe_data
        request.session['amd_steps'] = step_list
        # Determine next step
        next_step = self._amd_next_dynamic_step(step_list, 'Company amendment(s)')
        return request.redirect('/spc/company-management/apply/amd-dynamic/' + next_step + '/' + service_type)

    @http.route('/spc/company-management/apply/amd-dynamic/<string:step_name>/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def amd_dynamic_step(self, step_name, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        step_list = request.session.get('amd_steps', ['Company', 'Company amendment(s)', 'Nature of business', 'Supporting Document', 'Review application', 'Payment'])
        step_name_map = {
            'legal_type': 'Legal Type',
            'business_activities': 'Business Activities',
            'shareholder': 'Shareholder Information',
            'manager': 'Manager Information',
            'director': 'Director Information',
            'company_info': 'Company Information',
            'facility_type': 'Facility Type',
            'nature': 'Nature of business',
            'docs': 'Supporting Document',
            'review': 'Review application',
        }
        step_templates = {
            'legal_type': 'spc_portal.template_ra_step3',
            'business_activities': 'spc_portal.template_ra_step4',
            'shareholder': 'spc_portal.template_setup_company_step6',
            'manager': 'spc_portal.template_setup_company_step7',
            'director': 'spc_portal.template_setup_company_step8',
            'company_info': 'spc_portal.template_amd_company_info',
            'facility_type': 'spc_portal.template_setup_company_step4',
            'nature': 'spc_portal.template_setup_company_step10',
            'docs': 'spc_portal.template_amd_step4',
            'review': 'spc_portal.template_amd_step5',
        }
        current_name = step_name_map.get(step_name, '')
        try:
            current_idx = step_list.index(current_name) + 1
        except:
            current_idx = 3
        submit_url = f'/spc/company-management/apply/amd-dynamic-submit/{step_name}/{service_type}'
        # Get existing business activities for reuse
        all_activities = request.env['spc.business.activity'].sudo().search([])
        activities = all_activities
        categories = [
            ('publishing_media', 'Publishing and Media'),
            ('wholesale_retail', 'Wholesale and Retail'),
            ('services_consultancy', 'Services and Consultancy'),
            ('electronic_publishing', 'Electronic Publishing'),
            ('real_publishing', 'Real Publishing'),
        ]
        activities_data = {}
        for cat_key, cat_label in categories:
            cat_acts = all_activities.filtered(lambda a: a.category == cat_key)
            divisions = {}
            for act in cat_acts:
                div = act.division or 'General'
                if div not in divisions:
                    divisions[div] = []
                divisions[div].append({'id': act.id, 'code': act.code, 'name': act.name})
            activities_data[cat_key] = {'label': cat_label, 'divisions': divisions}
        if not any(activities_data[k]['divisions'] for k in activities_data):
            divisions = {}
            for act in all_activities:
                div = act.division or act.category or 'General'
                if div not in divisions:
                    divisions[div] = []
                divisions[div].append({'id': act.id, 'code': act.code or str(act.id), 'name': act.name})
            activities_data['all'] = {'label': 'All Activities', 'divisions': divisions}
            categories = [('all', 'All Activities')]
        # shareholder/manager/director count from URL or default 1
        sh_count = max(1, min(int(request.params.get('shareholder_count') or kw.get('shareholder_count') or 1), 20))
        mgr_count = max(1, min(int(request.params.get('manager_count') or kw.get('manager_count') or 1), 20))
        dir_count = max(1, min(int(request.params.get('director_count') or kw.get('director_count') or 1), 20))
        customer_info = {}
        customer_id = request.session.get('spc_selected_customer_id')
        if customer_id:
            partner = request.env['res.partner'].sudo().browse(customer_id)
            if partner.exists():
                name_parts = (partner.name or '').split(' ', 1)
                customer_info = {
                    'first_name': name_parts[0] if name_parts else '',
                    'last_name': name_parts[1] if len(name_parts) > 1 else '',
                    'email': partner.email or '',
                    'mobile': partner.mobile or partner.phone or '',
                    'nationality': partner.country_id.code if partner.country_id else '',
                }
        template = step_templates.get(step_name, 'spc_portal.template_amd_nature')
        return request.render(template, {
            'service_type': service_type,
            'steps': step_list,
            'current_step': current_idx,
            'form_submit_url': submit_url,
            'step_base_url': f'/spc/company-management/apply/amd-dynamic/{step_name}/',
            'activities': activities,
            'activities_data': activities_data,
            'categories': categories,
            'fee': 0,
            'customer_info': customer_info,
            'form_data': {},
            'errors': [],
            'sh_count': sh_count,
            'sh_range': list(range(1, sh_count + 1)),
            'mgr_count': mgr_count,
            'mgr_range': list(range(1, mgr_count + 1)),
            'dir_count': dir_count,
            'dir_range': list(range(1, dir_count + 1)),
        })

    @http.route('/spc/company-management/apply/amd-dynamic-submit/<string:step_name>/<string:service_type>', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def amd_dynamic_submit(self, step_name, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        import base64
        step_list = request.session.get('amd_steps', [])
        step_name_map = {
            'legal_type': 'Legal Type',
            'business_activities': 'Business Activities',
            'shareholder': 'Shareholder Information',
            'manager': 'Manager Information',
            'director': 'Director Information',
            'company_info': 'Company Information',
            'facility_type': 'Facility Type',
            'nature': 'Nature of business',
            'docs': 'Supporting Document',
            'review': 'Review application',
        }
        # Save step data
        files = request.httprequest.files
        safe_data = {k: v for k, v in kw.items() if isinstance(v, str)}
        # Handle business activities
        if step_name == 'business_activities':
            raw_ids = kw.get('activity_ids', '')
            activity_names_str = kw.get('activity_names', '')
            # Try ID-based first, then name-based
            activity_ids = [int(x) for x in raw_ids.split(',') if x.strip().isdigit()]
            if not activity_ids and activity_names_str:
                # Name-based: find IDs from names
                names = [n.strip() for n in activity_names_str.split(',') if n.strip()]
                acts = request.env['spc.business.activity'].sudo().search([('name', 'in', names)])
                activity_ids = acts.ids
                activity_names_str = ', '.join(acts.mapped('name'))
            elif not activity_ids:
                # Check if checkboxes submitted as names
                selected = [v for k, v in kw.items() if k == 'business_activities']
                if selected:
                    acts = request.env['spc.business.activity'].sudo().search([('name', 'in', selected)])
                    activity_ids = acts.ids
                    activity_names_str = ', '.join(acts.mapped('name'))
            request.session[f'amd_{step_name}_data'] = {
                'activity_ids': activity_ids,
                'activity_names': activity_names_str,
            }
            current_name2 = 'Business Activities'
            next_r = self._amd_next_dynamic_step(step_list, current_name2)
            if next_r == 'payment':
                return request.redirect('/spc/company-management/apply/amd-payment/' + service_type)
            return request.redirect(f'/spc/company-management/apply/amd-dynamic/{next_r}/{service_type}')
        # Handle file uploads for shareholder/manager/director
        if step_name == 'shareholder':
            sh_count = int(kw.get('shareholder_count', 1) or 1)
            shareholders = []
            for i in range(1, sh_count + 1):
                sh = {k: kw.get(k, '') for k in kw if k.startswith(f'sh_{i}_') and isinstance(kw.get(k), str)}
                for fname in [f'sh_{i}_passport_file', f'sh_{i}_passport_special', f'sh_{i}_visa_file', f'sh_{i}_eid_file']:
                    if fname in files and files[fname].filename:
                        f = files[fname]
                        sh[fname + '_filename'] = f.filename
                        sh[fname + '_data'] = base64.b64encode(f.read()).decode()
                shareholders.append(sh)
            request.session[f'amd_{step_name}_data'] = {'shareholder_count': sh_count, 'shareholders': shareholders}
        elif step_name == 'manager':
            mgr_count = int(kw.get('manager_count', 1) or 1)
            managers = []
            for i in range(1, mgr_count + 1):
                mgr = {k: kw.get(k, '') for k in kw if k.startswith(f'mgr_{i}_') and isinstance(kw.get(k), str)}
                for fname in [f'mgr_{i}_passport_file', f'mgr_{i}_passport_sp', f'mgr_{i}_res_visa', f'mgr_{i}_eid']:
                    if fname in files and files[fname].filename:
                        f = files[fname]
                        mgr[fname + '_filename'] = f.filename
                        mgr[fname + '_data'] = base64.b64encode(f.read()).decode()
                managers.append(mgr)
            request.session[f'amd_{step_name}_data'] = {'manager_count': mgr_count, 'managers': managers}
        elif step_name == 'director':
            dir_count = int(kw.get('director_count', 1) or 1)
            directors = []
            for i in range(1, dir_count + 1):
                d = {k: kw.get(k, '') for k in kw if k.startswith(f'dir_{i}_') and isinstance(kw.get(k), str)}
                for fname in [f'dir_{i}_pf', f'dir_{i}_spf', f'dir_{i}_rvf', f'dir_{i}_eidf']:
                    if fname in files and files[fname].filename:
                        f = files[fname]
                        d[fname + '_filename'] = f.filename
                        d[fname + '_data'] = base64.b64encode(f.read()).decode()
                directors.append(d)
            request.session[f'amd_{step_name}_data'] = {'director_count': dir_count, 'directors': directors}
        else:
            request.session[f'amd_{step_name}_data'] = safe_data
        current_name = step_name_map.get(step_name, '')
        # Also save with specific keys for payment_submit to find
        if step_name == 'nature':
            request.session['amd_nature_data'] = request.session.get(f'amd_{step_name}_data', {})
        elif step_name == 'company_info':
            request.session['amd_company_info_data'] = request.session.get(f'amd_{step_name}_data', {})
        elif step_name == 'facility_type':
            request.session['amd_facility_type_data'] = request.session.get(f'amd_{step_name}_data', {})
        elif step_name == 'legal_type':
            request.session['amd_legal_type_data'] = request.session.get(f'amd_{step_name}_data', {})
        elif step_name == 'business_activities':
            pass  # Already handled above
        next_route = self._amd_next_dynamic_step(step_list, current_name)
        if next_route == 'payment':
            return request.redirect('/spc/company-management/apply/amd-payment/' + service_type)
        return request.redirect(f'/spc/company-management/apply/amd-dynamic/{next_route}/{service_type}')

    @http.route('/spc/company-management/apply/amd-step3/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def amd_step3(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_setup_company_step10', {
            'service_type': service_type,
            'steps': ['Company', 'Company amendment(s)', 'Nature of business', 'Supporting Document', 'Review application', 'Payment'],
            'current_step': 3,
            'form_submit_url': '/spc/company-management/apply/amd-step3/submit',
        
            'steps': ['Legal type', 'Business activities', 'Company', 'Facility', 'Visa allocation', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Bank account', 'Documents', 'Review', 'Payment'],
            'current_step': 10,
        })

    @http.route('/spc/company-management/apply/amd-step3/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def amd_step3_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'amendment')
        customer_market_list = [kw.get(f'customer_market_{i}', '') for i in range(1, 21) if kw.get(f'customer_market_{i}', '')]
        supplier_market_list = [kw.get(f'supplier_market_{i}', '') for i in range(1, 21) if kw.get(f'supplier_market_{i}', '')]
        request.session['amd_step3_data'] = {
            'annual_turnover': kw.get('annual_turnover', ''),
            'customer_markets': ', '.join(customer_market_list),
            'supplier_markets': ', '.join(supplier_market_list),
            'paid_up_capital': kw.get('paid_up_capital', ''),
            'capital_range': kw.get('capital_range', ''),
            'has_website': kw.get('has_website', ''),
            'website_url': kw.get('website_url', ''),
            'multinational_group': kw.get('multinational_group', ''),
        }
        return request.redirect('/spc/company-management/apply/amd-step4/' + service_type)

    @http.route('/spc/company-management/apply/amd-step4/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def amd_step4(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_amd_step4', {
            'service_type': service_type,
            'steps': ['Company', 'Company amendment(s)', 'Nature of business', 'Supporting Document', 'Review application', 'Payment'],
            'current_step': 4,
        })

    @http.route('/spc/company-management/apply/amd-step4/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def amd_step4_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        import base64
        service_type = kw.get('service_type', 'amendment')
        files = request.httprequest.files
        docs = []
        for key, f in files.items():
            if f and f.filename:
                docs.append({
                    'filename': f.filename,
                    'data': base64.b64encode(f.read()).decode('utf-8'),
                })
        request.session['amd_step4_data'] = {'documents': docs}
        return request.redirect('/spc/company-management/apply/amd-step5/' + service_type)

    @http.route('/spc/company-management/apply/amd-step5/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def amd_step5(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        step1 = request.session.get('amd_step1_data', {}) or {}
        step2 = request.session.get('amd_step2_data', {}) or {}
        step3 = request.session.get('amd_step3_data', {}) or {}
        step4 = request.session.get('amd_step4_data', {}) or {}
        return request.render('spc_portal.template_amd_step5', {
            'service_type': service_type,
            'steps': ['Company', 'Company amendment(s)', 'Nature of business', 'Supporting Document', 'Review application', 'Payment'],
            'current_step': 5,
            'step1': step1, 'step2': step2, 'step3': step3, 'step4': step4,
        })

    @http.route('/spc/company-management/apply/amd-step5/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def amd_step5_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'amendment')
        return request.redirect('/spc/company-management/apply/amd-payment/' + service_type)

    @http.route('/spc/company-management/apply/amd-payment/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def amd_payment(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_setup_company_step14', {
            'service_type': service_type,
            'steps': ['Company', 'Company amendment(s)', 'Nature of business', 'Supporting Document', 'Review application', 'Payment'],
            'current_step': 6,
            'payment_action': '/spc/company-management/apply/amd-payment/submit',
        
            'steps': ['Legal type', 'Business activities', 'Company', 'Facility', 'Visa allocation', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Bank account', 'Documents', 'Review', 'Payment'],
            'current_step': 14,
        })

    @http.route('/spc/company-management/apply/amd-payment/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def amd_payment_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'amendment')
        try:
            customer_id = request.session.get('spc_selected_customer_id')
            step1 = request.session.get('amd_step1_data', {}) or {}
            step2 = request.session.get('amd_step2_data', {}) or {}
            # Nature of business - check both static and dynamic session keys
            step3 = request.session.get('amd_step3_data', {}) or {}
            nature_data = request.session.get('amd_nature_data', {}) or {}
            # Merge: dynamic takes priority
            if nature_data:
                step3 = nature_data
            step4 = request.session.get('amd_step4_data', {}) or {}
            docs_data = request.session.get('amd_docs_data', {}) or {}
            if docs_data:
                step4 = docs_data
            board_doc = request.session.get('amd_board_doc', {}) or {}
            amendment_list = [k.replace('amendment_', '') for k, v in step2.items() if k.startswith('amendment_') and v == 'on']

            # Build customer markets from dynamic fields
            customer_markets = step3.get('customer_markets', '')
            if not customer_markets:
                cm_list = [step3.get(f'customer_market_{i}', '') for i in range(1, 21) if step3.get(f'customer_market_{i}', '')]
                customer_markets = ', '.join(cm_list)
            supplier_markets = step3.get('supplier_markets', '')
            if not supplier_markets:
                sm_list = [step3.get(f'supplier_market_{i}', '') for i in range(1, 21) if step3.get(f'supplier_market_{i}', '')]
                supplier_markets = ', '.join(sm_list)

            vals = {
                'customer_id': customer_id,
                'approved_company_id': request.session.get('spc_selected_company_id'),
                'state': 'submitted',
                'company_name': step1.get('company_name', ''),
                'amendment_types': ', '.join(amendment_list),
                'acknowledgement': bool(step2.get('acknowledgement')),
                'annual_turnover': float(step3.get('annual_turnover', 0) or 0),
                'customer_markets': customer_markets,
                'supplier_markets': supplier_markets,
                'paid_up_capital': step3.get('paid_up_capital', ''),
                'capital_range': step3.get('capital_range', ''),
                'has_website': step3.get('has_website', ''),
                'website_url': step3.get('website_url', ''),
                'multinational_group': step3.get('multinational_group', ''),
                'payment_method': kw.get('payment_method', ''),
                'payment_status': 'paid',
                'fee': float(kw.get('amount', 0)) or 0.0,
            }
            if step1.get('company_id'):
                try:
                    vals['company_id'] = int(step1['company_id'])
                except:
                    pass
            if board_doc.get('data'):
                vals['board_resolution_file'] = board_doc['data']
                vals['board_resolution_filename'] = board_doc.get('filename', '')
            # Get dynamic step data
            legal_data = request.session.get('amd_legal_type_data', {}) or {}
            ba_data = request.session.get('amd_business_activities_data', {}) or {}
            sh_data = request.session.get('amd_shareholder_data', {}) or {}
            mgr_data = request.session.get('amd_manager_data', {}) or {}
            dir_data = request.session.get('amd_director_data', {}) or {}
            ci_data = request.session.get('amd_company_info_data', {}) or {}
            ft_data = request.session.get('amd_facility_type_data', {}) or {}
            vals.update({
                'fp_activity_change': step2.get('fp_activity_change', ''),
                'fp_shareholder_change': step2.get('fp_shareholder_change', ''),
                'fp_name_change': step2.get('fp_name_change', ''),
                'legal_type': legal_data.get('legal_type', ''),
                'package_type': legal_data.get('package_type', ''),
                'activity_names': ba_data.get('activity_names', ''),
                'shareholder_count': int(sh_data.get('shareholder_count', 0) or 0),
                'manager_count': int(mgr_data.get('manager_count', 0) or 0),
                'director_count': int(dir_data.get('director_count', 0) or 0),
                'new_company_name': ci_data.get('new_company_name', ''),
                'company_name_arabic': ci_data.get('company_name_arabic', ''),
                'company_address': ci_data.get('address_line1', '') or ci_data.get('company_address', ''),
                'company_phone': ci_data.get('phone', '') or ci_data.get('company_phone', ''),
                'company_email': ci_data.get('email', '') or ci_data.get('company_email', ''),
                'company_website': ci_data.get('website', '') or ci_data.get('company_website', ''),
                'company_info_notes': ci_data.get('company_info_notes', ''),
                'facility_type': ft_data.get('facility_type', '') or ft_data.get('facility_type', ''),
            })
            draft_id = request.session.get('amd_draft_id')
            if draft_id:
                amd = request.env['spc.amendment'].sudo().browse(draft_id)
                if not amd.exists():
                    amd = request.env['spc.amendment'].sudo().create(vals)
                else:
                    amd.sudo().write(vals)
            else:
                amd = request.env['spc.amendment'].sudo().create(vals)
            # Business Activities
            if ba_data.get('activity_ids'):
                try:
                    act_ids = [int(x) for x in str(ba_data['activity_ids']).split(',') if str(x).strip().isdigit()]
                    if act_ids:
                        amd.business_activity_ids = [(6, 0, act_ids)]
                except:
                    pass
            # Shareholders
            sh_doc_names = {'passport_file': 'Passport Copy', 'passport_special': 'Passport Special Page', 'visa_file': 'UAE Resident Visa', 'eid_file': 'Emirates ID'}
            for sh in sh_data.get('shareholders', []):
                # Support both flat dict and nested dict formats
                fn = sh.get('sh_1_first_name', '') or sh.get('first_name', '')
                ln = sh.get('sh_1_last_name', '') or sh.get('last_name', '')
                full_name = (fn + ' ' + ln).strip() or sh.get('entity_name', '')
                sh_rec = request.env['spc.amd.shareholder'].sudo().create({
                    'amd_id': amd.id,
                    'full_name': full_name,
                    'first_name': fn,
                    'last_name': ln,
                    'passport_no': sh.get('sh_1_passport_no', '') or sh.get('passport_no', ''),
                    'nationality': sh.get('sh_1_nationality', '') or sh.get('nationality', ''),
                    'email': sh.get('sh_1_email', '') or sh.get('email', ''),
                    'mobile': sh.get('sh_1_mobile', '') or sh.get('mobile', ''),
                    'dob': sh.get('sh_1_dob', '') or sh.get('dob', ''),
                    'address': sh.get('sh_1_address', '') or sh.get('address', ''),
                    'city': sh.get('sh_1_city', '') or sh.get('city', ''),
                    'country': sh.get('sh_1_country', '') or sh.get('country', ''),
                    'has_uae_visa': sh.get('sh_1_uae_visa', '') or sh.get('has_uae_visa', ''),
                    'visa_no': sh.get('sh_1_visa_no', '') or sh.get('visa_no', ''),
                    'eid_no': sh.get('sh_1_eid_no', '') or sh.get('eid_no', ''),
                    'uid': sh.get('sh_1_uid', '') or sh.get('uid', ''),
                    'shares_allocated': int(sh.get('sh_1_shares', 0) or sh.get('shares_allocated', 0) or 0),
                    'entity_name': sh.get('entity_name', ''),
                    'entity_reg_no': sh.get('entity_reg_no', ''),
                })
                # Save shareholder documents
                for key in sh:
                    if key.endswith('_filename') and sh.get(key):
                        data_key = key.replace('_filename', '_data')
                        if sh.get(data_key):
                            parts = key.replace('_filename', '').split('_')
                            doc_key = '_'.join(parts[2:]) if len(parts) > 2 else key
                            request.env['spc.amd.document'].sudo().create({
                                'amd_id': amd.id, 'stage': 5,
                                'document_type': sh_doc_names.get(doc_key, doc_key),
                                'related_to': f'Shareholder: {full_name}',
                                'file_name': sh[key], 'file_data': sh[data_key],
                            })

            # Managers
            mgr_doc_names = {'passport_file': 'Passport Copy', 'passport_sp': 'Passport Special Page', 'res_visa': 'UAE Resident Visa', 'eid': 'Emirates ID'}
            for mgr in mgr_data.get('managers', []):
                fn = mgr.get('mgr_1_first_name', '') or mgr.get('first_name', '')
                ln = mgr.get('mgr_1_last_name', '') or mgr.get('last_name', '')
                full_name = (fn + ' ' + ln).strip()
                mgr_rec = request.env['spc.amd.manager'].sudo().create({
                    'amd_id': amd.id,
                    'full_name': full_name,
                    'first_name': fn,
                    'last_name': ln,
                    'nationality': mgr.get('mgr_1_nationality', '') or mgr.get('nationality', ''),
                    'email': mgr.get('mgr_1_email', '') or mgr.get('email', ''),
                    'mobile': mgr.get('mgr_1_mobile', '') or mgr.get('mobile', ''),
                    'passport_no': mgr.get('mgr_1_passport_no', '') or mgr.get('passport_no', ''),
                    'has_uae_residence': mgr.get('mgr_1_uae_resident', '') or mgr.get('uae_resident', ''),
                    'visa_no': mgr.get('mgr_1_visa_no', '') or mgr.get('visa_no', ''),
                    'eid_no': mgr.get('mgr_1_eid_no', '') or mgr.get('eid_no', ''),
                    'uid': mgr.get('mgr_1_uid', '') or mgr.get('uid', ''),
                })
                for key in mgr:
                    if key.endswith('_filename') and mgr.get(key):
                        data_key = key.replace('_filename', '_data')
                        if mgr.get(data_key):
                            parts = key.replace('_filename', '').split('_')
                            doc_key = '_'.join(parts[2:]) if len(parts) > 2 else key
                            request.env['spc.amd.document'].sudo().create({
                                'amd_id': amd.id, 'stage': 6,
                                'document_type': mgr_doc_names.get(doc_key, doc_key),
                                'related_to': f'Manager: {full_name}',
                                'file_name': mgr[key], 'file_data': mgr[data_key],
                            })

            # Directors
            dir_doc_names = {'pf': 'Passport Copy', 'spf': 'Passport Special Page', 'rvf': 'UAE Resident Visa', 'eidf': 'Emirates ID'}
            for d in dir_data.get('directors', []):
                fn = d.get('dir_1_fn', '') or d.get('first_name', '')
                ln = d.get('dir_1_ln', '') or d.get('last_name', '')
                full_name = (fn + ' ' + ln).strip()
                dir_rec = request.env['spc.amd.director'].sudo().create({
                    'amd_id': amd.id,
                    'full_name': full_name,
                    'first_name': fn,
                    'last_name': ln,
                    'nationality': d.get('dir_1_nat', '') or d.get('nationality', ''),
                    'email': d.get('dir_1_email', '') or d.get('email', ''),
                    'mobile': d.get('dir_1_mob', '') or d.get('mobile', ''),
                    'passport_no': d.get('dir_1_passport_no', '') or d.get('passport_no', ''),
                    'has_uae_residence': d.get('dir_1_ures', '') or d.get('uae_resident', ''),
                    'visa_no': d.get('dir_1_vno', '') or d.get('visa_no', ''),
                    'eid_no': d.get('dir_1_eino', '') or d.get('eid_no', ''),
                    'uid': d.get('dir_1_uid', '') or d.get('uid', ''),
                })
                for key in d:
                    if key.endswith('_filename') and d.get(key):
                        data_key = key.replace('_filename', '_data')
                        if d.get(data_key):
                            parts = key.replace('_filename', '').split('_')
                            doc_key = '_'.join(parts[2:]) if len(parts) > 2 else key
                            request.env['spc.amd.document'].sudo().create({
                                'amd_id': amd.id, 'stage': 7,
                                'document_type': dir_doc_names.get(doc_key, doc_key),
                                'related_to': f'Director: {full_name}',
                                'file_name': d[key], 'file_data': d[data_key],
                            })
            # Board Resolution Document
            if board_doc.get('data'):
                request.env['spc.amd.document'].sudo().create({
                    'amd_id': amd.id, 'stage': 2,
                    'document_type': 'Board Resolution',
                    'related_to': step1.get('company_name', ''),
                    'file_name': board_doc.get('filename', ''),
                    'file_data': board_doc['data'],
                })
            # Supporting Documents
            for doc in step4.get('documents', []):
                if doc.get('data'):
                    request.env['spc.amd.document'].sudo().create({
                        'amd_id': amd.id, 'stage': 4,
                        'document_type': 'Supporting Document',
                        'related_to': step1.get('company_name', ''),
                        'file_name': doc.get('filename', ''),
                        'file_data': doc['data'],
                    })
            for key in ['amd_step1_data', 'amd_step2_data', 'amd_step3_data', 'amd_step4_data', 'amd_board_doc', 'amd_draft_id']:
                request.session.pop(key, None)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"AMD save error: {e}")
        return request.redirect('/spc/payment/amendment')



    # ============================================================
    # ESTABLISHMENT CARD & E-CHANNEL ROUTES
    # ============================================================

    def _ec_service_info(self, sub_type):
        from odoo.tools import Markup
        infos = {
            'new': {
                'name': 'Establishment Card and E-Channel - New',
                'badge': 'New',
                'banner_style': 'background:linear-gradient(135deg,#1a2340,#2d5fa3);color:#fff;min-height:280px;',
                'banner_html': Markup('<div style="padding:40px;color:#fff"><div style="background:#1a3c5e;display:inline-block;padding:8px 20px;font-weight:700;font-size:14px;margin-bottom:16px">New</div><div style="font-size:42px;font-weight:900;line-height:1.2">Establishment<br/>Card &amp;<br/>E-channel</div></div>'),
                'desc_html': Markup('<p>The establishment card is an immigration card issued to companies to create an account within the immigration system. A company must have an active establishment card to be able to apply for visas sponsored by the company. It is issued by the immigration authority.</p><br/><p>The e-channel service enables applicants to complete all visa-related registrations and approvals online eliminating the need for in-person visits to service centers. Users can apply for visas, check application statuses, and print visa-related documents.</p><br/><p><strong>Requirements</strong></p><ol style="margin-left:20px;margin-top:6px;margin-bottom:12px"><li>Valid Formation Documents</li><li>Colored Passport Copy of all Shareholders and Managers</li><li>Copy of UAE Residence Visa or E-Visa or UID Number Page of all shareholders and Manager</li><li>Special Comment Page of the Passport as per the Visa Checklist</li><li>Two (2) Passport size photos (As per the photo guidelines)</li><li>Copy of Pre-Approval (If applicable)</li><li>Copy of parent company documents (If applicable)</li><li>Payment</li></ol><p><strong>Timeline</strong></p><p style="margin-top:4px;margin-bottom:12px">3 business days</p><p><strong>Fees</strong></p><p style="margin-top:4px">AED 640 (Starting from)</p>'),
                'start_url': '/spc/company-management/apply/ec-new-step1/ec_new',
            },
            'renewal': {
                'name': 'Establishment Card and E-Channel - Renewal',
                'badge': 'Renew',
                'banner_style': 'background:linear-gradient(135deg,#0d6e4f,#1abc9c);color:#fff;min-height:280px;',
                'banner_html': Markup('<div style="padding:40px;color:#fff"><div style="background:#0a5540;display:inline-block;padding:8px 20px;font-weight:700;font-size:14px;margin-bottom:16px">Renew</div><div style="font-size:42px;font-weight:900;line-height:1.2">Establishment<br/>Card &amp;<br/>E-channel</div></div>'),
                'desc_html': Markup('<p>Once a company&#39;s Establishment Card is close to expiry, it must go through the renewal process in order to continue any activity in relation to the issuance, renewal, or cancellation of visas under the company.</p><br/><p><strong>Requirements</strong></p><ol style="margin-left:20px;margin-top:6px;margin-bottom:12px"><li>Valid Formation Documents</li><li>Colored Passport Copy of all Shareholders and Managers</li><li>Copy of UAE Residence Visa or E-Visa or UID Number Page of all shareholders and Manager</li><li>Special Comment Page of the Passport as per the Visa Checklist</li><li>Two (2) Passport size photos (As per the photo guidelines)</li><li>Copy of Pre-Approval (If applicable)</li><li>Copy of parent company documents (If applicable)</li><li>Payment</li></ol><p><strong>Output</strong></p><ol style="margin-left:20px;margin-top:6px;margin-bottom:12px"><li>Soft Copy of amended Establishment Card</li></ol><p><strong>Output Documents (Collection)</strong></p><ol style="margin-left:20px;margin-top:6px;margin-bottom:12px"><li>Establishment attested copy of Establishment Card (If applicable)</li></ol><p><strong>Timeline</strong></p><p style="margin-top:4px;margin-bottom:12px">3 business days</p><p><strong>Fees</strong></p><p style="margin-top:4px">Varies upon selection</p>'),
                'start_url': '/spc/company-management/apply/ec-renewal-company/ec_renewal',
            },
            'amendment': {
                'name': 'Establishment Card and E-Channel - New - Amendment',
                'badge': 'Amend',
                'banner_style': 'background:linear-gradient(135deg,#2d2d2d,#555);color:#fff;min-height:280px;',
                'banner_html': Markup('<div style="padding:40px;color:#fff"><div style="background:#1a3c5e;display:inline-block;padding:8px 20px;font-weight:700;font-size:14px;margin-bottom:16px">Amend</div><div style="font-size:42px;font-weight:900;line-height:1.2">Establishment<br/>Card &amp;<br/>E-channel</div></div>'),
                'desc_html': Markup('<p>If certain aspects of a company are changed, an Amended Establishment Card is issued reflecting the same. Amendments are made when there are changes to the company name, company activity, shareholders, managers or directors.</p><br/><p><strong>Requirements</strong></p><ol style="margin-left:20px;margin-top:6px;margin-bottom:12px"><li>Valid Formation Documents</li><li>Colored Passport Copy of all Shareholders and Managers</li><li>Copy of UAE Residence Visa or E-Visa or UID Number Page of all Shareholders and Managers</li><li>Special Comment Page of the Passport as per the Visa Checklist</li><li>Two (2) Passport-sized Photos (As per the photo guidelines)</li><li>Copy of Pre-Approval (If applicable)</li><li>Copy of Parent Company Documents (If applicable)</li><li>Payment</li></ol><p><strong>Input</strong></p><ol style="margin-left:20px;margin-top:6px;margin-bottom:12px"><li>Soft Copy of Establishment Card</li><li>Copy of Amended License</li><li>Payment Receipt</li></ol>'),
                'start_url': '/spc/company-management/apply/ec-amd-company/ec_amendment',
            },
            'cancellation': {
                'name': 'Establishment Card and E-Channel - Cancellation',
                'badge': 'Cancel',
                'banner_style': 'background:linear-gradient(135deg,#8b0000,#e53935);color:#fff;min-height:280px;',
                'banner_html': Markup('<div style="padding:40px;color:#fff"><div style="background:#5a0000;display:inline-block;padding:8px 20px;font-weight:700;font-size:14px;margin-bottom:16px">Cancel</div><div style="font-size:42px;font-weight:900;line-height:1.2">Establishment<br/>Card &amp;<br/>E-channel</div></div>'),
                'desc_html': Markup('<p>The Establishment Card and E-Channel cancellation process is required when a company wishes to close its immigration account or cancel its establishment card and e-channel services.</p><br/><p><strong>Requirements</strong></p><ol style="margin-left:20px;margin-top:6px;margin-bottom:12px"><li>Valid Formation Documents</li><li>Cancellation Request Letter</li><li>Payment</li></ol><p><strong>Timeline</strong></p><p style="margin-top:4px;margin-bottom:12px">3 business days</p><p><strong>Fees</strong></p><p style="margin-top:4px">AED 620</p>'),
                'start_url': '/spc/company-management/apply/ec-cancel-company/ec_cancellation',
            },
        }
        return infos.get(sub_type, infos['new'])

    @http.route([
        '/spc/company-management/service/ec_new',
        '/spc/company-management/service/ec_renewal',
        '/spc/company-management/service/ec_amendment',
        '/spc/company-management/service/ec_cancellation',
    ], type='http', auth='public', website=True, csrf=False)
    def ec_service_detail(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        path = request.httprequest.path
        sub_map = {'ec_new': 'new', 'ec_renewal': 'renewal', 'ec_amendment': 'amendment', 'ec_cancellation': 'cancellation'}
        sub_type = sub_map.get(path.split('/')[-1], 'new')
        info = self._ec_service_info(sub_type)
        service = {
            'name': info['name'],
            'banner_html': info['banner_html'],
            'banner_style': info['banner_style'],
            'desc_html': info.get('desc_html', ''),
        }
        return request.render('spc_portal.template_company_mgmt_service_detail', {
            'service_type': 'ec_' + sub_type,
            'service': service,
        })

    # --- EC NEW ---
    @http.route('/spc/company-management/apply/ec-new-step1/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def ec_new_step1(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_ec_new_step1', {'service_type': service_type})

    @http.route('/spc/company-management/apply/ec-new-step1/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def ec_new_step1_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'ec_new')
        request.session['ec_step1_data'] = {
            'confirm_establishment_card': kw.get('confirm_establishment_card', ''),
            'establishment_card_validity': kw.get('establishment_card_validity', ''),
            'confirm_echannel': kw.get('confirm_echannel', ''),
            'echannel_validity': kw.get('echannel_validity', ''),
        }
        try:
            from odoo.fields import Datetime
            _cid = request.session.get('spc_selected_customer_id')
            _ec = request.env['spc.establishment.card'].sudo().create({
                'customer_id': _cid, 'approved_company_id': request.session.get('spc_selected_company_id'), 'state': 'draft',
                'confirm_establishment_card': kw.get('confirm_establishment_card', ''),
                'establishment_card_validity': kw.get('establishment_card_validity', ''),
                'confirm_echannel': kw.get('confirm_echannel', ''),
                'echannel_validity': kw.get('echannel_validity', ''),
            })
            request.session['ec_draft_id'] = _ec.id
        except Exception as _e:
            import logging; logging.getLogger(__name__).error("DRAFT CREATE ERROR [%d]: %s", 2, _e)
        steps = ['Application details', 'Declaration', 'Review application', 'Payment']
        return request.render('spc_portal.template_ec_declaration', {
            'service_type': service_type,
            'page_title': 'New',
            'form_action': '/spc/company-management/apply/ec-declaration/submit',
            'steps': steps,
            'current_step': 2,
        })

    @http.route('/spc/company-management/apply/ec-declaration/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def ec_declaration_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'ec_new')
        request.session['ec_decl_data'] = {'declaration': kw.get('declaration', '')}
        # Build review data
        step1 = request.session.get('ec_step1_data', {}) or {}
        company_data = request.session.get('ec_company_data', {}) or {}
        review_data = []
        if company_data.get('company_name'):
            review_data.append(('Company', company_data['company_name']))
        if step1.get('confirm_establishment_card'):
            review_data.append(('Establishment Card', step1['confirm_establishment_card']))
        if step1.get('establishment_card_validity'):
            review_data.append(('Card Validity', step1['establishment_card_validity'].replace('_', ' ').title()))
        if step1.get('confirm_echannel'):
            review_data.append(('E-Channel', step1['confirm_echannel']))
        if step1.get('echannel_validity'):
            review_data.append(('E-Channel Validity', step1['echannel_validity'].replace('_', ' ').title()))
        # Determine sub type
        sub_type = service_type.replace('ec_', '')
        title_map = {'new': 'New', 'renewal': 'Renewal', 'amendment': 'New - Amendment', 'cancellation': 'Cancellation'}
        steps_map = {
            'new': ['Application details', 'Declaration', 'Review application', 'Payment'],
            'renewal': ['Company', 'Application details', 'Declaration', 'Review application', 'Payment'],
            'amendment': ['Company', 'Application details', 'Declaration', 'Review application', 'Payment'],
            'cancellation': ['Company', 'Declaration', 'Review application', 'Payment'],
        }
        steps = steps_map.get(sub_type, steps_map['new'])
        cur = steps.index('Review application') + 1 if 'Review application' in steps else len(steps) - 1
        return request.render('spc_portal.template_ec_review', {
            'service_type': service_type,
            'review_data': review_data,
            'payment_action': '/spc/company-management/apply/ec-payment',
            'steps': steps,
            'current_step': cur,
        })

    @http.route('/spc/company-management/apply/ec-payment', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def ec_payment(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'ec_new')
        sub_type = service_type.replace('ec_', '')
        steps_map = {
            'new': ['Application details', 'Declaration', 'Review application', 'Payment'],
            'renewal': ['Company', 'Application details', 'Declaration', 'Review application', 'Payment'],
            'amendment': ['Company', 'Application details', 'Declaration', 'Review application', 'Payment'],
            'cancellation': ['Company', 'Declaration', 'Review application', 'Payment'],
        }
        steps = steps_map.get(sub_type, steps_map['new'])
        return request.redirect('/spc/payment/establishment_card_' + sub_type)

    @http.route('/spc/company-management/apply/ec-final-submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def ec_final_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        try:
            customer_id = request.session.get('spc_selected_customer_id')
            step1 = request.session.get('ec_step1_data', {}) or {}
            company_data = request.session.get('ec_company_data', {}) or {}
            sub_type = kw.get('sub_type', 'new')
            vals = {
                'customer_id': customer_id,
                'service_sub_type': sub_type,
                'state': 'submitted',
                'company_name': company_data.get('company_name', ''),
                'confirm_establishment_card': step1.get('confirm_establishment_card', ''),
                'establishment_card_validity': step1.get('establishment_card_validity', ''),
                'confirm_echannel': step1.get('confirm_echannel', ''),
                'echannel_validity': step1.get('echannel_validity', ''),
                'declaration': bool(request.session.get('ec_decl_data', {}).get('declaration')),
                'payment_method': kw.get('payment_method', ''),
                'payment_status': 'paid',
                'fee': float(kw.get('amount', 0)) or 0.0,
            }
            if company_data.get('company_id'):
                try:
                    vals['company_id'] = int(company_data['company_id'])
                except:
                    pass
            draft_id = request.session.get('ec_draft_id')
            if draft_id:
                ec = request.env['spc.establishment.card'].sudo().browse(draft_id)
                if not ec.exists():
                    request.env['spc.establishment.card'].sudo().create(vals)
                else:
                    ec.sudo().write(vals)
            else:
                request.env['spc.establishment.card'].sudo().create(vals)
            for key in ['ec_step1_data', 'ec_company_data', 'ec_decl_data', 'ec_draft_id']:
                request.session.pop(key, None)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"EC save error: {e}")
        return request.redirect('/spc/payment/establishment_card_' + kw.get('sub_type', 'new'))

    # --- EC RENEWAL ---
    @http.route('/spc/company-management/apply/ec-renewal-company/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def ec_renewal_company(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        customer_id = request.session.get('spc_selected_customer_id')
        companies = request.env['res.partner'].sudo().search([
            ('parent_id', '=', customer_id), ('is_company', '=', True)
        ]) if customer_id else []
        return request.render('spc_portal.template_ec_company_step', {
            'service_type': service_type,
            'page_title': 'Renewal',
            'form_action': '/spc/company-management/apply/ec-renewal-company/submit',
            'companies': companies,
            'steps': ['Company', 'Application details', 'Declaration', 'Review application', 'Payment'],
            'current_step': 1,
        })

    @http.route('/spc/company-management/apply/ec-renewal-company/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def ec_renewal_company_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'ec_renewal')
        company_id = kw.get('company_id', '')
        company_name = kw.get('company_name_manual', '')
        if company_id and company_id != 'manual':
            try:
                p = request.env['res.partner'].sudo().browse(int(company_id))
                company_name = p.name
            except:
                pass
        request.session['ec_company_data'] = {'company_id': company_id, 'company_name': company_name}
        return request.render('spc_portal.template_ec_new_step1', {'service_type': service_type})

    # --- EC AMENDMENT ---
    @http.route('/spc/company-management/apply/ec-amd-company/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def ec_amd_company(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        customer_id = request.session.get('spc_selected_customer_id')
        companies = request.env['res.partner'].sudo().search([
            ('parent_id', '=', customer_id), ('is_company', '=', True)
        ]) if customer_id else []
        return request.render('spc_portal.template_ec_company_step', {
            'service_type': service_type,
            'page_title': 'New - Amendment',
            'form_action': '/spc/company-management/apply/ec-amd-company/submit',
            'companies': companies,
            'steps': ['Company', 'Application details', 'Declaration', 'Review application', 'Payment'],
            'current_step': 1,
        })

    @http.route('/spc/company-management/apply/ec-amd-company/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def ec_amd_company_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'ec_amendment')
        company_id = kw.get('company_id', '')
        company_name = kw.get('company_name_manual', '')
        if company_id and company_id != 'manual':
            try:
                p = request.env['res.partner'].sudo().browse(int(company_id))
                company_name = p.name
            except:
                pass
        request.session['ec_company_data'] = {'company_id': company_id, 'company_name': company_name}
        return request.render('spc_portal.template_ec_amd_step1', {'service_type': service_type})

    @http.route('/spc/company-management/apply/ec-amd-step2/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def ec_amd_step2_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'ec_amendment')
        request.session['ec_step1_data'] = {
            'confirm_establishment_card': kw.get('confirm_establishment_card', ''),
            'establishment_card_validity': kw.get('establishment_card_validity', ''),
            'confirm_echannel': kw.get('confirm_echannel', ''),
        }
        steps = ['Company', 'Application details', 'Declaration', 'Review application', 'Payment']
        return request.render('spc_portal.template_ec_declaration', {
            'service_type': service_type,
            'page_title': 'New - Amendment',
            'form_action': '/spc/company-management/apply/ec-declaration/submit',
            'steps': steps,
            'current_step': 3,
        })

    # --- EC CANCELLATION ---
    @http.route('/spc/company-management/apply/ec-cancel-company/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def ec_cancel_company(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        customer_id = request.session.get('spc_selected_customer_id')
        companies = request.env['res.partner'].sudo().search([
            ('parent_id', '=', customer_id), ('is_company', '=', True)
        ]) if customer_id else []
        return request.render('spc_portal.template_ec_company_step', {
            'service_type': service_type,
            'page_title': 'Cancellation',
            'form_action': '/spc/company-management/apply/ec-cancel-company/submit',
            'companies': companies,
            'steps': ['Company', 'Declaration', 'Review application', 'Payment'],
            'current_step': 1,
        })

    @http.route('/spc/company-management/apply/ec-cancel-company/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def ec_cancel_company_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'ec_cancellation')
        company_id = kw.get('company_id', '')
        company_name = kw.get('company_name_manual', '')
        if company_id and company_id != 'manual':
            try:
                p = request.env['res.partner'].sudo().browse(int(company_id))
                company_name = p.name
            except:
                pass
        request.session['ec_company_data'] = {'company_id': company_id, 'company_name': company_name}
        request.session['ec_step1_data'] = {}
        steps = ['Company', 'Declaration', 'Review application', 'Payment']
        return request.render('spc_portal.template_ec_declaration', {
            'service_type': service_type,
            'page_title': 'Cancellation',
            'form_action': '/spc/company-management/apply/ec-declaration/submit',
            'steps': steps,
            'current_step': 2,
        })

    # ============================================================
    # CERTIFY ROUTES
    # ============================================================

    @http.route('/spc/company-management/service/certify', type='http', auth='public', website=True, csrf=False)
    def certify_service_detail(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        from odoo.tools import Markup
        service = {
            'name': 'Company Formation - Certify',
            'banner_html': Markup('<div style="position:relative;height:100%;display:flex;align-items:center;padding:40px"><div><div style="background:#1a3c5e;display:inline-block;padding:8px 20px;font-weight:700;font-size:14px;margin-bottom:16px;color:#fff">Certify</div><div style="font-size:52px;font-weight:900;line-height:1.1;color:#fff">Formation</div></div></div>'),
            'banner_style': 'background:linear-gradient(135deg,#1a2340,#2d4a6e);color:#fff;min-height:280px;',
            'desc_html': Markup('<p>SPC Authority provides certified formation documents to verify document authenticity.</p><p><strong>Input Documents</strong></p><ol style="margin-left:20px;margin-top:4px;margin-bottom:12px"><li>Request Letter or Request Email</li><li>Payment</li></ol><p><strong>Output Documents</strong></p><ol style="margin-left:20px;margin-top:4px;margin-bottom:12px"><li>Certified Business License Documents</li><li>Payment Receipt</li></ol><p><strong>Output Documents (Collection)</strong></p><ol style="margin-left:20px;margin-top:4px;margin-bottom:12px"><li>Certified Business License Documents</li></ol><p><strong>Timeline</strong></p><p style="margin-top:4px;margin-bottom:12px">1 to 3 business days</p><p><strong>Fees</strong></p><p style="margin-top:4px">AED 350/Document</p>'),
        }
        return request.render('spc_portal.template_company_mgmt_service_detail', {
            'service_type': 'certify',
            'service': service,
        })

    @http.route('/spc/company-management/apply/certify-step1/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def certify_step1(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_certify_step1', {'service_type': service_type})

    @http.route('/spc/company-management/apply/certify-step1/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def certify_step1_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'certify')
        request.session['certify_step1_data'] = {
            'document_names': kw.get('document_names', ''),
            'remarks': kw.get('remarks', ''),
        }
        try:
            from odoo.fields import Datetime
            _cid = request.session.get('spc_selected_customer_id')
            _c = request.env['spc.certify'].sudo().create({
                'customer_id': _cid, 'approved_company_id': request.session.get('spc_selected_company_id'), 'state': 'draft',
                'document_names': kw.get('document_names', ''),
                'remarks': kw.get('remarks', ''),
            })
            request.session['certify_draft_id'] = _c.id
        except Exception as _e:
            import logging; logging.getLogger(__name__).error("DRAFT CREATE ERROR [%d]: %s", 3, _e)
        return request.redirect('/spc/company-management/apply/certify-step2/' + service_type)

    @http.route('/spc/company-management/apply/certify-step2/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def certify_step2(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_certify_step2', {'service_type': service_type})

    @http.route('/spc/company-management/apply/certify-step2/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def certify_step2_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'certify')
        request.session['certify_step2_data'] = {'declaration': kw.get('declaration', '')}
        return request.redirect('/spc/company-management/apply/certify-review/' + service_type)

    @http.route('/spc/company-management/apply/certify-review/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def certify_review(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        step1 = request.session.get('certify_step1_data', {}) or {}
        return request.render('spc_portal.template_certify_review', {
            'service_type': service_type, 'step1': step1,
        })

    @http.route('/spc/company-management/apply/certify-payment/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def certify_payment(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'certify')
        return request.render('spc_portal.template_certify_payment', {'service_type': service_type})

    @http.route('/spc/company-management/apply/certify-final-submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def certify_final_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        try:
            customer_id = request.session.get('spc_selected_customer_id')
            step1 = request.session.get('certify_step1_data', {}) or {}
            step2 = request.session.get('certify_step2_data', {}) or {}
            vals = {
                'customer_id': customer_id,
                'approved_company_id': request.session.get('spc_selected_company_id'),
                'state': 'submitted',
                'document_names': step1.get('document_names', ''),
                'remarks': step1.get('remarks', ''),
                'declaration': bool(step2.get('declaration')),
                'payment_method': kw.get('payment_method', ''),
                'payment_status': 'paid',
                'fee': float(kw.get('amount', 0)) or 0.0,
            }
            draft_id = request.session.get('certify_draft_id')
            if draft_id:
                draft = request.env['spc.certify'].sudo().browse(draft_id)
                if draft.exists():
                    draft.sudo().write(vals)
                else:
                    request.env['spc.certify'].sudo().create(vals)
            else:
                request.env['spc.certify'].sudo().create(vals)
            for key in ['certify_step1_data', 'certify_step2_data', 'certify_draft_id']:
                request.session.pop(key, None)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Certify save error: {e}")
        return request.redirect('/spc/payment/certify')

    # ============================================================
    # VISA ALLOCATION AMENDMENT ROUTES
    # ============================================================

    @http.route('/spc/company-management/service/visa_allocation_amendment', type='http', auth='public', website=True, csrf=False)
    def va_service_detail(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        from odoo.tools import Markup
        from odoo.tools import Markup
        service = {
            'name': 'Visa Allocation Amendment',
            'banner_html': Markup('<div style="position:relative;height:100%;display:flex;align-items:center;padding:40px"><div><div style="background:#1a3c5e;display:inline-block;padding:8px 20px;font-weight:700;font-size:14px;margin-bottom:16px">Amend</div><div style="font-size:52px;font-weight:900;line-height:1.1">Visa<br/>Allocation</div></div></div>'),
            'banner_style': 'background:linear-gradient(135deg,#1a2340,#2d6a4f);color:#fff;min-height:280px;',
        }
        return request.render('spc_portal.template_company_mgmt_service_detail', {
            'service_type': 'visa_allocation_amendment',
            'service': service,
        })

    @http.route('/spc/company-management/apply/va-step1/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def va_step1(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        customer_id = request.session.get('spc_selected_customer_id')
        companies = request.env['res.partner'].sudo().search([
            ('parent_id', '=', customer_id), ('is_company', '=', True)
        ]) if customer_id else []
        return request.render('spc_portal.template_va_step1', {
            'service_type': service_type,
            'companies': companies,
        })

    @http.route('/spc/company-management/apply/va-step1/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def va_step1_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'visa_allocation_amendment')
        company_id = kw.get('company_id', '')
        company_name = kw.get('company_name_manual', '')
        if company_id and company_id != 'manual':
            try:
                partner = request.env['res.partner'].sudo().browse(int(company_id))
                company_name = partner.name
            except:
                pass
        elif company_id == 'manual':
            company_id = ''
        request.session['va_step1_data'] = {
            'company_id': company_id,
            'company_name': company_name,
        }
        try:
            from odoo.fields import Datetime
            _cid = request.session.get('spc_selected_customer_id')
            _vals = {'customer_id': _cid, 'approved_company_id': request.session.get('spc_selected_company_id'), 'state': 'draft', 'company_name': company_name}
            if company_id:
                try: _vals['company_id'] = int(company_id)
                except: pass
            _va = request.env['spc.visa.allocation.amendment'].sudo().create(_vals)
            request.session['va_draft_id'] = _va.id
        except Exception as _e:
            import logging; logging.getLogger(__name__).error("DRAFT CREATE ERROR [%d]: %s", 4, _e)
        return request.redirect('/spc/company-management/apply/va-step2/' + service_type)

    @http.route('/spc/company-management/apply/va-step2/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def va_step2(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        customer_id = request.session.get('spc_selected_customer_id')
        companies = request.env['res.partner'].sudo().search([
            ('parent_id', '=', customer_id), ('is_company', '=', True)
        ]) if customer_id else []
        return request.render('spc_portal.template_va_step2', {
            'service_type': service_type,
            'companies': companies,
        })

    @http.route('/spc/company-management/apply/va-step2/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def va_step2_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'visa_allocation_amendment')
        request.session['va_step2_data'] = {
            'company_id': kw.get('company_id', ''),
            'package_type': kw.get('package_type', ''),
            'amendment_type': kw.get('amendment_type', ''),
        }
        return request.redirect('/spc/company-management/apply/va-step3/' + service_type)

    @http.route('/spc/company-management/apply/va-step3/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def va_step3(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_va_step3', {'service_type': service_type})

    @http.route('/spc/company-management/apply/va-step3/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def va_step3_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'visa_allocation_amendment')
        request.session['va_step3_data'] = {'license_validity': kw.get('license_validity', '')}
        return request.redirect('/spc/company-management/apply/va-step4/' + service_type)

    @http.route('/spc/company-management/apply/va-step4/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def va_step4(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_va_step4', {'service_type': service_type})

    @http.route('/spc/company-management/apply/va-step4/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def va_step4_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'visa_allocation_amendment')
        request.session['va_step4_data'] = {'facility_type': kw.get('facility_type', '')}
        return request.redirect('/spc/company-management/apply/va-step5/' + service_type)

    @http.route('/spc/company-management/apply/va-step5/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def va_step5(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_va_step5', {'service_type': service_type})

    @http.route('/spc/company-management/apply/va-step5/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def va_step5_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'visa_allocation_amendment')
        request.session['va_step5_data'] = {
            'existing_visa_allocation': int(kw.get('existing_visa_allocation', 0) or 0),
            'upgrade_downgrade': kw.get('upgrade_downgrade', ''),
            'additional_visas': int(kw.get('additional_visas', 0) or 0),
            'final_visa_allocation': int(kw.get('final_visa_allocation', 0) or 0),
        }
        return request.redirect('/spc/company-management/apply/va-step6/' + service_type)

    @http.route('/spc/company-management/apply/va-step6/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def va_step6(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_va_step6', {'service_type': service_type})

    @http.route('/spc/company-management/apply/va-step6/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def va_step6_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'visa_allocation_amendment')
        request.session['va_step6_data'] = {
            'declaration': kw.get('declaration', ''),
            'remarks': kw.get('remarks', ''),
        }
        return request.redirect('/spc/company-management/apply/va-review/' + service_type)

    @http.route('/spc/company-management/apply/va-review/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def va_review(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        step1 = request.session.get('va_step1_data', {}) or {}
        step2 = request.session.get('va_step2_data', {}) or {}
        step3 = request.session.get('va_step3_data', {}) or {}
        step4 = request.session.get('va_step4_data', {}) or {}
        step5 = request.session.get('va_step5_data', {}) or {}
        return request.render('spc_portal.template_va_review', {
            'service_type': service_type,
            'step1': step1, 'step2': step2, 'step3': step3,
            'step4': step4, 'step5': step5,
        })

    @http.route('/spc/company-management/apply/va-payment/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def va_payment(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'visa_allocation_amendment')
        return request.render('spc_portal.template_va_payment', {'service_type': service_type})

    @http.route('/spc/company-management/apply/va-final-submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def va_final_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        try:
            customer_id = request.session.get('spc_selected_customer_id')
            step1 = request.session.get('va_step1_data', {}) or {}
            step2 = request.session.get('va_step2_data', {}) or {}
            step3 = request.session.get('va_step3_data', {}) or {}
            step4 = request.session.get('va_step4_data', {}) or {}
            step5 = request.session.get('va_step5_data', {}) or {}
            vals = {
                'customer_id': customer_id,
                'approved_company_id': request.session.get('spc_selected_company_id'),
                'state': 'submitted',
                'company_name': step1.get('company_name', ''),
                'package_type': step2.get('package_type', ''),
                'amendment_type': step2.get('amendment_type', ''),
                'license_validity': step3.get('license_validity', ''),
                'facility_type': step4.get('facility_type', ''),
                'existing_visa_allocation': step5.get('existing_visa_allocation', 0),
                'upgrade_downgrade': step5.get('upgrade_downgrade', ''),
                'additional_visas': step5.get('additional_visas', 0),
                'final_visa_allocation': step5.get('final_visa_allocation', 0),
                'remarks': request.session.get('va_step6_data', {}).get('remarks', ''),
                'payment_method': kw.get('payment_method', ''),
                'payment_status': 'paid',
                'fee': float(kw.get('amount', 0)) or 0.0,
            }
            if step1.get('company_id'):
                try:
                    vals['company_id'] = int(step1['company_id'])
                except:
                    pass
            if step2.get('company_id') and not vals.get('company_id'):
                try:
                    vals['company_id'] = int(step2['company_id'])
                except:
                    pass
            draft_id = request.session.get('va_draft_id')
            if draft_id:
                va = request.env['spc.visa.allocation.amendment'].sudo().browse(draft_id)
                if not va.exists():
                    request.env['spc.visa.allocation.amendment'].sudo().create(vals)
                else:
                    va.sudo().write(vals)
            else:
                request.env['spc.visa.allocation.amendment'].sudo().create(vals)
            for key in ['va_step1_data', 'va_step2_data', 'va_step3_data', 'va_step4_data', 'va_step5_data', 'va_step6_data', 'va_draft_id']:
                request.session.pop(key, None)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"VA save error: {e}")
        return request.redirect('/spc/payment/visa_allocation_amendment')

    # ════════════════════════════════════════════════════════
    #  BUSINESS LICENSE
    # ════════════════════════════════════════════════════════

    PHYSICAL_FACILITIES = ['office', 'retail', 'store', 'shell_core', 'warehouse']

    def _bl_compute_steps(self):
        """Dynamically compute BL step labels based on current session."""
        d  = dict(request.session.get('bl_data', {}) or {})
        lt = d.get('license_type', '')
        ft = d.get('facility_type', '')
        vc = int(d.get('visa_count', 0) or 0)

        steps = ['Formation details', 'Business activities']

        if lt:
            steps += ['License validity', 'Office facility']
            if ft in self.PHYSICAL_FACILITIES:
                steps.append('Visa requirements')
                if vc > 0:
                    steps.append('Establishment card')

        steps += ['Manager information', 'Nature of business',
                  'Declarations', 'Additional Remarks',
                  'Review application', 'Payment']
        return steps

    def _bl_step_index(self, key):
        """Return 1-based step number by finding label in computed steps list."""
        key_to_label = {
            'step1':       'Formation details',
            'step2':       'Business activities',
            'step3':       'License validity',
            'step4':       'Office facility',
            'step5':       'Visa requirements',
            'step6':       'Establishment card',
            'manager':     'Manager information',
            'nature':      'Nature of business',
            'declaration': 'Declarations',
            'remarks':     'Additional Remarks',
            'review':      'Review application',
            'payment':     'Payment',
        }
        label = key_to_label.get(key, '')
        steps = self._bl_compute_steps()
        try:
            return steps.index(label) + 1
        except ValueError:
            return 1

    def _bl_ctx(self, current_key):
        # Always read fresh from session
        bl_data = dict(request.session.get('bl_data', {}) or {})
        steps   = self._bl_compute_steps()
        cur     = self._bl_step_index(current_key)
        return {
            'steps':        steps,
            'current_step': cur,
            'bl_data':      bl_data,
        }

    # ── Main page ──────────────────────────────────────────
    @http.route('/spc/company-management/business-license',
                type='http', auth='public', website=True)
    def bl_main(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_company_management', {
            'section': 'business_license',
        })

    # ── Additional BL detail page ──────────────────────────
    @http.route('/spc/company-management/business-license/additional',
                type='http', auth='public', website=True)
    def bl_additional(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        customer = request.env['res.partner'].sudo().browse(
            request.session.get('spc_selected_customer_id'))
        return request.render('spc_portal.template_service_detail', {
            'customer': customer,
            'service': {
                'category': 'Business License',
                'name': 'Additional Business License',
                'tag': 'New',
                'fee': 6500.0,
            },
            'service_type': 'bl_additional',
        })


    @http.route('/spc/company-management/apply/bl_additional',
                type='http', auth='public', website=True)
    def bl_additional_apply(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.redirect('/spc/company-management/business-license/bl-start')
    # ── Start ──────────────────────────────────────────────
    @http.route('/spc/company-management/business-license/bl-start',
                type='http', auth='public', website=True)
    def bl_start(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        request.session['bl_data'] = {}
        return request.redirect('/spc/company-management/business-license/bl-step1')

    # ── AJAX: update steps sidebar ─────────────────────────
    @http.route('/spc/company-management/business-license/bl-ajax-steps',
                type='json', auth='public', website=True, csrf=False)
    def bl_ajax_steps(self, field=None, value=None, current_step=None, **kw):
        if not self._check_spc_session():
            return {'error': 'not authenticated'}
        d = dict(request.session.get('bl_data', {}) or {})
        if field == 'visa_count':
            d['visa_count'] = int(value) if value is not None else 0
        elif field:
            d[field] = value or ''
        request.session['bl_data'] = d
        request.session.modified = True
        # Always build full steps list
        vc = int(d.get('visa_count', 0) or 0)
        steps = ['Formation details', 'Business activities', 'License validity',
                 'Office facility', 'Visa requirements']
        if vc > 0:
            steps.append('Establishment card')
        steps += ['Manager information', 'Nature of business', 'Declarations',
                  'Additional Remarks', 'Review application', 'Payment']
        cur = int(current_step) if current_step else 1
        return {
            'steps': steps,
            'current_step': cur,
        }

    # ── Step 1 GET ─────────────────────────────────────────
    @http.route('/spc/company-management/business-license/bl-step1',
                type='http', auth='public', website=True)
    def bl_step1(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_bl_step1', self._bl_ctx('step1'))

    # ── Step 1 POST ────────────────────────────────────────
    @http.route('/spc/company-management/business-license/bl-step1/submit',
                type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def bl_step1_submit(self, **post):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        request.session['bl_step1_data'] = {
            'license_type':       post.get('license_type', ''),
            'instant_license_fee': post.get('instant_license_fee', ''),
        }
        # Keep bl_data for sidebar steps computation
        d = dict(request.session.get('bl_data') or {})
        d['license_type'] = post.get('license_type', '')
        request.session['bl_data'] = d
        request.session.modified = True
        try:
            from odoo.fields import Datetime
            _cid = request.session.get('spc_selected_customer_id')
            _bl = request.env['spc.business.license'].sudo().create({
                'customer_id': _cid, 'approved_company_id': request.session.get('spc_selected_company_id'), 'state': 'draft',
                'license_type': post.get('license_type', ''),
            })
            request.session['bl_draft_id'] = _bl.id
        except Exception as _e:
            import logging; logging.getLogger(__name__).error("DRAFT CREATE ERROR [%d]: %s", 5, _e)
        return request.redirect('/spc/company-management/business-license/bl-step2')

    # ── Step 2 GET ─────────────────────────────────────────
    @http.route('/spc/company-management/business-license/bl-step2',
                type='http', auth='public', website=True)
    def bl_step2(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        d0 = dict(request.session.get('bl_data', {}) or {})
        lt0 = d0.get('license_type', '')
        all_activities = request.env['spc.business.activity'].sudo().search([])
        categories = [
            ('publishing_media',    'Publishing and Media'),
            ('wholesale_retail',    'Wholesale and Retail'),
            ('services_consultancy','Services and Consultancy'),
            ('electronic_publishing','Electronic Publishing'),
            ('real_publishing',     'Real Publishing'),
        ]
        cat_map = {}
        for cat_key, cat_label in categories:
            acts = all_activities.filtered(lambda a, k=cat_key: a.category == k)
            if acts:
                cat_map[cat_label] = acts
        if not cat_map:
            for act in all_activities:
                grp = getattr(act, 'division', None) or getattr(act, 'category', None) or 'General'
                if grp not in cat_map:
                    cat_map[grp] = all_activities.browse([])
                cat_map[grp] |= act
        # Step2 is only reached after step1 (license_type selected)
        # Always show License validity + Office facility in sidebar
        steps2 = ['Formation details', 'Business activities',
                  'License validity', 'Office facility',
                  'Manager information', 'Nature of business', 'Declarations',
                  'Additional Remarks', 'Review application', 'Payment']
        import logging
        logging.getLogger(__name__).info(f"BL step2 cat_map keys: {list(cat_map.keys())}, sizes: {[(k, len(v)) for k,v in cat_map.items()]}")
        return request.render('spc_portal.template_bl_step2', {
            'steps':        steps2,
            'current_step': 2,
            'bl_data':      d0,
            'categories':   cat_map,
        })

    # ── Step 2 POST ────────────────────────────────────────
    @http.route('/spc/company-management/business-license/bl-step2/submit',
                type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def bl_step2_submit(self, **post):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        d = request.session.get('bl_data', {})
        request.session['bl_step2_data'] = {
            'activity_ids': request.httprequest.form.getlist('activity_ids'),
        }
        d = dict(request.session.get('bl_data') or {})
        request.session['bl_data'] = d
        request.session.modified = True
        return request.redirect('/spc/company-management/business-license/bl-step3')

    # ── Step 3 (License Validity) GET ──────────────────────
    @http.route('/spc/company-management/business-license/bl-step3',
                type='http', auth='public', website=True)
    def bl_step3(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        d = dict(request.session.get('bl_data', {}) or {})
        steps = ['Formation details','Business activities','License validity','Office facility',
                 'Visa requirements','Manager information','Nature of business','Declarations',
                 'Additional Remarks','Review application','Payment']
        return request.render('spc_portal.template_bl_step3', {
            'steps': steps, 'current_step': 3, 'bl_data': d,
            'bl_prev_url': '/spc/company-management/business-license/bl-step2'})

    # ── Step 3 POST ────────────────────────────────────────
    @http.route('/spc/company-management/business-license/bl-step3/submit',
                type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def bl_step3_submit(self, **post):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        d = request.session.get('bl_data', {})
        request.session['bl_step3_data'] = {
            'license_validity': post.get('license_validity', ''),
        }
        d = dict(request.session.get('bl_data') or {})
        request.session['bl_data'] = d
        request.session.modified = True
        return request.redirect('/spc/company-management/business-license/bl-step4')

    # ── Step 4 (Office Facility) GET ───────────────────────
    @http.route('/spc/company-management/business-license/bl-step4',
                type='http', auth='public', website=True)
    def bl_step4(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        d = dict(request.session.get('bl_data', {}) or {})
        steps = ['Formation details','Business activities','License validity','Office facility',
                 'Visa requirements','Manager information','Nature of business','Declarations',
                 'Additional Remarks','Review application','Payment']
        return request.render('spc_portal.template_bl_step4', {
            'steps': steps, 'current_step': 4, 'bl_data': d,
            'bl_prev_url': '/spc/company-management/business-license/bl-step3'})

    # ── Step 4 POST ────────────────────────────────────────
    @http.route('/spc/company-management/business-license/bl-step4/submit',
                type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def bl_step4_submit(self, **post):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        d = request.session.get('bl_data', {})
        ft = post.get('facility_type', '')
        request.session['bl_step4_data'] = {
            'facility_type':            ft,
            'facility_acknowledgement': post.get('facility_acknowledgement', ''),
        }
        d = dict(request.session.get('bl_data') or {})
        d['facility_type'] = ft
        request.session['bl_data'] = d
        request.session.modified = True
        return request.redirect('/spc/company-management/business-license/bl-step5')

    # ── Step 5 (Visa) GET ──────────────────────────────────
    @http.route('/spc/company-management/business-license/bl-step5',
                type='http', auth='public', website=True)
    def bl_step5(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        d = dict(request.session.get('bl_data', {}) or {})
        vc = int(d.get('visa_count', 0) or 0)
        steps = ['Formation details','Business activities','License validity','Office facility','Visa requirements']
        if vc > 0:
            steps.append('Establishment card')
        steps += ['Manager information','Nature of business','Declarations','Additional Remarks','Review application','Payment']
        return request.render('spc_portal.template_bl_step5', {
            'steps': steps, 'current_step': 5, 'bl_data': d,
            'bl_prev_url': '/spc/company-management/business-license/bl-step4'})

    # ── Step 5 POST ────────────────────────────────────────
    @http.route('/spc/company-management/business-license/bl-step5/submit',
                type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def bl_step5_submit(self, **post):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        d = request.session.get('bl_data', {})
        vc_new = int(post.get('visa_count', 0) or 0)
        request.session['bl_step5_data'] = {'visa_count': vc_new}
        d = dict(request.session.get('bl_data') or {})
        d['visa_count'] = vc_new
        request.session['bl_data'] = d
        request.session.modified = True
        if vc_new > 0:
            return request.redirect('/spc/company-management/business-license/bl-step6')
        return request.redirect('/spc/company-management/business-license/bl-manager')

    # ── Step 6 (Establishment Card) GET ────────────────────
    @http.route('/spc/company-management/business-license/bl-step6',
                type='http', auth='public', website=True)
    def bl_step6(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        d = dict(request.session.get('bl_data', {}) or {})
        steps = ['Formation details','Business activities','License validity','Office facility','Visa requirements','Establishment card'] + ['Manager information','Nature of business','Declarations','Additional Remarks','Review application','Payment']
        return request.render('spc_portal.template_bl_step6', {
            'steps': steps, 'current_step': 6, 'bl_data': d,
            'bl_prev_url': '/spc/company-management/business-license/bl-step5'})

    # ── Step 6 POST ────────────────────────────────────────
    @http.route('/spc/company-management/business-license/bl-step6/submit',
                type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def bl_step6_submit(self, **post):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        request.session['bl_step6_data'] = {
            'establishment_card': post.get('establishment_card', ''),
            'ec_validity':        post.get('ec_validity', ''),
            'e_channel':          post.get('e_channel', ''),
        }
        request.session.modified = True
        return request.redirect('/spc/company-management/business-license/bl-manager')

    # ── Manager GET ────────────────────────────────────────
    @http.route('/spc/company-management/business-license/bl-manager',
                type='http', auth='public', website=True)
    def bl_manager(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        d  = request.session.get('bl_data', {})
        ft = d.get('facility_type', '')
        vc = int(d.get('visa_count', 0) or 0)
        lt = d.get('license_type', '')
        if lt and ft in self.PHYSICAL_FACILITIES and vc > 0:
            prev = '/spc/company-management/business-license/bl-step6'
        elif lt and ft in self.PHYSICAL_FACILITIES:
            prev = '/spc/company-management/business-license/bl-step5'
        elif lt:
            prev = '/spc/company-management/business-license/bl-step4'
        else:
            prev = '/spc/company-management/business-license/bl-step2'
        d2 = dict(request.session.get('bl_data', {}) or {})
        vc2 = int(d2.get('visa_count', 0) or 0)
        steps = ['Formation details','Business activities','License validity',
                 'Office facility','Visa requirements']
        if vc2 > 0:
            steps.append('Establishment card')
        steps += ['Manager information','Nature of business','Declarations',
                  'Additional Remarks','Review application','Payment']
        cur = steps.index('Manager information') + 1
        return request.render('spc_portal.template_ra_step6', {
            'service_type':    'bl_additional',
            'steps':           steps,
            'current_step':    cur,
            'form_submit_url': '/spc/company-management/business-license/bl-manager/submit',
            'manager_count':   1,
            'fee':             0,
        
            'steps': ['Legal type', 'Business activities', 'Company', 'Facility', 'Visa allocation', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Bank account', 'Documents', 'Review', 'Payment'],
            'current_step': 7,
        })

    # ── Manager POST ───────────────────────────────────────
    @http.route('/spc/company-management/business-license/bl-manager/submit',
                type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def bl_manager_submit(self, **post):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        import base64 as _b64
        mgr_count = int(post.get('manager_count', 1) or 1)
        managers = []
        files = request.httprequest.files
        doc_list = []
        for i in range(1, mgr_count + 1):
            mgr = {
                'first_name':   post.get(f'mgr_{i}_first_name', ''),
                'last_name':    post.get(f'mgr_{i}_last_name', ''),
                'nationality':  post.get(f'mgr_{i}_nationality', ''),
                'email':        post.get(f'mgr_{i}_email', ''),
                'mobile':       post.get(f'mgr_{i}_mobile', ''),
                'uae_resident': post.get(f'mgr_{i}_uae_resident', ''),
                'visa_no':      post.get(f'mgr_{i}_visa_no', ''),
                'eid_no':       post.get(f'mgr_{i}_eid_no', ''),
                'uid_no':       post.get(f'mgr_{i}_uid', ''),
                'dob':          post.get(f'mgr_{i}_dob', ''),
                'spc_passport': post.get(f'mgr_{i}_spc_passport', ''),
                'passport_expiry': post.get(f'mgr_{i}_doe', ''),
                'id_number':    post.get(f'mgr_{i}_id_number', ''),
            }
            managers.append(mgr)
            # Collect uploaded files
            file_fields = [
                (f'mgr_{i}_passport_file',  'Passport Copy'),
                (f'mgr_{i}_passport_sp',    'Passport Special Page'),
                (f'mgr_{i}_uid_file',       'UID Document'),
                (f'mgr_{i}_visa_file',      'Visa Copy'),
                (f'mgr_{i}_eid_file',       'Emirates ID'),
            ]
            for field_name, doc_type in file_fields:
                f = files.get(field_name)
                if f and f.filename:
                    data = _b64.b64encode(f.read()).decode('utf-8')
                    doc_list.append({
                        'name':     f.filename,
                        'data':     data,
                        'mimetype': f.content_type or 'application/octet-stream',
                        'doc_type': doc_type,
                        'related_to': f'Manager {i}',
                    })
        import logging as _l
        _l.getLogger(__name__).info(f"BL MANAGER: managers={managers}, docs={len(doc_list)}")
        # Save docs directly to ir.attachment (res_id=0 temp)
        att_ids = []
        for doc in doc_list:
            try:
                att = request.env['ir.attachment'].sudo().create({
                    'name':        doc['name'],
                    'datas':       doc['data'],
                    'mimetype':    doc.get('mimetype','application/octet-stream'),
                    'res_model':   'spc.business.license',
                    'res_id':      0,
                    'description': doc.get('doc_type','') + ' - ' + doc.get('related_to',''),
                })
                att_ids.append(att.id)
            except Exception as e:
                _l.getLogger(__name__).error(f"BL doc save error: {e}")
        request.session['bl_step7_data'] = {
            'managers':      managers,
            'manager_count': mgr_count,
            'att_ids':       att_ids,
        }
        request.session.modified = True
        return request.redirect('/spc/company-management/business-license/bl-nature')

    # ── Nature GET ─────────────────────────────────────────
    @http.route('/spc/company-management/business-license/bl-nature',
                type='http', auth='public', website=True)
    def bl_nature(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        bl_ctx = self._bl_ctx('nature')
        d2 = dict(request.session.get('bl_data', {}) or {})
        vc2 = int(d2.get('visa_count', 0) or 0)
        steps = ['Formation details','Business activities','License validity',
                 'Office facility','Visa requirements']
        if vc2 > 0:
            steps.append('Establishment card')
        steps += ['Manager information','Nature of business','Declarations',
                  'Additional Remarks','Review application','Payment']
        cur = steps.index('Nature of business') + 1
        return request.render('spc_portal.template_setup_company_step10', {
            'service_type':    'bl_additional',
            'steps':           steps,
            'current_step':    cur,
            'form_submit_url': '/spc/company-management/business-license/bl-nature/submit',
            'fee':             0,
        
            'steps': ['Legal type', 'Business activities', 'Company', 'Facility', 'Visa allocation', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Bank account', 'Documents', 'Review', 'Payment'],
            'current_step': 10,
        })

    @http.route('/spc/company-management/business-license/bl-nature/submit',
                type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def bl_nature_submit(self, **post):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        request.session['bl_step8_data'] = {
            'nature_of_business': post.get('nature_of_business', ''),
            'annual_turnover':    post.get('annual_turnover', ''),
            'customer_markets':   [post.get(f'customer_market_{i}','') for i in range(1,6) if post.get(f'customer_market_{i}')],
            'supplier_markets':   [post.get(f'supplier_market_{i}','') for i in range(1,6) if post.get(f'supplier_market_{i}')],
        }
        request.session.modified = True
        return request.redirect('/spc/company-management/business-license/bl-declaration')

    # ── Declaration GET ────────────────────────────────────
    @http.route('/spc/company-management/business-license/bl-declaration',
                type='http', auth='public', website=True)
    def bl_declaration(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        d2 = dict(request.session.get('bl_data', {}) or {})
        vc2 = int(d2.get('visa_count', 0) or 0)
        steps = ['Formation details','Business activities','License validity',
                 'Office facility','Visa requirements']
        if vc2 > 0:
            steps.append('Establishment card')
        steps += ['Manager information','Nature of business','Declarations',
                  'Additional Remarks','Review application','Payment']
        cur = steps.index('Declarations') + 1
        return request.render('spc_portal.template_bl_declaration', {
            'steps': steps, 'current_step': cur, 'bl_data': d2,
            'bl_submit_url': '/spc/company-management/business-license/bl-declaration/submit',
            'bl_prev_url':   '/spc/company-management/business-license/bl-nature',
        })

    @http.route('/spc/company-management/business-license/bl-declaration/submit',
                type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def bl_declaration_submit(self, **post):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        request.session['bl_step9_data'] = {'declaration': post.get('declaration', '')}
        request.session.modified = True
        return request.redirect('/spc/company-management/business-license/bl-remarks')

    # ── Remarks GET ────────────────────────────────────────
    @http.route('/spc/company-management/business-license/bl-remarks',
                type='http', auth='public', website=True)
    def bl_remarks(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        d2 = dict(request.session.get('bl_data', {}) or {})
        vc2 = int(d2.get('visa_count', 0) or 0)
        steps = ['Formation details','Business activities','License validity',
                 'Office facility','Visa requirements']
        if vc2 > 0:
            steps.append('Establishment card')
        steps += ['Manager information','Nature of business','Declarations',
                  'Additional Remarks','Review application','Payment']
        cur = steps.index('Additional Remarks') + 1
        return request.render('spc_portal.template_bl_remarks', {
            'steps': steps, 'current_step': cur, 'bl_data': d2,
            'bl_submit_url': '/spc/company-management/business-license/bl-remarks/submit',
            'bl_prev_url':   '/spc/company-management/business-license/bl-declaration',
        })

    @http.route('/spc/company-management/business-license/bl-remarks/submit',
                type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def bl_remarks_submit(self, **post):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        request.session['bl_step10_data'] = {'remarks': post.get('remarks', '')}
        request.session.modified = True
        return request.redirect('/spc/company-management/business-license/bl-review')

    # ── Review ─────────────────────────────────────────────
    @http.route('/spc/company-management/business-license/bl-review',
                type='http', auth='public', website=True)
    def bl_review(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        d2 = dict(request.session.get('bl_data', {}) or {})
        vc2 = int(d2.get('visa_count', 0) or 0)
        steps = ['Formation details','Business activities','License validity',
                 'Office facility','Visa requirements']
        if vc2 > 0:
            steps.append('Establishment card')
        steps += ['Manager information','Nature of business','Declarations',
                  'Additional Remarks','Review application','Payment']
        cur = steps.index('Review application') + 1
        return request.render('spc_portal.template_bl_review', {
            'steps': steps, 'current_step': cur, 'bl_data': d2,
            'bl_prev_url': '/spc/company-management/business-license/bl-remarks',
            'bl_next_url': '/spc/company-management/business-license/bl-payment',
        })

    # ── Payment ────────────────────────────────────────────
    @http.route('/spc/company-management/business-license/bl-payment',
                type='http', auth='public', website=True)
    def bl_payment(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        d2 = dict(request.session.get('bl_data', {}) or {})
        vc2 = int(d2.get('visa_count', 0) or 0)
        steps = ['Formation details','Business activities','License validity',
                 'Office facility','Visa requirements']
        if vc2 > 0:
            steps.append('Establishment card')
        steps += ['Manager information','Nature of business','Declarations',
                  'Additional Remarks','Review application','Payment']
        cur = steps.index('Payment') + 1
        return request.render('spc_portal.template_bl_payment', {
            'steps': steps, 'current_step': cur, 'bl_data': d2,
            'bl_prev_url': '/spc/company-management/business-license/bl-review',
        })

    # ── Save & Continue Later ──────────────────────────────
    @http.route('/spc/company-management/business-license/additional/save-later',
                type='http', auth='public', website=True)
    def bl_save_later(self, **kw):
        return request.redirect('/spc/company-management')

    # ── Cancel ─────────────────────────────────────────────
    @http.route('/spc/company-management/business-license/additional/cancel',
                type='http', auth='public', website=True)
    def bl_cancel(self, **kw):
        request.session.pop('bl_data', None)
        return request.redirect('/spc/company-management')

    # ── Final Submit ───────────────────────────────────────
    @http.route('/spc/company-management/business-license/bl-final-submit',
                type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def bl_final_submit(self, **post):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        try:
            customer_id = request.session.get('spc_selected_customer_id')
            # Merge all step data (VA pattern)
            s1 = request.session.get('bl_step1_data', {}) or {}
            s2 = request.session.get('bl_step2_data', {}) or {}
            s3 = request.session.get('bl_step3_data', {}) or {}
            s4 = request.session.get('bl_step4_data', {}) or {}
            s5 = request.session.get('bl_step5_data', {}) or {}
            s6 = request.session.get('bl_step6_data', {}) or {}
            s7 = request.session.get('bl_step7_data', {}) or {}
            s8 = request.session.get('bl_step8_data', {}) or {}
            s9 = request.session.get('bl_step9_data', {}) or {}
            s10= request.session.get('bl_step10_data',{}) or {}
            import logging as _log
            _log.getLogger(__name__).info(f'BL FINAL: s1={s1} s3={s3} s4={s4} s7keys={list(s7.keys())}')
            import json as _json
            # Manager data from step7
            managers = s7.get('managers', [])
            mgr = managers[0] if managers else {}
            mgr_name = (mgr.get('first_name','') + ' ' + mgr.get('last_name','')).strip()

            # Nature of business - step10 saves differently
            s8n = s8.get('nature_of_business','')
            s8t = str(s8.get('annual_turnover',''))
            s8cm = s8.get('customer_markets', [])
            s8sm = s8.get('supplier_markets', [])
            # Format markets nicely
            cm_str = ', '.join(s8cm) if isinstance(s8cm, list) else str(s8cm)
            sm_str = ', '.join(s8sm) if isinstance(s8sm, list) else str(s8sm)

            vals = {
                'customer_id':              customer_id,
                'approved_company_id': request.session.get('spc_selected_company_id'),
                'state':                    'submitted',
                # Package
                'license_type':             s1.get('license_type', ''),
                'instant_license_fee':      s1.get('instant_license_fee') == 'yes',
                'license_validity':         s3.get('license_validity', ''),
                # Facility
                'facility_type':            s4.get('facility_type', ''),
                'facility_acknowledgement': s4.get('facility_acknowledgement') == 'yes',
                # Visa
                'visa_count':               int(s5.get('visa_count', 0) or 0),
                # Establishment Card
                'establishment_card':       s6.get('establishment_card', ''),
                'ec_validity':              s6.get('ec_validity', ''),
                'e_channel':                s6.get('e_channel', ''),
                # Manager
                'manager_name':         mgr_name,
                'manager_mobile':       mgr.get('mobile', ''),
                'manager_email':        mgr.get('email', ''),
                'manager_passport_no':    mgr.get('spc_passport', ''),
                'manager_passport_expiry': mgr.get('passport_expiry') or False,
                'manager_uid_no':         mgr.get('uid_no', ''),
                'manager_gender':       mgr.get('gender', ''),
                'manager_dob':          mgr.get('dob') or False,
                'manager_visa_no':      mgr.get('visa_no', ''),
                'manager_eid_no':       mgr.get('eid_no', ''),
                'manager_uae_resident': mgr.get('uae_resident', ''),
                # Managers JSON
                'managers_data':            _json.dumps(managers),
                'manager_count':            int(s7.get('manager_count', 1) or 1),
                # Nature of Business
                'nature_of_business':       s8n,
                'annual_turnover':          s8t,
                'customer_markets':         cm_str,
                'supplier_markets':         sm_str,
                # Declaration + Remarks
                'declaration':              s9.get('declaration') == 'yes',
                'remarks':                  s10.get('remarks', ''),
                # Payment
                'payment_method':           post.get('payment_method', ''),
                'payment_status':           'paid',
                'fee':                      10.0,
            }
            # Nationality — step7 stores as country name string
            nat_str = mgr.get('nationality', '')
            if nat_str:
                nat_rec = request.env['res.country'].sudo().search(
                    [('name','ilike', nat_str)], limit=1)
                if nat_rec:
                    vals['manager_nationality_id'] = nat_rec.id
            # Business Activities
            act_ids = [int(a) for a in (s2.get('activity_ids') or []) if str(a).isdigit()]
            if act_ids:
                vals['business_activity_ids'] = [(6, 0, act_ids)]

            draft_id = request.session.get('bl_draft_id')
            if draft_id:
                bl_record = request.env['spc.business.license'].sudo().browse(draft_id)
                if not bl_record.exists():
                    bl_record = request.env['spc.business.license'].sudo().create(vals)
                else:
                    bl_record.sudo().write(vals)
            else:
                bl_record = request.env['spc.business.license'].sudo().create(vals)
            # Create structured document lines from pre-saved attachments
            _att_ids = s7.get('att_ids', [])
            if _att_ids:
                _atts = request.env['ir.attachment'].sudo().search([('id','in',_att_ids)])
                _atts.write({'res_id': bl_record.id, 'res_model': 'spc.business.license'})
                bl_record.sudo().write({'document_ids': [(6, 0, _att_ids)]})
                _mgrs = s7.get('managers', [])
                _mgr0 = _mgrs[0] if _mgrs else {}
                _mgr_name = (_mgr0.get('first_name','') + ' ' + _mgr0.get('last_name','')).strip()
                for _att in _atts:
                    _desc = _att.description or ''
                    _doc_type = _desc.split(' - ')[0] if ' - ' in _desc else _desc or _att.name
                    _related  = _desc.split(' - ')[1] if ' - ' in _desc else f'Manager: {_mgr_name}'
                    request.env['spc.bl.document'].sudo().create({
                        'bl_id':         bl_record.id,
                        'stage':         'Manager Information',
                        'document_type': _doc_type,
                        'related_to':    _related,
                        'file_name':     _att.name,
                        'file_data':     _att.datas,
                    })
            # Link pre-saved attachments to record
            att_ids = s7.get('att_ids', [])
            if att_ids:
                request.env['ir.attachment'].sudo().search([
                    ('id','in', att_ids)
                ]).write({
                    'res_id': bl_record.id,
                    'res_model': 'spc.business.license',
                })
                bl_record.sudo().write({'document_ids': [(6, 0, att_ids)]})
            for k in ['bl_data','bl_step1_data','bl_step2_data','bl_step3_data',
                       'bl_step4_data','bl_step5_data','bl_step6_data','bl_step7_data',
                       'bl_step8_data','bl_step9_data','bl_step10_data','bl_draft_id']:
                request.session.pop(k, None)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"BL final submit error: {e}")
        return request.redirect('/spc/payment/business_license')

    # ══════════════════════════════════════════════════
    # CORPORATE LETTERS
    # ══════════════════════════════════════════════════

    CL_STEPS = ['Type of corporate letter', 'Declaration', 'Review application', 'Payment']

    @http.route('/spc/company-management/corporate-letters',
                type='http', auth='public', website=True)
    def cl_main(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_cl_main', {})

    @http.route('/spc/company-management/corporate-letters/additional',
                type='http', auth='public', website=True)
    def cl_additional(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_cl_service_detail', {})

    @http.route('/spc/company-management/apply/corporate_letters',
                type='http', auth='public', website=True)
    def cl_apply(self, **kw):
        request.session.pop('cl_step1_data', None)
        request.session.pop('cl_step2_data', None)
        return request.redirect('/spc/company-management/corporate-letters/step1')

    @http.route('/spc/company-management/corporate-letters/step1',
                type='http', auth='public', website=True)
    def cl_step1(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        cl_data = dict(request.session.get('cl_step1_data') or {})
        customer_id = request.session.get('spc_selected_customer_id')
        companies = []
        if customer_id:
            partner = request.env['res.partner'].sudo().browse(customer_id)
            companies = [partner.name] if partner else []
        countries = request.env['res.country'].sudo().search([], order='name')
        return request.render('spc_portal.template_cl_step1', {
            'steps':        self.CL_STEPS,
            'current_step': 1,
            'cl_data':      cl_data,
            'companies':    companies,
            'countries':    countries,
        })

    @http.route('/spc/company-management/corporate-letters/step1/submit',
                type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def cl_step1_submit(self, **post):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        import base64 as _b64
        # Handle vehicle reg file upload
        files = request.httprequest.files
        reg_file_data = ''
        reg_file_name = ''
        f = files.get('vehicle_reg_copy')
        if f and f.filename:
            reg_file_data = _b64.b64encode(f.read()).decode('utf-8')
            reg_file_name = f.filename
        request.session['cl_step1_data'] = {
            'company_name':          post.get('company_name', ''),
            'letter_type':           post.get('letter_type', ''),
            'other_letter_name':     post.get('other_letter_name', ''),
            'license_expiry_date':   post.get('license_expiry_date', ''),
            'noc_type':              post.get('noc_type', ''),
            'police_station_name':   post.get('police_station_name', ''),
            'police_emirate':        post.get('police_emirate', ''),
            'ded_emirate':           post.get('ded_emirate', ''),
            'ded_office_location':   post.get('ded_office_location', ''),
            'vehicle_type':          post.get('vehicle_type', '') or post.get('transfer_vehicle_type', ''),
            'vehicle_chassis':       post.get('vehicle_chassis', '') or post.get('transfer_chassis', ''),
            'vehicle_engine':        post.get('vehicle_engine', '') or post.get('transfer_engine', ''),
            'vehicle_model_year':    post.get('vehicle_model_year', ''),
            'vehicle_color':         post.get('vehicle_color', '') or post.get('transfer_color', ''),
            'vehicle_country_origin': post.get('vehicle_country_origin', '') or post.get('transfer_country_origin', ''),
            'vehicle_name':          post.get('vehicle_name', ''),
            'vehicle_make_model':    post.get('transfer_make_model', '') or post.get('vehicle_make_model', ''),
            'vehicle_authority':     post.get('vehicle_authority', ''),
            'vehicle_authority_select': post.get('vehicle_authority_select', ''),
            'vehicle_reg_data':      reg_file_data,
            'vehicle_reg_name':      reg_file_name,
            'remarks':               post.get('remarks', '') or post.get('general_remarks', ''),
        }
        request.session.modified = True
        try:
            from odoo.fields import Datetime
            _cid = request.session.get('spc_selected_customer_id')
            _cl = request.env['spc.corporate.letter'].sudo().create({
                'customer_id': _cid, 'approved_company_id': request.session.get('spc_selected_company_id'), 'state': 'draft',
                'letter_type': post.get('letter_type', ''),
                'remarks': post.get('remarks', '') or post.get('general_remarks', ''),
            })
            request.session['cl_draft_id'] = _cl.id
        except Exception as _e:
            import logging; logging.getLogger(__name__).error("DRAFT CREATE ERROR [%d]: %s", 6, _e)
        return request.redirect('/spc/company-management/corporate-letters/step2')

    @http.route('/spc/company-management/corporate-letters/step2',
                type='http', auth='public', website=True)
    def cl_step2(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        cl_data = dict(request.session.get('cl_step1_data') or {})
        return request.render('spc_portal.template_cl_step2', {
            'steps':        self.CL_STEPS,
            'current_step': 2,
            'cl_data':      cl_data,
        })

    @http.route('/spc/company-management/corporate-letters/step2/submit',
                type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def cl_step2_submit(self, **post):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        request.session['cl_step2_data'] = {
            'declaration': post.get('declaration', ''),
        }
        request.session.modified = True
        return request.redirect('/spc/company-management/corporate-letters/review')

    @http.route('/spc/company-management/corporate-letters/review',
                type='http', auth='public', website=True)
    def cl_review(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        cl_data = {**(request.session.get('cl_step1_data') or {}),
                   **(request.session.get('cl_step2_data') or {})}
        return request.render('spc_portal.template_cl_review', {
            'steps':        self.CL_STEPS,
            'current_step': 3,
            'cl_data':      cl_data,
        })

    @http.route('/spc/company-management/corporate-letters/payment',
                type='http', auth='public', website=True)
    def cl_payment(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        cl_data = {**(request.session.get('cl_step1_data') or {}),
                   **(request.session.get('cl_step2_data') or {})}
        return request.render('spc_portal.template_cl_payment', {
            'steps':        self.CL_STEPS,
            'current_step': 4,
            'cl_data':      cl_data,
        })

    @http.route('/spc/company-management/corporate-letters/final-submit',
                type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def cl_final_submit(self, **post):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        try:
            customer_id = request.session.get('spc_selected_customer_id')
            s1 = request.session.get('cl_step1_data', {}) or {}
            s2 = request.session.get('cl_step2_data', {}) or {}
            import base64 as _b64
            vals = {
                'customer_id':       customer_id,
                'state':             'submitted',
                'company_name':      s1.get('company_name', ''),
                'letter_type':       s1.get('letter_type', ''),
                'other_letter_name': s1.get('other_letter_name', ''),
                'license_expiry_date': s1.get('license_expiry_date') or False,
                'noc_type':          s1.get('noc_type', ''),
                'police_station_name': s1.get('police_station_name', ''),
                'police_emirate':    s1.get('police_emirate', ''),
                'ded_emirate':       s1.get('ded_emirate', ''),
                'ded_office_location': s1.get('ded_office_location', ''),
                'vehicle_type':      s1.get('vehicle_type', ''),
                'vehicle_chassis':   s1.get('vehicle_chassis', ''),
                'vehicle_engine':    s1.get('vehicle_engine', ''),
                'vehicle_model_year': s1.get('vehicle_model_year', ''),
                'vehicle_color':     s1.get('vehicle_color', ''),
                'vehicle_name':      s1.get('vehicle_name', ''),
                'vehicle_make_model': s1.get('vehicle_make_model', ''),
                'vehicle_authority': s1.get('vehicle_authority', '') or s1.get('vehicle_authority_select', ''),
                'remarks':           s1.get('remarks', ''),
                'declaration':       s2.get('declaration') == 'yes',
                'payment_method':    post.get('payment_method', ''),
                'payment_status':    'paid',
                'fee':               360.0,
            }
            # Country of origin
            coo = s1.get('vehicle_country_origin', '')
            if coo and str(coo).isdigit():
                vals['vehicle_country_origin'] = int(coo)
            # Vehicle reg file
            if s1.get('vehicle_reg_data'):
                vals['vehicle_reg_copy'] = s1.get('vehicle_reg_data')
                vals['vehicle_reg_filename'] = s1.get('vehicle_reg_name', '')
            draft_id = request.session.get('cl_draft_id')
            if draft_id:
                cl_rec = request.env['spc.corporate.letter'].sudo().browse(draft_id)
                if not cl_rec.exists():
                    cl_rec = request.env['spc.corporate.letter'].sudo().create(vals)
                else:
                    cl_rec.sudo().write(vals)
            else:
                cl_rec = request.env['spc.corporate.letter'].sudo().create(vals)
            for k in ['cl_step1_data', 'cl_step2_data', 'cl_draft_id']:
                request.session.pop(k, None)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"CL submit error: {e}")
        return request.redirect('/spc/payment/corporate_letters')

    @http.route('/spc/company-management/corporate-letters/save-later',
                type='http', auth='public', website=True)
    def cl_save_later(self, **kw):
        return request.redirect('/spc/company-management')

    @http.route('/spc/company-management/corporate-letters/cancel',
                type='http', auth='public', website=True)
    def cl_cancel(self, **kw):
        for k in ['cl_step1_data', 'cl_step2_data']:
            request.session.pop(k, None)
        return request.redirect('/spc/company-management')

    # ══════════════════════════════════════════════════
    # NAME RESERVATION — Detail + Start
    # ══════════════════════════════════════════════════

    @http.route('/spc/company-management/name-reservation/additional',
                type='http', auth='public', website=True)
    def nr_additional(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_nr_service_detail', {})

    @http.route('/spc/company-management/apply/name_reservation',
                type='http', auth='public', website=True)
    def nr_apply(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.redirect('/spc/setup-new-company/apply/step2/name_reservation')

    # ══════════════════════════════════════════════════
    # PRE-APPROVAL — Detail + Start
    # ══════════════════════════════════════════════════

    @http.route('/spc/company-management/pre-approval/additional',
                type='http', auth='public', website=True)
    def pa_additional(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_pa_service_detail', {})

    @http.route('/spc/company-management/apply/pre_approval',
                type='http', auth='public', website=True)
    def pa_apply(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.redirect('/spc/setup-new-company/apply/step2/pre_approval')


    # ══════════════════════════════════════════════════
    # NMA MEDIA LICENSE
    # ══════════════════════════════════════════════════

    @http.route('/spc/company-management/nma-media-license',
                type='http', auth='public', website=True)
    def nma_ml_main(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_nma_main', {})

    @http.route('/spc/company-management/nma-media-license/<string:license_type>/additional',
                type='http', auth='public', website=True)
    def nma_ml_service_detail(self, license_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        type_config = {
            'new': {
                'label': 'New', 'fee': 535.00, 'timeline': 10,
                'description': 'Obtaining a new NMA Media License requires an application to the National Media License (NMA) to secure authorisation for commencing media-related activities within SPC Free Zone.',
            },
            'renewal': {
                'label': 'Renewal', 'fee': 535.00, 'timeline': 10,
                'description': 'Renew your existing NMA Media License to continue authorised media-related activities within SPC Free Zone.',
            },
            'amend': {
                'label': 'Amend', 'fee': 535.00, 'timeline': 10,
                'description': 'Amend your existing NMA Media License details including activities or company information within SPC Free Zone.',
            },
            'cancellation': {
                'label': 'Cancellation', 'fee': 525.00, 'timeline': 5,
                'description': 'Cancel your existing NMA Media License and cease media-related activities within SPC Free Zone.',
            },
        }
        config = type_config.get(license_type, type_config['new'])
        return request.render('spc_portal.template_nma_service_detail', {
            'license_type': license_type,
            'config': config,
        })

    @http.route('/spc/apply/nma_media_license/<string:license_type>',
                type='http', auth='public', website=True, methods=['GET', 'POST'])
    def nma_ml_step1(self, license_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        if request.httprequest.method == 'POST':
            data = {
                'company_name': kw.get('company_name', ''),
                'manager_name': kw.get('manager_name', ''),
                'manager_first_name': kw.get('manager_first_name', ''),
                'manager_last_name': kw.get('manager_last_name', ''),
                'manager_dob': kw.get('manager_dob', ''),
                'step1_remarks': kw.get('step1_remarks', ''),
            }
            request.session['nma_step1_data'] = data
            request.session['nma_license_type'] = license_type
            draft_id = request.session.get('nma_draft_id')
            if draft_id:
                request.env['spc.nma.media.license'].sudo().browse(int(draft_id)).write({
                    'company_name': data.get('company_name',''),
                    'manager_first_name': data.get('manager_first_name',''),
                    'manager_last_name': data.get('manager_last_name',''),
                })
            return request.redirect('/spc/apply/nma_media_license/%s/step2' % license_type)
        step1_data = request.session.get('nma_step1_data', {})
        partner = request.env.user.partner_id
        companies = request.env['res.partner'].sudo().search([
            ('parent_id', '=', partner.id), ('is_company', '=', True)
        ])
        resume_id = kw.get('resume_id')
        if resume_id:
            request.session['nma_draft_id'] = int(resume_id)
            # Redirect to correct step
            draft_rec = request.env['spc.nma.media.license'].sudo().browse(int(resume_id))
            if draft_rec.exists() and draft_rec.current_step > 1:
                step = draft_rec.current_step
                if step >= 6:
                    return request.redirect('/spc/apply/nma_media_license/%s/step6' % license_type)
                return request.redirect('/spc/apply/nma_media_license/%s/step%d' % (license_type, step))
        if not request.session.get('nma_draft_id'):
            # Check existing draft in DB first
            existing = request.env['spc.nma.media.license'].sudo().search([
                ('partner_id', '=', partner.id),
                ('license_type', '=', license_type),
                ('state', '=', 'draft'),
            ], order='id desc', limit=1)
            if existing:
                request.session['nma_draft_id'] = existing.id
            else:
                from odoo import fields as odoo_fields
                rec = request.env['spc.nma.media.license'].sudo().create({
                    'license_type': license_type,
                    'partner_id': partner.id,
            'approved_company_id': request.session.get('spc_selected_company_id'),
                    'state': 'draft',
                    'current_step': 1,
                    'started_date': odoo_fields.Datetime.now(),
                })
                request.session['nma_draft_id'] = rec.id
        return request.render('spc_portal.template_nma_step1', {
            'license_type': license_type,
            'step1_data': step1_data,
            'companies': companies,
        })

    @http.route('/spc/apply/nma_media_license/<string:license_type>/step2',
                type='http', auth='public', website=True, methods=['GET', 'POST'])
    def nma_ml_step2(self, license_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        if request.httprequest.method == 'POST':
            data = {
                'num_activities': kw.get('num_activities', ''),
                'activity_1': kw.get('activity_1', ''),
                'activity_2': kw.get('activity_2', ''),
                'activity_3': kw.get('activity_3', ''),
                'activity_4': kw.get('activity_4', ''),
                'activity_5': kw.get('activity_5', ''),
                'business_plan': kw.get('business_plan', ''),
            }
            request.session['nma_step2_data'] = data
            draft_id = request.session.get('nma_draft_id')
            if draft_id:
                request.env['spc.nma.media.license'].sudo().browse(draft_id).write({'current_step': 3})
            return request.redirect('/spc/apply/nma_media_license/%s/step3' % license_type)
        step2_data = request.session.get('nma_step2_data', {})
        return request.render('spc_portal.template_nma_step2', {
            'license_type': license_type,
            'step2_data': step2_data,
        })

    @http.route('/spc/apply/nma_media_license/<string:license_type>/step3',
                type='http', auth='public', website=True, methods=['GET', 'POST'])
    def nma_ml_step3(self, license_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        if request.httprequest.method == 'POST':
            import base64
            data = {
                'shareholder_name': kw.get('shareholder_name', ''),
                'shareholder_uae_resident': kw.get('shareholder_uae_resident', 'no'),
            }
            request.session['nma_step3_data'] = data
            files_data = {}
            for field in ['doc_mro_form', 'doc_photo', 'doc_emirates_id',
                          'doc_power_of_attorney', 'doc_request_form']:
                f = request.httprequest.files.get(field)
                if f and f.filename:
                    files_data[field] = base64.b64encode(f.read()).decode('utf-8')
                    files_data[field + '_name'] = f.filename
            request.session['nma_step3_files'] = files_data
            draft_id = request.session.get('nma_draft_id')
            if draft_id:
                request.env['spc.nma.media.license'].sudo().browse(draft_id).write({'current_step': 4})
            return request.redirect('/spc/apply/nma_media_license/%s/step4' % license_type)
        step3_data = request.session.get('nma_step3_data', {})
        partner = request.env.user.partner_id
        shareholders = request.env['res.partner'].sudo().search([
            ('parent_id', '=', partner.id)
        ])
        return request.render('spc_portal.template_nma_step3', {
            'license_type': license_type,
            'step3_data': step3_data,
            'shareholders': shareholders,
        })

    @http.route('/spc/apply/nma_media_license/<string:license_type>/step4',
                type='http', auth='public', website=True, methods=['GET', 'POST'])
    def nma_ml_step4(self, license_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        if request.httprequest.method == 'POST':
            data = {
                'declaration_accepted': kw.get('declaration_accepted', 'off') == 'on',
            }
            request.session['nma_step4_data'] = data
            draft_id = request.session.get('nma_draft_id')
            if draft_id:
                request.env['spc.nma.media.license'].sudo().browse(draft_id).write({'current_step': 5})
            return request.redirect('/spc/apply/nma_media_license/%s/step5' % license_type)
        step4_data = request.session.get('nma_step4_data', {})
        return request.render('spc_portal.template_nma_step4', {
            'license_type': license_type,
            'step4_data': step4_data,
        })

    @http.route('/spc/apply/nma_media_license/<string:license_type>/step5',
                type='http', auth='public', website=True, methods=['GET', 'POST'])
    def nma_ml_step5(self, license_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        if request.httprequest.method == 'POST':
            data = {'additional_remarks': kw.get('additional_remarks', '')}
            request.session['nma_step5_data'] = data
            draft_id = request.session.get('nma_draft_id')
            if draft_id:
                request.env['spc.nma.media.license'].sudo().browse(draft_id).write({'current_step': 6})
            return request.redirect('/spc/apply/nma_media_license/%s/step6' % license_type)
        step5_data = request.session.get('nma_step5_data', {})
        return request.render('spc_portal.template_nma_step5', {
            'license_type': license_type,
            'step5_data': step5_data,
        })

    @http.route('/spc/apply/nma_media_license/<string:license_type>/step6',
                type='http', auth='public', website=True, methods=['GET'])
    def nma_ml_step6(self, license_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_nma_step6', {
            'license_type': license_type,
            'step1': request.session.get('nma_step1_data', {}),
            'step2': request.session.get('nma_step2_data', {}),
            'step3': request.session.get('nma_step3_data', {}),
            'step4': request.session.get('nma_step4_data', {}),
            'step5': request.session.get('nma_step5_data', {}),
        })

    @http.route('/spc/apply/nma_media_license/<string:license_type>/step7',
                type='http', auth='public', website=True, methods=['GET'])
    def nma_ml_step7(self, license_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_nma_step7', {
            'license_type': license_type,
        })

    @http.route('/spc/apply/nma_media_license/<string:license_type>/final-submit',
                type='http', auth='public', website=True, methods=['POST'])
    def nma_ml_final_submit(self, license_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        from odoo import fields as odoo_fields
        step1 = request.session.get('nma_step1_data', {})
        step2 = request.session.get('nma_step2_data', {})
        step3 = request.session.get('nma_step3_data', {})
        step3_files = request.session.get('nma_step3_files', {})
        step4 = request.session.get('nma_step4_data', {})
        step5 = request.session.get('nma_step5_data', {})
        vals = {
            'license_type': license_type,
            'partner_id': request.env.user.partner_id.id,
            'approved_company_id': request.session.get('spc_selected_company_id'),
            'state': 'submitted',
            'submission_date': odoo_fields.Datetime.now(),
            'company_name': step1.get('company_name', ''),
            'manager_name': step1.get('manager_name', ''),
            'manager_first_name': step1.get('manager_first_name', ''),
            'manager_last_name': step1.get('manager_last_name', ''),
            'step1_remarks': step1.get('step1_remarks', ''),
            'num_activities': step2.get('num_activities', '') or False,
            'activity_1': step2.get('activity_1', '') or False,
            'activity_2': step2.get('activity_2', '') or False,
            'activity_3': step2.get('activity_3', '') or False,
            'activity_4': step2.get('activity_4', '') or False,
            'activity_5': step2.get('activity_5', '') or False,
            'business_plan': step2.get('business_plan', ''),
            'shareholder_name': step3.get('shareholder_name', ''),
            'shareholder_uae_resident': step3.get('shareholder_uae_resident', 'no'),
            'declaration_accepted': step4.get('declaration_accepted', False),
            'additional_remarks': step5.get('additional_remarks', ''),
            'total_amount': 525.0 if license_type == 'cancellation' else 535.0,
        }
        dob = step1.get('manager_dob', '')
        if dob:
            try:
                from datetime import datetime as dt
                vals['manager_dob'] = dt.strptime(dob, '%Y-%m-%d').date()
            except Exception:
                pass
        for f in ['doc_mro_form', 'doc_photo', 'doc_emirates_id',
                  'doc_power_of_attorney', 'doc_request_form']:
            if step3_files.get(f):
                vals[f] = step3_files[f]
            if step3_files.get(f + '_name'):
                vals[f + '_name'] = step3_files[f + '_name']
        draft_id = request.session.pop('nma_draft_id', None)
        if draft_id:
            rec = request.env['spc.nma.media.license'].sudo().browse(draft_id)
            if rec.exists():
                rec.write(vals)
                record = rec
            else:
                record = request.env['spc.nma.media.license'].sudo().create(vals)
        else:
            record = request.env['spc.nma.media.license'].sudo().create(vals)
        for key in ['nma_step1_data', 'nma_step2_data', 'nma_step3_data',
                    'nma_step3_files', 'nma_step4_data', 'nma_step5_data',
                    'nma_license_type']:
            request.session.pop(key, None)
        return request.redirect('/spc/payment/nma_media_license/' + str(record.id))

    # ══════════════════════════════════════════════════
    # NMA PERMIT
    # ══════════════════════════════════════════════════

    @http.route('/spc/company-management/nma-permit',
                type='http', auth='public', website=True)
    def nma_permit_main(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_nma_permit_main', {})

    @http.route('/spc/company-management/nma-permit/<string:permit_type>/additional',
                type='http', auth='public', website=True)
    def nma_permit_service_detail(self, permit_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_nma_permit_service_detail', {
            'permit_type': permit_type,
        })

    @http.route('/spc/apply/nma_permit/step1',
                type='http', auth='public', website=True, methods=['GET', 'POST'])
    def nma_permit_step1(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        if request.httprequest.method == 'POST':
            pt = kw.get('permit_type', '')
            data = {
                'permit_type': pt,
                # Printing fields
                'publication_type': kw.get('publication_type', ''),
                'book_title': kw.get('book_title', ''),
                'author_name': kw.get('author_name', '') or kw.get('author_name_map', '') or kw.get('author_name_brochures', ''),
                'language': kw.get('language', '') or kw.get('language_map', '') or kw.get('language_brochures', '') or kw.get('language_movie', ''),
                'article_type': kw.get('article_type', ''),
                'issue_number': kw.get('issue_number', ''),
                'publish_method': kw.get('publish_method', ''),
                'cover_type': kw.get('cover_type', ''),
                'subject_category': kw.get('subject_category', ''),
                'subject_subcategory': kw.get('subject_subcategory', ''),
                'publication_title': kw.get('pub_title_map', '') or kw.get('pub_title_brochures', '') or kw.get('pub_title_movie', ''),
                # Trading fields
                'trade_format': kw.get('trade_format', ''),
                'book_title_trading': kw.get('book_title_trading', ''),
                'author_name_trading': kw.get('author_name_trading', ''),
                'subject_category_trading': kw.get('subject_category_trading', ''),
                'subject_subcategory_trading': kw.get('subject_subcategory_trading', ''),
                'print_year': kw.get('print_year', ''),
                'distributor_agency': kw.get('distributor_agency', ''),
                'national_depository_number': kw.get('national_depository_number', ''),
                'isbn': kw.get('isbn', ''),
                'version_number': kw.get('version_number', ''),
                'how_obtained': kw.get('how_obtained', ''),
                # Text permit
                'text_publication_type': kw.get('text_publication_type', ''),
                # Regulatory
                'material_type': kw.get('material_type', ''),
                'reg_title': kw.get('reg_title', ''),
                'reg_number_of_title': kw.get('reg_number_of_title', '') or kw.get('reg_number_of_title_brochures', ''),
                # Remarks
                'step1_remarks': (kw.get('step1_remarks', '') or kw.get('step1_remarks_trading', '')
                                  or kw.get('step1_remarks_text', '') or kw.get('step1_remarks_regulatory', '')),
            }
            request.session['nma_permit_step1'] = data
            return request.redirect('/spc/apply/nma_permit/step2')
        step1_data = request.session.get('nma_permit_step1', {})
        if not request.session.get('nma_permit_draft_id'):
            _partner_id = request.env.user.partner_id.id
            existing = request.env['spc.nma.permit'].sudo().search([
                ('partner_id', '=', _partner_id),
                ('state', '=', 'draft'),
            ], order='id desc', limit=1)
            if existing:
                request.session['nma_permit_draft_id'] = existing.id
            else:
                from odoo import fields as odoo_fields
                rec = request.env['spc.nma.permit'].sudo().create({
                    'partner_id': _partner_id,
                    'approved_company_id': request.session.get('spc_selected_company_id'),
                    'state': 'draft', 'current_step': 1,
                    'started_date': odoo_fields.Datetime.now(),
                })
                request.session['nma_permit_draft_id'] = rec.id
        return request.render('spc_portal.template_nma_permit_step1', {
            'step1_data': step1_data,
        })

    @http.route('/spc/apply/nma_permit/step2',
                type='http', auth='public', website=True, methods=['GET', 'POST'])
    def nma_permit_step2(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        if request.httprequest.method == 'POST':
            import base64
            files_data = {}
            for field in ['doc_undertaking', 'doc_soft_copy', 'doc_media_license',
                          'doc_copy_book', 'doc_declaration']:
                f = request.httprequest.files.get(field)
                if f and f.filename:
                    files_data[field] = base64.b64encode(f.read()).decode('utf-8')
                    files_data[field + '_name'] = f.filename
            request.session['nma_permit_step2_files'] = files_data
            return request.redirect('/spc/apply/nma_permit/step3')
        return request.render('spc_portal.template_nma_permit_step2', {})

    @http.route('/spc/apply/nma_permit/step3',
                type='http', auth='public', website=True, methods=['GET', 'POST'])
    def nma_permit_step3(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        if request.httprequest.method == 'POST':
            data = {
                'declaration_accepted': kw.get('declaration_accepted', 'off') == 'on',
            }
            request.session['nma_permit_step3'] = data
            return request.redirect('/spc/apply/nma_permit/step4')
        step3_data = request.session.get('nma_permit_step3', {})
        return request.render('spc_portal.template_nma_permit_step3', {
            'step3_data': step3_data,
        })

    @http.route('/spc/apply/nma_permit/step4',
                type='http', auth='public', website=True, methods=['GET'])
    def nma_permit_step4(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_nma_permit_step4', {
            'step1': request.session.get('nma_permit_step1', {}),
            'step3': request.session.get('nma_permit_step3', {}),
        })

    @http.route('/spc/apply/nma_permit/step5',
                type='http', auth='public', website=True, methods=['GET'])
    def nma_permit_step5(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_nma_permit_step5', {})

    @http.route('/spc/apply/nma_permit/final-submit',
                type='http', auth='public', website=True, methods=['POST'])
    def nma_permit_final_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        from odoo import fields as odoo_fields
        step1 = request.session.get('nma_permit_step1', {})
        step2_files = request.session.get('nma_permit_step2_files', {})
        step3 = request.session.get('nma_permit_step3', {})
        vals = {
            'partner_id': request.env.user.partner_id.id,
            'approved_company_id': request.session.get('spc_selected_company_id'),
            'state': 'submitted',
            'submission_date': odoo_fields.Datetime.now(),
            'permit_type': step1.get('permit_type', '') or False,
            'publication_type': step1.get('publication_type', '') or False,
            'book_title': step1.get('book_title', ''),
            'author_name': step1.get('author_name', ''),
            'language': step1.get('language', ''),
            'article_type': step1.get('article_type', '') or False,
            'issue_number': step1.get('issue_number', ''),
            'publish_method': step1.get('publish_method', '') or False,
            'cover_type': step1.get('cover_type', '') or False,
            'subject_category': step1.get('subject_category', '') or False,
            'subject_subcategory': step1.get('subject_subcategory', ''),
            'publication_title': step1.get('publication_title', ''),
            'step1_remarks': step1.get('step1_remarks', ''),
            'trade_format': step1.get('trade_format', '') or False,
            'print_year': step1.get('print_year', ''),
            'distributor_agency': step1.get('distributor_agency', ''),
            'national_depository_number': step1.get('national_depository_number', ''),
            'isbn': step1.get('isbn', ''),
            'version_number': step1.get('version_number', ''),
            'how_obtained': step1.get('how_obtained', '') or False,
            'text_publication_type': step1.get('text_publication_type', '') or False,
            'material_type': step1.get('material_type', '') or False,
            'number_of_title': step1.get('reg_number_of_title', ''),
            'reg_title': step1.get('reg_title', ''),
            'declaration_accepted': step3.get('declaration_accepted', False),
            'total_amount': 210.0,
        }
        for f in ['doc_undertaking', 'doc_soft_copy', 'doc_media_license',
                  'doc_copy_book', 'doc_declaration']:
            if step2_files.get(f):
                vals[f] = step2_files[f]
            if step2_files.get(f + '_name'):
                vals[f + '_name'] = step2_files[f + '_name']
        draft_id = request.session.pop('nma_permit_draft_id', None)
        if draft_id:
            rec = request.env['spc.nma.permit'].sudo().browse(draft_id)
            if rec.exists():
                rec.write(vals)
                record = rec
            else:
                record = request.env['spc.nma.permit'].sudo().create(vals)
        else:
            record = request.env['spc.nma.permit'].sudo().create(vals)
        for key in ['nma_permit_step1', 'nma_permit_step2_files', 'nma_permit_step3']:
            request.session.pop(key, None)
        return request.redirect('/spc/payment/nma_permit/' + str(record.id))

    # ══════════════════════════════════════════════════
    # EMPLOYEE LIST
    # ══════════════════════════════════════════════════

    @http.route('/spc/company-management/employee-list',
                type='http', auth='public', website=True)
    def el_main(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_el_main', {})

    @http.route('/spc/company-management/employee-list/<string:el_type>/additional',
                type='http', auth='public', website=True)
    def el_service_detail(self, el_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_el_service_detail', {
            'el_type': el_type,
        })

    @http.route('/spc/apply/employee_list/step1',
                type='http', auth='public', website=True, methods=['GET', 'POST'])
    def el_step1(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        if request.httprequest.method == 'POST':
            data = {
                'declaration_accepted': kw.get('declaration_accepted', 'off') == 'on',
            }
            request.session['el_step1'] = data
            return request.redirect('/spc/apply/employee_list/step2')
        step1 = request.session.get('el_step1', {})
        if not request.session.get('el_draft_id'):
            _partner_id = request.env.user.partner_id.id
            existing = request.env['spc.employee.list'].sudo().search([
                ('partner_id', '=', _partner_id),
                ('state', '=', 'draft'),
            ], order='id desc', limit=1)
            if existing:
                request.session['el_draft_id'] = existing.id
            else:
                from odoo import fields as odoo_fields
                rec = request.env['spc.employee.list'].sudo().create({
                    'partner_id': _partner_id,
                    'approved_company_id': request.session.get('spc_selected_company_id'),
                    'state': 'draft', 'current_step': 1,
                    'started_date': odoo_fields.Datetime.now(),
                })
                request.session['el_draft_id'] = rec.id
        return request.render('spc_portal.template_el_step1', {
            'step1': step1,
        })

    @http.route('/spc/apply/employee_list/step2',
                type='http', auth='public', website=True, methods=['GET'])
    def el_step2(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_el_step2', {
            'step1': request.session.get('el_step1', {}),
        })

    @http.route('/spc/apply/employee_list/step3',
                type='http', auth='public', website=True, methods=['GET'])
    def el_step3(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_el_step3', {})

    @http.route('/spc/apply/employee_list/final-submit',
                type='http', auth='public', website=True, methods=['POST'])
    def el_final_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        from odoo import fields as odoo_fields
        step1 = request.session.get('el_step1', {})
        vals = {
            'partner_id': request.env.user.partner_id.id,
            'approved_company_id': request.session.get('spc_selected_company_id'),
            'state': 'submitted',
            'submission_date': odoo_fields.Datetime.now(),
            'declaration_accepted': step1.get('declaration_accepted', False),
            'total_amount': 385.0,
        }
        draft_id = request.session.pop('el_draft_id', None)
        if draft_id:
            rec = request.env['spc.employee.list'].sudo().browse(draft_id)
            if rec.exists():
                rec.write(vals)
                record = rec
            else:
                record = request.env['spc.employee.list'].sudo().create(vals)
        else:
            record = request.env['spc.employee.list'].sudo().create(vals)
        request.session.pop('el_step1', None)
        return request.redirect('/spc/payment/employee_list/' + str(record.id))

    # ══════════════════════════════════════════════════
    # EMPLOYEE LIST
    # ══════════════════════════════════════════════════

    @http.route('/spc/company-management/employee-list',
                type='http', auth='public', website=True)
    def el_main(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_el_main', {})

    @http.route('/spc/company-management/employee-list/<string:el_type>/additional',
                type='http', auth='public', website=True)
    def el_service_detail(self, el_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_el_service_detail', {'el_type': el_type})

    @http.route('/spc/apply/employee_list/step1',
                type='http', auth='public', website=True, methods=['GET', 'POST'])
    def el_step1(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        if request.httprequest.method == 'POST':
            request.session['el_step1'] = {
                'declaration_accepted': kw.get('declaration_accepted', 'off') == 'on',
            }
            return request.redirect('/spc/apply/employee_list/step2')
        return request.render('spc_portal.template_el_step1', {
            'step1': request.session.get('el_step1', {}),
        })

    @http.route('/spc/apply/employee_list/step2',
                type='http', auth='public', website=True, methods=['GET'])
    def el_step2(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_el_step2', {
            'step1': request.session.get('el_step1', {}),
        })

    @http.route('/spc/apply/employee_list/step3',
                type='http', auth='public', website=True, methods=['GET'])
    def el_step3(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_el_step3', {})

    @http.route('/spc/apply/employee_list/final-submit',
                type='http', auth='public', website=True, methods=['POST'])
    def el_final_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        from odoo import fields as odoo_fields
        step1 = request.session.get('el_step1', {})
        vals = {
            'partner_id': request.env.user.partner_id.id,
            'approved_company_id': request.session.get('spc_selected_company_id'),
            'state': 'submitted',
            'submission_date': odoo_fields.Datetime.now(),
            'declaration_accepted': step1.get('declaration_accepted', False),
            'total_amount': 385.0,
        }
        record = request.env['spc.employee.list'].sudo().create(vals)
        request.session.pop('el_step1', None)
        return request.redirect('/spc/payment/employee_list/' + str(record.id))

    # ══════════════════════════════════════════════════
    # EMPLOYEE MANAGEMENT
    # ══════════════════════════════════════════════════
    @http.route('/spc/employee-management', type='http', auth='public', website=True, csrf=False)
    def employee_management(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        customer_id = request.session.get('spc_selected_customer_id')
        company_id = request.session.get('spc_selected_company_id')
        customer = None
        selected_company = None
        all_companies = []
        if customer_id:
            rec = request.env['res.partner'].sudo().browse(customer_id)
            if rec.exists():
                customer = rec
            all_companies = request.env['spc.approved.company'].sudo().search([
                ('partner_id', '=', customer_id), ('active', '=', True),
            ], order='company_name asc')
        if company_id:
            comp = request.env['spc.approved.company'].sudo().browse(company_id)
            if comp.exists():
                selected_company = comp
        return request.render('spc_portal.template_employee_management', {
            'customer': customer,
            'company_name': selected_company.company_name if selected_company else '',
            'all_companies': all_companies,
            'selected_company_id': company_id,
        })

    @http.route('/spc/employee-management/service/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def employee_management_service(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        # Change of Status service detail
        if service_type and 'change_status' in service_type:
            return request.render('spc_portal.template_cos_service_detail', {
                'service_type': service_type,
            })
        return request.render('spc_portal.template_employee_management', {'service_type': service_type})

    # ══════════════════════════════════════════════════
    # FACILITY MANAGEMENT
    # ══════════════════════════════════════════════════
    @http.route('/spc/facility-management', type='http', auth='public', website=True, csrf=False)
    def facility_management(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        customer_id = request.session.get('spc_selected_customer_id')
        company_id = request.session.get('spc_selected_company_id')
        customer = None
        selected_company = None
        all_companies = []
        if customer_id:
            rec = request.env['res.partner'].sudo().browse(customer_id)
            if rec.exists():
                customer = rec
            all_companies = request.env['spc.approved.company'].sudo().search([
                ('partner_id', '=', customer_id), ('active', '=', True),
            ], order='company_name asc')
        if company_id:
            comp = request.env['spc.approved.company'].sudo().browse(company_id)
            if comp.exists():
                selected_company = comp
        return request.render('spc_portal.template_facility_management', {
            'customer': customer,
            'company_name': selected_company.company_name if selected_company else '',
            'all_companies': all_companies,
            'selected_company_id': company_id,
        })

    @http.route('/spc/facility-management/service/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def facility_management_service(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service = {
            'tag': 'New',
            'image_text': 'Facility\nManagement',
            'description': 'This service allows existing Sharjah Publishing City Free Zone clients to submit requests related to the facilities they would like to rent.',
        }
        return request.render('spc_portal.template_facility_service_detail', {
            'service_type': service_type,
            'service': service,
        })

    @http.route('/spc/facility-management/apply/<string:service_type>', type='http', auth='public', website=True, csrf=False, methods=['GET', 'POST'])
    def facility_management_apply(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        if request.httprequest.method == 'POST':
            import base64
            data = {
                'complaint_category': kw.get('complaint_category', ''),
                'incident_type': kw.get('incident_type', ''),
                'office_number': kw.get('office_number', ''),
                'contact_name': kw.get('contact_name', ''),
                'contact_number': kw.get('contact_number', ''),
                'complaint_description': kw.get('complaint_description', ''),
            }
            request.session['fm_step1'] = data
            f = request.httprequest.files.get('doc_image')
            if f and f.filename:
                request.session['fm_step1_files'] = {
                    'doc_image': base64.b64encode(f.read()).decode('utf-8'),
                    'doc_image_name': f.filename,
                }
            return request.redirect('/spc/facility-management/step2')
        if not request.session.get('fm_draft_id'):
            _partner_id = request.env.user.partner_id.id
            existing = request.env['spc.facility.management'].sudo().search([
                ('partner_id', '=', _partner_id),
                ('state', '=', 'draft'),
            ], order='id desc', limit=1)
            if existing:
                request.session['fm_draft_id'] = existing.id
            else:
                from odoo import fields as odoo_fields
                rec = request.env['spc.facility.management'].sudo().create({
                    'partner_id': _partner_id,
                    'approved_company_id': request.session.get('spc_selected_company_id'),
                    'state': 'draft', 'current_step': 1,
                    'started_date': odoo_fields.Datetime.now(),
                })
                request.session['fm_draft_id'] = rec.id

        _fm_price = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'facility_management'),
            ('is_active', '=', True)
        ], limit=1)
        _fm_base = _fm_price.amount if _fm_price else 0.0
        return request.render('spc_portal.template_fm_step1', {
            'step1': request.session.get('fm_step1', {}),
            'base_price': _fm_base,
        })

    # ══════════════════════════════════════════════════
    # CONCIERGE SERVICES
    # ══════════════════════════════════════════════════
    @http.route('/spc/concierge-services', type='http', auth='public', website=True, csrf=False)
    def concierge_services(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        customer_id = request.session.get('spc_selected_customer_id')
        company_id = request.session.get('spc_selected_company_id')
        customer = None
        selected_company = None
        all_companies = []
        if customer_id:
            rec = request.env['res.partner'].sudo().browse(customer_id)
            if rec.exists():
                customer = rec
            all_companies = request.env['spc.approved.company'].sudo().search([
                ('partner_id', '=', customer_id), ('active', '=', True),
            ], order='company_name asc')
        if company_id:
            comp = request.env['spc.approved.company'].sudo().browse(company_id)
            if comp.exists():
                selected_company = comp
        # Fetch service prices for concierge cards
        def get_price(service_type):
            p = request.env['spc.service.price'].sudo().search([
                ('service_type', '=', service_type),
                ('is_active', '=', True)
            ], limit=1)
            return p.amount if p else 0.0

        return request.render('spc_portal.template_concierge_services', {
            'customer': customer,
            'company_name': selected_company.company_name if selected_company else '',
            'all_companies': all_companies,
            'selected_company_id': company_id,
            'price_vip_medical_eid': get_price('vip_medical_eid'),
            'price_company_stamp': get_price('company_stamp'),
            'price_dependent_visa': get_price('dependent_visa'),
            'price_medical_new': get_price('medical_new'),
            'price_medical_renewal': get_price('medical_renewal'),
            'price_meeting_room': get_price('meeting_room'),
            'price_mofa': get_price('mofa'),
            'price_po_box': get_price('po_box'),
            'price_phone_answering': get_price('phone_answering'),
            'price_document_delivery': get_price('document_delivery'),
            'price_document_delivery_courier': get_price('document_delivery_courier'),
        })

    @http.route('/spc/concierge-services/service/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def concierge_service_detail(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        customer = None
        try:
            partner_id = request.session.get('spc_selected_customer_id') or request.session.get('spc_partner_id')
            if partner_id:
                customer = request.env['res.partner'].sudo().browse(partner_id)
        except Exception:
            pass
        services_map = {
            'doc_delivery_driver': {
                'name': 'Document Delivery - Driver',
                'type': 'driver',
                'fee': 'AED 10.00',
                'detail_route': '/spc/concierge/doc-delivery/driver/detail',
            },
            'doc_delivery_courier': {
                'name': 'Document Delivery - Courier',
                'type': 'courier',
                'fee': 'AED 10.00',
                'detail_route': '/spc/concierge/doc-delivery/courier/detail',
            },
            'phone_answering': {
                'name': 'Phone Answering',
                'tag': 'New',
                'fee': 'AED 10.00',
                'detail_route': '/spc/concierge/phone-answering/new/detail',
            },
            'po_box_new': {
                'name': 'PO Box - New',
                'tag': 'New',
                'fee': 'AED 1,500.00',
                'detail_route': '/spc/concierge/po-box/new/detail',
            },
            'po_box_renewal': {
                'name': 'PO Box - Renewal',
                'tag': 'Renew',
                'fee': 'AED 1,500.00',
                'detail_route': '/spc/concierge/po-box/renewal/detail',
            },
            'driving_license': {
                'name': 'Driving License',
                'tag': None,
                'fee': 0,
                'description': 'Driving License services',
                'apply_url': '/spc/concierge/driving-license',
                'image_title': 'Driving License',
                'bg_color': 'linear-gradient(135deg,#1a3c6e,#1565c0)',
                'is_submenu': True,
            },
            'vip_medical_eid': {
                'name': 'VIP Medical and EID (Including Transportation)',
                'tag': 'New',
                'fee': 3025,
                'description': '''The Medical and Emirates ID assistance service helps clients undergo a Medical Fitness Test and apply for Emirates ID.

Medical Fitness Test:

The Medical Fitness Test is a mandatory examination the UAE government requires for individuals applying for residency visas. The objective is to ensure all applicants are free from communicable and infectious diseases. A successful outcome will generate a certificate of good health, "Fit." The examination includes an X-ray and blood test.

Emirates ID:

The Emirates Identity Card (EID) is a mandatory identification card issued to citizens and residents of the United Arab Emirates (UAE). It allows access to government services, banking, obtaining a mobile number, and many other related services.

Pricing: AED 3025.00

Input Details:
· Passport copy
· Entry visa with Change of Status / Entry stamp copy
· Passport-sized photo

Output details:

1. Application submission:
o Submitting a medical test and Emirates ID application to relevant authorities.

2. Appointment Scheduling:
o Scheduling a medical test and biometrics appointment wherever applicable.

3. Escort service to medical test centers and biometrics (if applicable):
o Pick and drop service along with in-center assistance.


Please note transportation is provided for Dubai, Sharjah, and Ajman only.''',
                'apply_url': '/spc/concierge/vip-medical-eid',
                'image_title': 'VIP Medical & EID',
                'bg_color': 'linear-gradient(135deg,#1a3c6e,#2a6db5)',
            },
            'company_stamp': {
                'name': 'Company Stamp',
                'tag': 'New',
                'fee': 260,
                'description': '''This service allows a company to obtain an official rubber stamp.

This involves creating the stamp with your company's details and registering it with the Free Zone authorities.

Timeline

1 Business day

Fees

AED 260.00''',
                'apply_url': '/spc/concierge/company-stamp',
                'image_title': 'Company Stamp',
                'bg_color': 'linear-gradient(135deg,#1a3c6e,#2d6a4f)',
            },
            'dependent_visa': {
                'name': 'Dependent Visa',
                'tag': 'New',
                'fee': 5010,
                'description': '''This Visa permits sponsoring of parents, spouse, and children (below 18 years of age).

This service allows to client to create the permit issued to non-citizens/expats allowing them to reside in the UAE for a period of time.

Requirement(s)
1. Physical Emirates ID of the Sponsor
2. Passport Copy of the Sponsor
3. Attested Tenancy Contract
4. Attested marriage certificate in Arabic or duly translated into Arabic (if applicable)
5. Attested Birth Certificate (If applicable)
6. Latest Utility Bills

Important Notes:
- The sponsor must have a minimum salary of AED 4,000, or AED 3,000 plus accommodation for sponsoring spouse and children. A minimum salary of AED 15,000 is required for sponsoring parents.
- Male and female family members above 18 years must undergo and pass a medical fitness test.
- A mother can sponsor her children in special cases approved by ICP, and in such cases, an NOC from the father issued by the UAE Court is mandatory.
- A resident can sponsor parents, but the residence visa will be granted on a yearly basis regardless of the sponsor's visa validity. An Affidavit (Dependency Certificate) attested by the sponsor's Consulate, confirming responsibility for the parents' care and wellbeing, is required.''',
                'apply_url': '/spc/concierge/dependent-visa',
                'image_title': 'Dependent Visa',
                'bg_color': 'linear-gradient(135deg,#6b2fa0,#1a3c6e)',
            },
            'phone_answering': {
                'name': 'Phone Answering',
                'tag': 'New',
                'fee': 'AED 10.00',
                'detail_route': '/spc/concierge/phone-answering/new/detail',
            },
            'driving_license': {
                'name': 'Driving License',
                'tag': None,
                'fee': 0,
                'description': 'Driving License services',
                'apply_url': '/spc/concierge/driving-license',
                'image_title': 'Driving License',
                'bg_color': 'linear-gradient(135deg,#1a3c6e,#1565c0)',
                'is_submenu': True,
            },
            'vip_medical_eid': {
                'name': 'VIP Medical and EID (Including Transportation)',
                'tag': 'New',
                'fee': 3025,
                'description': 'VIP Medical and EID service description',
                'apply_url': '/spc/concierge/vip-medical-eid',
            },
            'company_stamp': {
                'name': 'Company Stamp',
                'tag': 'New',
                'fee': 260,
                'description': 'Company Stamp service description',
                'apply_url': '/spc/concierge/company-stamp',
            },
            'dependent_visa': {
                'name': 'Dependent Visa',
                'tag': 'New',
                'fee': 5010,
                'description': 'Dependent Visa service description',
                'apply_url': '/spc/concierge/dependent-visa',
            },
            'eid_replacement': {
                'name': 'EID Replacement',
                'tag': 'New',
                'fee': 560,
            'description': 'Emirates ID replacement service. Requirements: High-Resolution Photo, Emirates ID Copy (Front & Back), Passport Copy. Timeline: 5-7 business days. Fees: AED 550.',
                'apply_url': '/spc/apply/eid_replacement/step1',
            },
            'vat_registration': {
                'name': 'VAT Registration/Deregistration',
                'tag': 'New',
                'fee': 0,
                'description': 'VAT Registration and Deregistration services.',
                'apply_url': '/spc/concierge-services/apply/vat_registration',
            },
            'corporate_tax': {
                'name': 'Corporate Tax Registration - Starter Package',
                'tag': 'New',
                'fee': 0,
                'description': 'Corporate Tax Registration services.',
                'apply_url': '/spc/concierge-services/apply/corporate_tax',
            },
            'bookkeeping': {
                'name': 'Bookkeeping',
                'tag': 'New',
                'fee': 0,
                'description': 'Bookkeeping services.',
                'apply_url': '/spc/concierge-services/apply/bookkeeping',
            },
            're_entry_permit': {
                'name': 'Re-Entry Permit',
                'tag': 'New',
                'fee': 0,
                'description': 'Re-Entry Permit services.',
                'apply_url': '/spc/concierge-services/apply/re_entry_permit',
            },
            'lease_documents': {
                'name': 'Lease Documents',
                'tag': 'New',
                'fee': 0.0,
                'description': 'Lease Documents services.',
                'apply_url': '/spc/concierge-services/apply/lease_documents',
            },
        }
        service = services_map.get(service_type, {
            'name': service_type.replace('_', ' ').title(),
            'tag': 'New',
            'fee': 0,
            'description': 'Service details coming soon.',
            'apply_url': '/spc/concierge-services/apply/' + service_type,
        })
        # eid_replacement has its own detail page
        if service_type == 'eid_replacement':
            return request.redirect('/spc/concierge/eid-replacement')
        if service_type == 'po_box_new':
            return request.redirect('/spc/concierge/po-box/new/detail')
        if service_type == 'po_box_renewal':
            return request.redirect('/spc/concierge/po-box/renewal/detail')
        if service_type == 'phone_answering':
            return request.redirect('/spc/concierge/phone-answering/new/detail')
        if service_type == 'driving_license':
            return request.redirect('/spc/concierge/driving-license')
        if service_type == 'vip_medical_eid':
            return request.redirect('/spc/concierge/vip-medical-eid/detail')
        if service_type == 'company_stamp':
            return request.redirect('/spc/concierge/company-stamp/detail')
        if service_type == 'dependent_visa':
            return request.redirect('/spc/concierge/dependent-visa/detail')
        if service_type == 'doc_delivery_driver':
            return request.redirect('/spc/concierge/doc-delivery/driver/detail')
        if service_type == 'doc_delivery_courier':
            return request.redirect('/spc/concierge/doc-delivery/courier/detail')
        if service_type in ['lease_documents', 're_entry_permit', 'reentry_permit']:
            return request.redirect('/spc/concierge/lease-document?type=new')
        return request.render('spc_portal.template_concierge_service_detail', {
            'service_type': service_type,
            'service': service,
            'customer': customer,
        })

    @http.route('/spc/concierge-services/apply/<string:service_type>', type='http', auth='public', website=True, csrf=False, methods=['GET', 'POST'])
    def concierge_apply(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        # Redirect known services to their own pages
        if service_type in ['lease_docs', 'lease_documents']:
            return request.redirect('/spc/concierge/lease-document?type=new')
        if service_type in ['reentry_permit', 're_entry_permit']:
            return request.redirect('/spc/concierge/reentry-permit')
        if 'medical' in service_type:
            mtype = 'renewal' if 'renewal' in service_type else 'new_residency'
            return request.redirect('/spc/concierge/medical?type=' + mtype)
        if 'meeting' in service_type:
            return request.redirect('/spc/concierge/meeting-room')
        if 'mofa' in service_type:
            return request.redirect('/spc/concierge/mofa-attestation')
        return request.render('spc_portal.template_concierge_apply', {'service_type': service_type, 'fee': 0.0})

    # ══════════════════════════════════════════════════
    # FACILITY BOOKINGS
    # ══════════════════════════════════════════════════
    @http.route('/spc/facility-bookings', type='http', auth='public', website=True, csrf=False)
    def facility_bookings(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        # Check if template exists
        template = request.env['ir.ui.view'].sudo().search([
            ('key', '=', 'spc_portal.template_facility_bookings')
        ], limit=1)
        if template:
            return request.render('spc_portal.template_facility_bookings', {})
        return request.render('spc_portal.template_facility_management', {})

    # ══════════════════════════════════════════════════
    # FACILITY MANAGEMENT - NEW ROUTES
    # ══════════════════════════════════════════════════

    @http.route('/spc/facility-management/apply/new',
                type='http', auth='public', website=True, methods=['GET', 'POST'])
    def fm_step1(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        if request.httprequest.method == 'POST':
            import base64
            data = {
                'complaint_category': kw.get('complaint_category', ''),
                'incident_type': kw.get('incident_type', ''),
                'office_number': kw.get('office_number', ''),
                'contact_name': kw.get('contact_name', ''),
                'contact_number': kw.get('contact_number', ''),
                'complaint_description': kw.get('complaint_description', ''),
            }
            request.session['fm_step1'] = data
            f = request.httprequest.files.get('doc_image')
            if f and f.filename:
                files_data = {
                    'doc_image': base64.b64encode(f.read()).decode('utf-8'),
                    'doc_image_name': f.filename,
                }
                request.session['fm_step1_files'] = files_data
            return request.redirect('/spc/facility-management/step2')

        _fm_price2 = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'facility_management'),
            ('is_active', '=', True)
        ], limit=1)
        _fm_base2 = _fm_price2.amount if _fm_price2 else 0.0
        return request.render('spc_portal.template_fm_step1', {
            'step1': request.session.get('fm_step1', {}),
            'base_price': _fm_base2,
        })

    @http.route('/spc/facility-management/save-exit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def fm_save_exit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        import base64
        step = kw.get('current_step', '1')
        if step == '1':
            data = {
                'complaint_category': kw.get('complaint_category', ''),
                'incident_type': kw.get('incident_type', ''),
                'office_number': kw.get('office_number', ''),
                'contact_name': kw.get('contact_name', ''),
                'contact_number': kw.get('contact_number', ''),
                'complaint_description': kw.get('complaint_description', ''),
            }
            request.session['fm_step1'] = data
            f = request.httprequest.files.get('doc_image')
            if f and f.filename:
                request.session['fm_step1_files'] = {
                    'doc_image': base64.b64encode(f.read()).decode('utf-8'),
                    'doc_image_name': f.filename,
                }
        elif step == '2':
            request.session['fm_step2'] = {
                'declaration_accepted': kw.get('declaration_accepted', 'off') == 'on',
            }
        request.session.modified = True
        return request.redirect('/spc/facility-management')

    @http.route('/spc/facility-management/step2',
                type='http', auth='public', website=True, methods=['GET', 'POST'])
    def fm_step2(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        if request.httprequest.method == 'POST':
            request.session['fm_step2'] = {
                'declaration_accepted': kw.get('declaration_accepted', 'off') == 'on',
            }
            return request.redirect('/spc/facility-management/step3')
        return request.render('spc_portal.template_fm_step2', {})

    @http.route('/spc/facility-management/step3',
                type='http', auth='public', website=True, methods=['GET'])
    def fm_step3(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_fm_step3', {
            'step1': request.session.get('fm_step1', {}),
            'step2': request.session.get('fm_step2', {}),
        })

    @http.route('/spc/facility-management/step4',
                type='http', auth='public', website=True, methods=['GET'])
    def fm_step4(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_fm_step4', {})

    @http.route('/spc/facility-management/final-submit',
                type='http', auth='public', website=True, methods=['POST'])
    def fm_final_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        from odoo import fields as odoo_fields
        step1 = request.session.get('fm_step1', {})
        step1_files = request.session.get('fm_step1_files', {})
        step2 = request.session.get('fm_step2', {})
        vals = {
            'partner_id': request.env.user.partner_id.id,
            'approved_company_id': request.session.get('spc_selected_company_id'),
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
        draft_id = request.session.pop('fm_draft_id', None)
        if draft_id:
            rec = request.env['spc.facility.management'].sudo().browse(draft_id)
            if rec.exists():
                rec.write(vals)
                record = rec
            else:
                record = request.env['spc.facility.management'].sudo().create(vals)
        else:
            record = request.env['spc.facility.management'].sudo().create(vals)
        for key in ['fm_step1', 'fm_step1_files', 'fm_step2']:
            request.session.pop(key, None)
        return request.redirect('/spc/payment/facility_management/' + str(record.id))

    # ══════════════════════════════════════════════════
    # CHANGE OF STATUS
    # ══════════════════════════════════════════════════

    @http.route('/spc/employee-management/change-of-status',
                type='http', auth='public', website=True)
    def cos_main(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_cos_main', {})

    @http.route('/spc/employee-management/change-of-status/save-exit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def cos_save_exit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        import base64
        step = kw.get('current_step', '1')
        if step == '1':
            data = {
                'applicant_name': kw.get('applicant_name', ''),
                'visa_status': kw.get('visa_status', ''),
                'remarks': kw.get('remarks', ''),
            }
            request.session['cos_step1'] = data
            files_data = {}
            for field in ['doc_cancelled_visa', 'doc_valid_visa']:
                f = request.httprequest.files.get(field)
                if f and f.filename:
                    files_data[field] = base64.b64encode(f.read()).decode('utf-8')
                    files_data[field + '_name'] = f.filename
            if files_data:
                request.session['cos_step1_files'] = files_data
        elif step == '2':
            request.session['cos_step2'] = {
                'first_name': kw.get('first_name', ''),
                'last_name': kw.get('last_name', ''),
            }
        elif step == '3':
            request.session['cos_step3'] = {
                'declaration_accepted': kw.get('declaration_accepted', 'off') == 'on',
            }
        request.session.modified = True
        return request.redirect('/spc/employee-management')

    @http.route('/spc/apply/change_of_status/step1',
                type='http', auth='public', website=True, methods=['GET', 'POST'])
    def cos_step1(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        if request.httprequest.method == 'POST':
            import base64
            data = {
                'applicant_name': kw.get('applicant_name', ''),
                'visa_status': kw.get('visa_status', ''),
                'remarks': kw.get('remarks', ''),
            }
            request.session['cos_step1'] = data
            files_data = {}
            for field in ['doc_cancelled_visa', 'doc_valid_visa']:
                f = request.httprequest.files.get(field)
                if f and f.filename:
                    files_data[field] = base64.b64encode(f.read()).decode('utf-8')
                    files_data[field + '_name'] = f.filename
            request.session['cos_step1_files'] = files_data
            return request.redirect('/spc/apply/change_of_status/step2')
        step1 = request.session.get('cos_step1', {})
        if not request.session.get('cos_draft_id'):
            _partner_id = request.session.get('spc_selected_customer_id') or request.env.user.partner_id.id
            existing = request.env['spc.change.of.status'].sudo().search([
                ('partner_id', '=', _partner_id),
                ('state', '=', 'draft'),
            ], order='id desc', limit=1)
            if existing:
                request.session['cos_draft_id'] = existing.id
            else:
                from odoo import fields as odoo_fields
                rec = request.env['spc.change.of.status'].sudo().create({
                    'partner_id': _partner_id,
                    'approved_company_id': request.session.get('spc_selected_company_id'),
                    'state': 'draft', 'current_step': 1,
                    'started_date': odoo_fields.Datetime.now(),
                })
                request.session['cos_draft_id'] = rec.id
        applicants = request.env['res.partner'].sudo().search([
            ('parent_id', '=', request.env.user.partner_id.id)
        ])

        _price_change_of_status = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'change_of_status'),
            ('is_active', '=', True)
        ], limit=1)
        _base_change_of_status = _price_change_of_status.amount if _price_change_of_status else 0.0
        return request.render('spc_portal.template_cos_step1', {
            'step1': step1,
            'applicants': applicants,
            'base_price': _base_change_of_status,
        })

    @http.route('/spc/apply/change_of_status/step2',
                type='http', auth='public', website=True, methods=['GET', 'POST'])
    def cos_step2(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        if request.httprequest.method == 'POST':
            request.session['cos_step2'] = {
                'first_name': kw.get('first_name', ''),
                'last_name': kw.get('last_name', ''),
            }
            return request.redirect('/spc/apply/change_of_status/step3')
        step1 = request.session.get('cos_step1', {})
        step2 = request.session.get('cos_step2', {})
        # Try to prefill from applicant name
        applicant_first = ''
        applicant_last = ''
        applicant_name = step1.get('applicant_name', '')
        if applicant_name:
            parts = applicant_name.split(' ', 1)
            applicant_first = parts[0]
            applicant_last = parts[1] if len(parts) > 1 else ''

        _price_change_of_status = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'change_of_status'),
            ('is_active', '=', True)
        ], limit=1)
        _base_change_of_status = _price_change_of_status.amount if _price_change_of_status else 0.0
        return request.render('spc_portal.template_cos_step2', {
            'step2': step2,
            'applicant_first': applicant_first,
            'applicant_last': applicant_last,
            'base_price': _base_change_of_status,
        })

    @http.route('/spc/apply/change_of_status/step3',
                type='http', auth='public', website=True, methods=['GET', 'POST'])
    def cos_step3(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        if request.httprequest.method == 'POST':
            request.session['cos_step3'] = {
                'declaration_accepted': kw.get('declaration_accepted', 'off') == 'on',
            }
            return request.redirect('/spc/apply/change_of_status/step4')

        _price_change_of_status = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'change_of_status'),
            ('is_active', '=', True)
        ], limit=1)
        _base_change_of_status = _price_change_of_status.amount if _price_change_of_status else 0.0
        return request.render('spc_portal.template_cos_step3', {
            'step3': request.session.get('cos_step3', {}),
            'base_price': _base_change_of_status,
        })

    @http.route('/spc/apply/change_of_status/step4',
                type='http', auth='public', website=True, methods=['GET'])
    def cos_step4(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')

        _price_change_of_status = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'change_of_status'),
            ('is_active', '=', True)
        ], limit=1)
        _base_change_of_status = _price_change_of_status.amount if _price_change_of_status else 0.0
        return request.render('spc_portal.template_cos_step4', {
            'step1': request.session.get('cos_step1', {}),
            'step2': request.session.get('cos_step2', {}),
            'step3': request.session.get('cos_step3', {}),
            'base_price': _base_change_of_status,
        })

    @http.route('/spc/apply/change_of_status/step5',
                type='http', auth='public', website=True, methods=['GET'])
    def cos_step5(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')

        _price_change_of_status = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'change_of_status'),
            ('is_active', '=', True)
        ], limit=1)
        _base_change_of_status = _price_change_of_status.amount if _price_change_of_status else 0.0
        return request.render('spc_portal.template_cos_step5', {'base_price': _base_change_of_status})

    @http.route('/spc/apply/change_of_status/final-submit',
                type='http', auth='public', website=True, methods=['POST'])
    def cos_final_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        from odoo import fields as odoo_fields
        step1 = request.session.get('cos_step1', {})
        step1_files = request.session.get('cos_step1_files', {})
        step2 = request.session.get('cos_step2', {})
        step3 = request.session.get('cos_step3', {})
        _cos_customer_id = request.session.get('spc_selected_customer_id')
        vals = {
            'partner_id': _cos_customer_id or request.env.user.partner_id.id,
            'approved_company_id': request.session.get('spc_selected_company_id'),
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
        draft_id = request.session.pop('cos_draft_id', None)
        if draft_id:
            rec = request.env['spc.change.of.status'].sudo().browse(draft_id)
            if rec.exists():
                rec.write(vals)
                record = rec
            else:
                record = request.env['spc.change.of.status'].sudo().create(vals)
        else:
            record = request.env['spc.change.of.status'].sudo().create(vals)
        for key in ['cos_step1', 'cos_step1_files', 'cos_step2', 'cos_step3']:
            request.session.pop(key, None)
        return request.redirect('/spc/payment/change_of_status/' + str(record.id))

    # ══════════════════════════════════════════════════
    # DEDICATED ACCOUNT MANAGER
    # ══════════════════════════════════════════════════

    @http.route('/spc/apply/dam/save-exit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def dam_save_exit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        step = kw.get('current_step', '1')
        if step == '1':
            request.session['dam_step1'] = {
                'is_existing_stakeholder': kw.get('is_existing_stakeholder', ''),
                'employee_list': kw.get('employee_list', ''),
                'first_name': kw.get('first_name', ''),
                'last_name': kw.get('last_name', ''),
                'contact_number': kw.get('contact_number', ''),
                'email': kw.get('email', ''),
                'designation': kw.get('designation', ''),
                'language_preference': kw.get('language_preference', ''),
            }
        elif step == '2':
            request.session['dam_step2'] = {'number_of_stakeholders': kw.get('number_of_stakeholders', '')}
        elif step == '3':
            request.session['dam_step3'] = {'number_of_years': kw.get('number_of_years', '')}
        request.session.modified = True
        return request.redirect('/spc/concierge-services')

    @http.route('/spc/apply/dam/step1',
                type='http', auth='public', website=True, methods=['GET', 'POST'])
    def dam_step1(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        if request.httprequest.method == 'POST':
            request.session['dam_step1'] = {
                'is_existing_stakeholder': kw.get('is_existing_stakeholder', ''),
                'employee_list': kw.get('employee_list', ''),
                'first_name': kw.get('first_name', ''),
                'last_name': kw.get('last_name', ''),
                'contact_number': kw.get('contact_number', ''),
                'email': kw.get('email', ''),
                'designation': kw.get('designation', ''),
                'language_preference': kw.get('language_preference', ''),
            }
            return request.redirect('/spc/apply/dam/step2')
        if not request.session.get('dam_draft_id'):
            _partner_id = request.env.user.partner_id.id
            existing = request.env['spc.dedicated.account.manager'].sudo().search([
                ('partner_id', '=', _partner_id),
                ('state', '=', 'draft'),
            ], order='id desc', limit=1)
            if existing:
                request.session['dam_draft_id'] = existing.id
            else:
                from odoo import fields as odoo_fields
                rec = request.env['spc.dedicated.account.manager'].sudo().create({
                    'partner_id': _partner_id,
                    'approved_company_id': request.session.get('spc_selected_company_id'),
                    'state': 'draft', 'current_step': 1,
                    'started_date': odoo_fields.Datetime.now(),
                })
                request.session['dam_draft_id'] = rec.id

        _dam_price = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'dedicated_account_manager'),
            ('is_active', '=', True)
        ], limit=1)
        _dam_base = _dam_price.amount if _dam_price else 0.0
        return request.render('spc_portal.template_dam_step1', {
            'step1': request.session.get('dam_step1', {}),
            'base_price': _dam_base,
        })

    @http.route('/spc/apply/dam/step2',
                type='http', auth='public', website=True, methods=['GET', 'POST'])
    def dam_step2(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        if request.httprequest.method == 'POST':
            request.session['dam_step2'] = {
                'number_of_stakeholders': kw.get('number_of_stakeholders', ''),
            }
            return request.redirect('/spc/apply/dam/step3')

        _dam_price = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'dedicated_account_manager'),
            ('is_active', '=', True)
        ], limit=1)
        _dam_base = _dam_price.amount if _dam_price else 0.0
        return request.render('spc_portal.template_dam_step2', {
            'step2': request.session.get('dam_step2', {}),
            'base_price': _dam_base,
        })

    @http.route('/spc/apply/dam/step3',
                type='http', auth='public', website=True, methods=['GET', 'POST'])
    def dam_step3(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        if request.httprequest.method == 'POST':
            request.session['dam_step3'] = {
                'number_of_years': kw.get('number_of_years', ''),
            }
            return request.redirect('/spc/apply/dam/step4')

        _dam_price = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'dedicated_account_manager'),
            ('is_active', '=', True)
        ], limit=1)
        _dam_base = _dam_price.amount if _dam_price else 0.0
        return request.render('spc_portal.template_dam_step3', {
            'step3': request.session.get('dam_step3', {}),
            'base_price': _dam_base,
        })

    @http.route('/spc/apply/dam/step4',
                type='http', auth='public', website=True, methods=['GET'])
    def dam_step4(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')

        _dam_price = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'dedicated_account_manager'),
            ('is_active', '=', True)
        ], limit=1)
        _dam_base = _dam_price.amount if _dam_price else 0.0
        return request.render('spc_portal.template_dam_step4', {
            'step1': request.session.get('dam_step1', {}),
            'step2': request.session.get('dam_step2', {}),
            'step3': request.session.get('dam_step3', {}),
            'base_price': _dam_base,
        })

    @http.route('/spc/apply/dam/step5',
                type='http', auth='public', website=True, methods=['GET'])
    def dam_step5(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')

        _dam_price = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'dedicated_account_manager'),
            ('is_active', '=', True)
        ], limit=1)
        _dam_base = _dam_price.amount if _dam_price else 0.0
        return request.render('spc_portal.template_dam_step5', {'base_price': _dam_base})

    @http.route('/spc/apply/dam/final-submit',
                type='http', auth='public', website=True, methods=['POST'])
    def dam_final_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        from odoo import fields as odoo_fields
        step1 = request.session.get('dam_step1', {})
        step2 = request.session.get('dam_step2', {})
        step3 = request.session.get('dam_step3', {})
        vals = {
            'partner_id': request.env.user.partner_id.id,
            'approved_company_id': request.session.get('spc_selected_company_id'),
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
        draft_id = request.session.pop('dam_draft_id', None)
        if draft_id:
            rec = request.env['spc.dedicated.account.manager'].sudo().browse(draft_id)
            if rec.exists():
                rec.write(vals)
                record = rec
            else:
                record = request.env['spc.dedicated.account.manager'].sudo().create(vals)
        else:
            record = request.env['spc.dedicated.account.manager'].sudo().create(vals)
        for key in ['dam_step1', 'dam_step2', 'dam_step3']:
            request.session.pop(key, None)
        return request.redirect('/spc/payment/dedicated_account_manager/' + str(record.id))

    @http.route('/spc/concierge-services/service/account_manager',
                type='http', auth='public', website=True)
    def dam_service_detail(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_dam_service_detail', {})


    # ═══════════════════════════════════════════════
    #  EID REPLACEMENT ROUTES
    def _eid_save_attachments(self, record, field_name, files_list):
        """Save multiple uploaded files as ir.attachment and link to record Many2many field."""
        if not files_list:
            return
        attachment_ids = []
        for f in files_list:
            if f and hasattr(f, 'read') and f.filename:
                file_data = f.read()
                if file_data:
                    import base64 as b64
                    att = request.env['ir.attachment'].sudo().create({
                        'name': f.filename,
                        'datas': b64.b64encode(file_data).decode('utf-8'),
                        'res_model': 'spc.eid.replacement',
                        'res_id': record.id,
                        'type': 'binary',
                    })
                    attachment_ids.append(att.id)
        if attachment_ids:
            field = getattr(record, field_name)
            record.sudo().write({field_name: [(4, aid) for aid in attachment_ids]})


    # ═══════════════════════════════════════════════

    @http.route('/spc/concierge/eid-replacement', type='http', auth='user', website=True)
    def eid_replacement_detail(self, **kwargs):
        return request.render('spc_portal.eid_replacement_detail', {})

    @http.route('/spc/apply/eid_replacement/step1', type='http', auth='user', website=True)
    def eid_replacement_step1(self, **kwargs):
        return request.render('spc_portal.eid_replacement_step1', {})

    @http.route('/spc/apply/eid_replacement/step1/submit', type='http', auth='user', website=True, methods=['POST'])
    def eid_replacement_step1_submit(self, **kwargs):
        visa_type = kwargs.get('visa_type', '')
        if not visa_type:
            return request.redirect('/spc/apply/eid_replacement/step1')
        partner = request.env.user.partner_id
        record = request.env['spc.eid.replacement'].sudo().create({
            'partner_id': partner.id,
            'approved_company_id': request.session.get('spc_selected_company_id'),
            'started_date': __import__('odoo').fields.Datetime.now(),
            'visa_type': visa_type,
            'state': 'draft',
        })
        return request.redirect('/spc/apply/eid_replacement/step2/%d' % record.id)

    @http.route('/spc/apply/eid_replacement/step2/<int:record_id>', type='http', auth='user', website=True)
    def eid_replacement_step2(self, record_id, **kwargs):
        record = request.env['spc.eid.replacement'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/apply/eid_replacement/step1')
        countries = request.env['res.country'].sudo().search([], order='name asc')
        return request.render('spc_portal.eid_replacement_step2', {'record': record, 'countries': countries})

    @http.route('/spc/apply/eid_replacement/step2/submit', type='http', auth='user', website=True, methods=['POST'])
    def eid_replacement_step2_submit(self, **kwargs):
        record_id = int(kwargs.get('record_id', 0))
        record = request.env['spc.eid.replacement'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/apply/eid_replacement/step1')
        def _int(v):
            try: return int(v)
            except: return 0
        vals = {
            'gender': kwargs.get('gender', ''),
            'first_name': kwargs.get('first_name', ''),
            'last_name': kwargs.get('last_name', ''),
            'father_name': kwargs.get('father_name', ''),
            'mother_name': kwargs.get('mother_name', ''),
            'phone_code': kwargs.get('phone_code', '+971'),
            'phone': kwargs.get('phone', ''),
            'applicant_email': kwargs.get('applicant_email', ''),
            'address': kwargs.get('address', ''),
            'city': kwargs.get('city', ''),
            'country_id': _int(kwargs.get('country_id', 0)),
            'birth_country_id': _int(kwargs.get('birth_country_id', 0)),
            'nationality_id': _int(kwargs.get('nationality_id', 0)),
            'prev_nationality_id': _int(kwargs.get('prev_nationality_id', 0)),
            'marital_status': kwargs.get('marital_status', ''),
            'religion': kwargs.get('religion', ''),
            'designation': kwargs.get('designation', ''),
            'designation_unavailable': kwargs.get('designation_unavailable', '0') == '1',
            'highest_qualification': kwargs.get('highest_qualification', ''),
            'has_dependents': kwargs.get('has_dependents', 'no'),
            'dependent_spouse': bool(kwargs.get('dependent_spouse')),
            'dependent_children': bool(kwargs.get('dependent_children')),
            'dependent_domestic': bool(kwargs.get('dependent_domestic')),
            'num_dependents': _int(kwargs.get('num_dependents', 0)),
            'dob': kwargs.get('dob') or False,
        }
        record.sudo().write(vals)
        # Save multiple file attachments (up to 5 per field)
        files = request.httprequest.files
        field_map = {
            'doc_photo': 'doc_photo_ids',
            'doc_evisa': 'doc_evisa_ids',
            'doc_change_status': 'doc_change_status_ids',
            'doc_medical': 'doc_medical_ids',
            'doc_emp_contract_copy': 'doc_emp_contract_copy_ids',
            'doc_eid_copy': 'doc_eid_copy_ids',
            'doc_attested_degree': 'doc_attested_degree_ids',
        }
        for form_field, model_field in field_map.items():
            uploaded = files.getlist(form_field)
            self._eid_save_attachments(record, model_field, uploaded[:5])
        return request.redirect('/spc/apply/eid_replacement/step3/%d' % record.id)

    @http.route('/spc/apply/eid_replacement/step3/<int:record_id>', type='http', auth='user', website=True)
    def eid_replacement_step3(self, record_id, **kwargs):
        record = request.env['spc.eid.replacement'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/apply/eid_replacement/step1')
        return request.render('spc_portal.eid_replacement_step3', {'record': record})

    @http.route('/spc/apply/eid_replacement/step3/submit', type='http', auth='user', website=True, methods=['POST'])
    def eid_replacement_step3_submit(self, **kwargs):
        record_id = int(kwargs.get('record_id', 0))
        record = request.env['spc.eid.replacement'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/apply/eid_replacement/step1')
        record.sudo().write({
            'prev_residence_visa': kwargs.get('prev_residence_visa', ''),
            'eid_number': kwargs.get('eid_number', ''),
            'eid_expiry': kwargs.get('eid_expiry') or False,
            'biometric_mobile': kwargs.get('biometric_mobile', ''),
            'biometric_center': kwargs.get('biometric_center', ''),
            'has_uae_pobox': kwargs.get('has_uae_pobox', ''),
            'pobox_location': kwargs.get('pobox_location', ''),
            'pobox_number': kwargs.get('pobox_number', ''),
            'deliver_physical_eid': kwargs.get('deliver_physical_eid', ''),
            'delivery_city': kwargs.get('delivery_city', ''),
            'delivery_landmark': kwargs.get('delivery_landmark', ''),
            'delivery_address': kwargs.get('delivery_address', ''),
            'delivery_country': kwargs.get('delivery_country', 'United Arab Emirates'),
            'delivery_phone': kwargs.get('delivery_phone', ''),
        })
        files = request.httprequest.files
        self._eid_save_attachments(record, 'doc_eid_front_ids', files.getlist('doc_eid_front')[:5])
        self._eid_save_attachments(record, 'doc_eid_back_ids', files.getlist('doc_eid_back')[:5])
        if record.visa_type == 'employee':
            return request.redirect('/spc/apply/eid_replacement/step4/%d' % record.id)
        else:
            return request.redirect('/spc/apply/eid_replacement/declaration/%d' % record.id)

    @http.route('/spc/apply/eid_replacement/step4/<int:record_id>', type='http', auth='user', website=True)
    def eid_replacement_step4(self, record_id, **kwargs):
        record = request.env['spc.eid.replacement'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/apply/eid_replacement/step1')
        return request.render('spc_portal.eid_replacement_step4', {'record': record})

    @http.route('/spc/apply/eid_replacement/step4/submit', type='http', auth='user', website=True, methods=['POST'])
    def eid_replacement_step4_submit(self, **kwargs):
        def _float(v):
            try: return float(v)
            except: return 0.0
        record_id = int(kwargs.get('record_id', 0))
        record = request.env['spc.eid.replacement'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/apply/eid_replacement/step1')
        record.sudo().write({
            'contract_type': kwargs.get('contract_type', ''),
            'probation_period': kwargs.get('probation_period', ''),
            'notice_period': kwargs.get('notice_period', ''),
            'salary_basic': _float(kwargs.get('salary_basic')),
            'salary_accommodation': _float(kwargs.get('salary_accommodation')),
            'salary_transport': _float(kwargs.get('salary_transport')),
            'salary_other': _float(kwargs.get('salary_other')),
            'salary_total': _float(kwargs.get('salary_total')),
            'contract_execution': kwargs.get('contract_execution') or False,
            'contract_position': kwargs.get('contract_position', ''),
            'contract_salary': _float(kwargs.get('salary_basic')),
            'contract_start': kwargs.get('contract_start') or False,
            'contract_end': kwargs.get('contract_end') or False,
        })
        files = request.httprequest.files
        self._eid_save_attachments(record, 'doc_contract_ids', files.getlist('doc_contract')[:5])
        return request.redirect('/spc/apply/eid_replacement/declaration/%d' % record.id)

    @http.route('/spc/apply/eid_replacement/declaration/<int:record_id>', type='http', auth='user', website=True)
    def eid_replacement_declaration(self, record_id, **kwargs):
        record = request.env['spc.eid.replacement'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/apply/eid_replacement/step1')
        return request.render('spc_portal.eid_replacement_declaration', {'record': record})

    @http.route('/spc/apply/eid_replacement/declaration/submit', type='http', auth='user', website=True, methods=['POST'])
    def eid_replacement_declaration_submit(self, **kwargs):
        record_id = int(kwargs.get('record_id', 0))
        record = request.env['spc.eid.replacement'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/apply/eid_replacement/step1')
        record.sudo().write({
            'declaration_accepted': bool(kwargs.get('declaration_accepted'))
        })
        return request.redirect('/spc/apply/eid_replacement/review/%d' % record.id)

    @http.route('/spc/apply/eid_replacement/review/<int:record_id>', type='http', auth='user', website=True)
    def eid_replacement_review(self, record_id, **kwargs):
        record = request.env['spc.eid.replacement'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/apply/eid_replacement/step1')
        return request.render('spc_portal.eid_replacement_review', {'record': record})

    @http.route('/spc/apply/eid_replacement/review/submit', type='http', auth='user', website=True, methods=['POST'])
    def eid_replacement_review_submit(self, **kwargs):
        record_id = int(kwargs.get('record_id', 0))
        record = request.env['spc.eid.replacement'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/apply/eid_replacement/step1')
        return request.redirect('/spc/apply/eid_replacement/payment/%d' % record.id)

    @http.route('/spc/apply/eid_replacement/payment/<int:record_id>', type='http', auth='user', website=True)
    def eid_replacement_payment(self, record_id, **kwargs):
        record = request.env['spc.eid.replacement'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/apply/eid_replacement/step1')
        return request.redirect('/spc/payment/eid_replacement/' + str(record_id))

    @http.route('/spc/apply/eid_replacement/payment/submit', type='http', auth='user', website=True, methods=['POST'])
    def eid_replacement_payment_submit(self, **kwargs):
        record_id = int(kwargs.get('record_id', 0))
        record = request.env['spc.eid.replacement'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/apply/eid_replacement/step1')
        record.sudo().write({
            'state': 'submitted',
            'payment_status': 'paid',
                'fee': float(kwargs.get('amount', 0)) or 0.0,
        })
        return request.redirect('/spc/payment/eid_replacement/' + str(record.id))


    # ═══════════════════════════════════════════════
    #  RE-ENTRY PERMIT ROUTES
    # ═══════════════════════════════════════════════

    @http.route('/spc/concierge/reentry-permit', type='http', auth='user', website=True)
    def reentry_permit_detail(self, **kwargs):
        return request.render('spc_portal.reentry_permit_detail', {})

    @http.route('/spc/apply/reentry_permit/step1', type='http', auth='user', website=True)
    def reentry_permit_step1(self, **kwargs):
        employees = []
        try:
            partner = request.env.user.partner_id
            emp_list = request.env['spc.employee.list'].sudo().search([('partner_id','=',partner.id)], limit=1)
            if emp_list and emp_list.employee_ids:
                for e in emp_list.employee_ids:
                    employees.append({
                        'name': (e.first_name or '') + ' ' + (e.last_name or ''),
                        'first_name': e.first_name or '',
                        'last_name': e.last_name or '',
                        'email': e.email or '',
                        'mobile': e.mobile or '',
                    })
        except Exception:
            pass
        return request.render('spc_portal.reentry_permit_step1', {'employees': employees})

    @http.route('/spc/apply/reentry_permit/step1/submit', type='http', auth='user', website=True, methods=['POST'])
    def reentry_permit_step1_submit(self, **kwargs):
        import base64 as b64
        partner = request.env.user.partner_id
        record = request.env['spc.reentry.permit'].sudo().create({
            'partner_id': partner.id,
            'approved_company_id': request.session.get('spc_selected_company_id'),
            'started_date': __import__('odoo').fields.Datetime.now(),
            'applicant_name': kwargs.get('applicant_name',''),
            'first_name': kwargs.get('first_name',''),
            'last_name': kwargs.get('last_name',''),
            'phone_code': kwargs.get('phone_code','+971'),
            'mobile': kwargs.get('mobile',''),
            'email': kwargs.get('email',''),
            'passport_number': kwargs.get('passport_number',''),
            'designation': kwargs.get('designation',''),
            'visa_type': kwargs.get('visa_type',''),
            'reason_outside_uae': kwargs.get('reason_outside_uae',''),
            'months_outside_uae': kwargs.get('months_outside_uae',''),
            'visa_issue_date': kwargs.get('visa_issue_date') or False,
            'visa_expiry_date': kwargs.get('visa_expiry_date') or False,
            'state': 'draft',
        })
        files = request.httprequest.files
        for fname, fmodel in [('doc_passport','doc_passport_ids'),('doc_visa','doc_visa_ids'),('doc_proof','doc_proof_ids')]:
            uploaded = files.getlist(fname)
            for f in uploaded[:5]:
                if f and f.filename:
                    fdata = f.read()
                    if fdata:
                        att = request.env['ir.attachment'].sudo().create({
                            'name': f.filename,
                            'datas': b64.b64encode(fdata).decode('utf-8'),
                            'res_model': 'spc.reentry.permit',
                            'res_id': record.id,
                            'type': 'binary',
                        })
                        record.sudo().write({fmodel: [(4, att.id)]})
        return request.redirect('/spc/apply/reentry_permit/declaration/%d' % record.id)

    @http.route('/spc/apply/reentry_permit/declaration/<int:record_id>', type='http', auth='user', website=True)
    def reentry_permit_declaration(self, record_id, **kwargs):
        record = request.env['spc.reentry.permit'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/apply/reentry_permit/step1')
        return request.render('spc_portal.reentry_permit_declaration', {'record': record})

    @http.route('/spc/apply/reentry_permit/declaration/submit', type='http', auth='user', website=True, methods=['POST'])
    def reentry_permit_declaration_submit(self, **kwargs):
        record_id = int(kwargs.get('record_id', 0))
        record = request.env['spc.reentry.permit'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/apply/reentry_permit/step1')
        record.sudo().write({'declaration_accepted': bool(kwargs.get('declaration_accepted'))})
        return request.redirect('/spc/apply/reentry_permit/review/%d' % record.id)

    @http.route('/spc/apply/reentry_permit/review/<int:record_id>', type='http', auth='user', website=True)
    def reentry_permit_review(self, record_id, **kwargs):
        record = request.env['spc.reentry.permit'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/apply/reentry_permit/step1')
        return request.render('spc_portal.reentry_permit_review', {'record': record})

    @http.route('/spc/apply/reentry_permit/review/submit', type='http', auth='user', website=True, methods=['POST'])
    def reentry_permit_review_submit(self, **kwargs):
        record_id = int(kwargs.get('record_id', 0))
        record = request.env['spc.reentry.permit'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/apply/reentry_permit/step1')
        return request.redirect('/spc/apply/reentry_permit/payment/%d' % record.id)

    @http.route('/spc/apply/reentry_permit/payment/<int:record_id>', type='http', auth='user', website=True)
    def reentry_permit_payment(self, record_id, **kwargs):
        record = request.env['spc.reentry.permit'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/apply/reentry_permit/step1')
        return request.render('spc_portal.reentry_permit_payment', {'record': record})

    @http.route('/spc/apply/reentry_permit/payment/submit', type='http', auth='user', website=True, methods=['POST'])
    def reentry_permit_payment_submit(self, **kwargs):
        record_id = int(kwargs.get('record_id', 0))
        record = request.env['spc.reentry.permit'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/apply/reentry_permit/step1')
        record.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
        return request.redirect('/spc/payment/reentry_permit/' + str(record.id))

    # ═══════════════════════════════════════════════
    #  LEASE DOCUMENT ROUTES
    # ═══════════════════════════════════════════════

    @http.route('/spc/concierge/lease-document', type='http', auth='user', website=True)
    def lease_document_detail(self, **kwargs):
        lease_type = kwargs.get('type', 'new')
        titles = {'new': 'Lease Documents', 'cancel': 'ERP Lease document - Cancel'}
        return request.render('spc_portal.lease_document_detail', {
            'lease_type': lease_type,
            'lease_title': titles.get(lease_type, 'Lease Documents'),
        })

    @http.route('/spc/apply/lease_document/step1', type='http', auth='user', website=True)
    def lease_document_step1(self, **kwargs):
        lease_type = kwargs.get('type', 'new')
        countries = request.env['res.country'].sudo().search([], order='name asc')
        return request.render('spc_portal.lease_document_step1', {
            'lease_type': lease_type,
            'countries': countries,
        })

    @http.route('/spc/apply/lease_document/step1/<int:record_id>', type='http', auth='user', website=True)
    def lease_document_step1_edit(self, record_id, **kwargs):
        record = request.env['spc.lease.document'].sudo().browse(record_id)
        countries = request.env['res.country'].sudo().search([], order='name asc')
        return request.render('spc_portal.lease_document_step1', {
            'lease_type': record.lease_type if record.exists() else 'new',
            'countries': countries,
        })

    @http.route('/spc/apply/lease_document/step1/submit', type='http', auth='user', website=True, methods=['POST'])
    def lease_document_step1_submit(self, **kwargs):
        def _float(v):
            try: return float(v)
            except: return 0.0
        def _int(v):
            try: return int(v)
            except: return 0
        partner = request.env.user.partner_id
        record = request.env['spc.lease.document'].sudo().create({
            'partner_id': partner.id,
            'approved_company_id': request.session.get('spc_selected_company_id'),
            'started_date': __import__('odoo').fields.Datetime.now(),
            'lease_type': kwargs.get('lease_type', 'new'),
            'company_name': kwargs.get('company_name', ''),
            'manager_first_name': kwargs.get('manager_first_name', ''),
            'manager_last_name': kwargs.get('manager_last_name', ''),
            'full_name_arabic': kwargs.get('full_name_arabic', ''),
            'nationality_id': _int(kwargs.get('nationality_id', 0)),
            'passport_number': kwargs.get('passport_number', ''),
            'description_en': kwargs.get('description_en', ''),
            'address_en': kwargs.get('address_en', ''),
            'lease_validity': kwargs.get('lease_validity', ''),
            'annual_rent': _float(kwargs.get('annual_rent', 0)),
            'commencement_date': kwargs.get('commencement_date') or False,
            'lease_expiry_date': kwargs.get('lease_expiry_date') or False,
            'facility_type': kwargs.get('facility_type', ''),
            'additional_lease': kwargs.get('additional_lease', 'no'),
            'additional_desc_en': kwargs.get('additional_desc_en', ''),
            'additional_address_en': kwargs.get('additional_address_en', ''),
            'additional_annual_rent': _float(kwargs.get('additional_annual_rent', 0)),
            'state': 'draft',
        })
        return request.redirect('/spc/apply/lease_document/declaration/%d' % record.id)

    @http.route('/spc/apply/lease_document/declaration/<int:record_id>', type='http', auth='user', website=True)
    def lease_document_declaration(self, record_id, **kwargs):
        record = request.env['spc.lease.document'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/concierge-services')
        return request.render('spc_portal.lease_document_declaration', {'record': record})

    @http.route('/spc/apply/lease_document/declaration/submit', type='http', auth='user', website=True, methods=['POST'])
    def lease_document_declaration_submit(self, **kwargs):
        record_id = int(kwargs.get('record_id', 0))
        record = request.env['spc.lease.document'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/concierge-services')
        record.sudo().write({'declaration_accepted': bool(kwargs.get('declaration_accepted'))})
        return request.redirect('/spc/apply/lease_document/review/%d' % record.id)

    @http.route('/spc/apply/lease_document/review/<int:record_id>', type='http', auth='user', website=True)
    def lease_document_review(self, record_id, **kwargs):
        record = request.env['spc.lease.document'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/concierge-services')
        return request.render('spc_portal.lease_document_review', {'record': record})

    @http.route('/spc/apply/lease_document/review/submit', type='http', auth='user', website=True, methods=['POST'])
    def lease_document_review_submit(self, **kwargs):
        record_id = int(kwargs.get('record_id', 0))
        record = request.env['spc.lease.document'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/concierge-services')
        return request.redirect('/spc/apply/lease_document/payment/%d' % record.id)

    @http.route('/spc/apply/lease_document/payment/<int:record_id>', type='http', auth='user', website=True)
    def lease_document_payment(self, record_id, **kwargs):
        record = request.env['spc.lease.document'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/concierge-services')
        return request.render('spc_portal.lease_document_payment', {'record': record})

    @http.route('/spc/apply/lease_document/payment/submit', type='http', auth='user', website=True, methods=['POST'])
    def lease_document_payment_submit(self, **kwargs):
        record_id = int(kwargs.get('record_id', 0))
        record = request.env['spc.lease.document'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/concierge-services')
        record.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
        return request.redirect('/spc/payment/lease_document/' + str(record.id))

    # MEDICAL ROUTES
    @http.route('/spc/concierge/medical', type='http', auth='user', website=True)
    def medical_detail(self, **kwargs):
        medical_type = kwargs.get('type', 'new_residency')
        titles = {'new_residency': 'Medical for New Residency', 'renewal': 'Medical for Residency Renewal'}
        tags = {'new_residency': 'New', 'renewal': 'Renew'}
        return request.render('spc_portal.medical_detail', {
            'medical_type': medical_type,
            'medical_title': titles.get(medical_type, 'Medical'),
            'medical_tag': tags.get(medical_type, 'New'),
        })

    @http.route('/spc/apply/medical/step1', type='http', auth='user', website=True)
    def medical_step1(self, **kwargs):
        medical_type = kwargs.get('type', 'new_residency')
        titles = {'new_residency': 'Medical for New Residency', 'renewal': 'Medical for Residency Renewal'}
        employees = []
        try:
            partner = request.env.user.partner_id
            emp_list = request.env['spc.employee.list'].sudo().search([('partner_id','=',partner.id)], limit=1)
            if emp_list and emp_list.employee_ids:
                for e in emp_list.employee_ids:
                    employees.append({'name': (e.first_name or '') + ' ' + (e.last_name or '')})
        except Exception:
            pass

        _med_type = medical_type if 'medical_type' in dir() else 'new_residency'
        _med_stype = 'medical_new' if _med_type == 'new_residency' else 'medical_renewal'
        _med_price = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', _med_stype),
            ('is_active', '=', True)
        ], limit=1)
        _med_base = _med_price.amount if _med_price else 0.0
        return request.render('spc_portal.medical_step1', {
            'medical_type': medical_type,
            'medical_title': titles.get(medical_type, 'Medical'),
            'employees': employees,
            'base_price': _med_base,
        })

    @http.route('/spc/apply/medical/step1/<int:record_id>', type='http', auth='user', website=True)
    def medical_step1_edit(self, record_id, **kwargs):
        titles = {'new_residency': 'Medical for New Residency', 'renewal': 'Medical for Residency Renewal'}
        record = request.env['spc.medical'].sudo().browse(record_id)
        mt = record.medical_type if record.exists() else 'new_residency'
        return request.render('spc_portal.medical_step1', {
            'medical_type': mt, 'medical_title': titles.get(mt, 'Medical'), 'employees': [],
        })

    @http.route('/spc/apply/medical/step1/submit', type='http', auth='user', website=True, methods=['POST'])
    def medical_step1_submit(self, **kwargs):
        import base64 as b64
        partner = request.env.user.partner_id
        record = request.env['spc.medical'].sudo().create({
            'partner_id': partner.id,
            'approved_company_id': request.session.get('spc_selected_company_id'),
            'started_date': __import__('odoo').fields.Datetime.now(),
            'medical_type': kwargs.get('medical_type', 'new_residency'),
            'applicant_name': kwargs.get('applicant_name', ''),
            'visa_type': kwargs.get('visa_type', ''),
            'service_type': kwargs.get('service_type', ''),
            'first_name': kwargs.get('first_name', ''),
            'last_name': kwargs.get('last_name', ''),
            'mother_name': kwargs.get('mother_name', ''),
            'email': kwargs.get('email', ''),
            'phone_code': kwargs.get('phone_code', '+971'),
            'mobile': kwargs.get('mobile', ''),
            'dob': kwargs.get('dob') or False,
            'marital_status': kwargs.get('marital_status', ''),
            'religion': kwargs.get('religion', ''),
            'amount': 2000.0 if kwargs.get('service_type') == 'vip' else 700.0,
            'state': 'draft',
        })
        files = request.httprequest.files
        for fname, fmodel in [('doc_passport','doc_passport_ids'),('doc_special','doc_special_ids'),
                               ('doc_entry_visa','doc_entry_visa_ids'),('doc_photo','doc_photo_ids')]:
            for f in files.getlist(fname)[:5]:
                if f and f.filename:
                    fdata = f.read()
                    if fdata:
                        att = request.env['ir.attachment'].sudo().create({
                            'name': f.filename, 'datas': b64.b64encode(fdata).decode(),
                            'res_model': 'spc.medical', 'res_id': record.id, 'type': 'binary',
                        })
                        record.sudo().write({fmodel: [(4, att.id)]})
        return request.redirect('/spc/apply/medical/declaration/%d' % record.id)

    @http.route('/spc/apply/medical/declaration/<int:record_id>', type='http', auth='user', website=True)
    def medical_declaration(self, record_id, **kwargs):
        record = request.env['spc.medical'].sudo().browse(record_id)

        _med_type = record.medical_type if record.exists() else 'new_residency'
        _med_stype = 'medical_new' if _med_type == 'new_residency' else 'medical_renewal'
        _med_price = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', _med_stype),
            ('is_active', '=', True)
        ], limit=1)
        _med_base = _med_price.amount if _med_price else 0.0
        return request.render('spc_portal.medical_declaration', {'record': record, 'base_price': _med_base}) if record.exists() else request.redirect('/spc/concierge-services')

    @http.route('/spc/apply/medical/declaration/submit', type='http', auth='user', website=True, methods=['POST'])
    def medical_declaration_submit(self, **kwargs):
        record = request.env['spc.medical'].sudo().browse(int(kwargs.get('record_id', 0)))
        if not record.exists(): return request.redirect('/spc/concierge-services')
        record.sudo().write({'declaration_accepted': bool(kwargs.get('declaration_accepted'))})
        return request.redirect('/spc/apply/medical/review/%d' % record.id)

    @http.route('/spc/apply/medical/review/<int:record_id>', type='http', auth='user', website=True)
    def medical_review(self, record_id, **kwargs):
        record = request.env['spc.medical'].sudo().browse(record_id)

        _med_type = record.medical_type if record.exists() else 'new_residency'
        _med_stype = 'medical_new' if _med_type == 'new_residency' else 'medical_renewal'
        _med_price = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', _med_stype),
            ('is_active', '=', True)
        ], limit=1)
        _med_base = _med_price.amount if _med_price else 0.0
        return request.render('spc_portal.medical_review', {'record': record, 'base_price': _med_base}) if record.exists() else request.redirect('/spc/concierge-services')

    @http.route('/spc/apply/medical/review/submit', type='http', auth='user', website=True, methods=['POST'])
    def medical_review_submit(self, **kwargs):
        record = request.env['spc.medical'].sudo().browse(int(kwargs.get('record_id', 0)))
        if not record.exists(): return request.redirect('/spc/concierge-services')
        return request.redirect('/spc/apply/medical/payment/%d' % record.id)

    @http.route('/spc/apply/medical/payment/<int:record_id>', type='http', auth='user', website=True)
    def medical_payment(self, record_id, **kwargs):
        record = request.env['spc.medical'].sudo().browse(record_id)
        return request.render('spc_portal.medical_payment', {'record': record}) if record.exists() else request.redirect('/spc/concierge-services')

    @http.route('/spc/apply/medical/payment/submit', type='http', auth='user', website=True, methods=['POST'])
    def medical_payment_submit(self, **kwargs):
        record = request.env['spc.medical'].sudo().browse(int(kwargs.get('record_id', 0)))
        if not record.exists(): return request.redirect('/spc/concierge-services')
        record.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
        return request.redirect('/spc/payment/medical_new/' + str(record.id))

    # MEETING ROOM ROUTES
    @http.route('/spc/concierge/meeting-room', type='http', auth='user', website=True)
    def meeting_room_detail(self, **kwargs):
        return request.render('spc_portal.meeting_room_detail', {})

    @http.route('/spc/apply/meeting_room/step1', type='http', auth='user', website=True)
    def meeting_room_step1(self, **kwargs):
        _mr_price = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'meeting_room'),
            ('is_active', '=', True)
        ], limit=1)
        _mr_base = _mr_price.amount if _mr_price else 0.0
        return request.render('spc_portal.meeting_room_step1_v2', {'base_price': _mr_base})

    @http.route('/spc/apply/meeting_room/step1/<int:record_id>', type='http', auth='user', website=True)
    def meeting_room_step1_edit(self, record_id, **kwargs):
        _mr_price = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'meeting_room'),
            ('is_active', '=', True)
        ], limit=1)
        _mr_base = _mr_price.amount if _mr_price else 0.0
        return request.render('spc_portal.meeting_room_step1_v2', {'base_price': _mr_base})

    @http.route('/spc/apply/meeting_room/step1/submit', type='http', auth='user', website=True, methods=['POST'])
    def meeting_room_step1_submit(self, **kwargs):
        partner = request.env.user.partner_id
        record = request.env['spc.meeting.room'].sudo().create({
            'partner_id': partner.id,
            'approved_company_id': request.session.get('spc_selected_company_id'),
            'started_date': __import__('odoo').fields.Datetime.now(),
            'booking_date': kwargs.get('booking_date') or False,
            'booking_start_time': kwargs.get('booking_start_time', ''),
            'meeting_duration': kwargs.get('meeting_duration', ''),
            'comments': kwargs.get('comments', ''),
            'state': 'draft',
        })
        return request.redirect('/spc/apply/meeting_room/review/%d' % record.id)

    @http.route('/spc/apply/meeting_room/review/<int:record_id>', type='http', auth='user', website=True)
    def meeting_room_review(self, record_id, **kwargs):
        record = request.env['spc.meeting.room'].sudo().browse(record_id)

        _mr_price = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'meeting_room'),
            ('is_active', '=', True)
        ], limit=1)
        _mr_base = _mr_price.amount if _mr_price else 0.0
        return request.render('spc_portal.meeting_room_review', {'record': record, 'base_price': _mr_base}) if record.exists() else request.redirect('/spc/concierge-services')

    @http.route('/spc/apply/meeting_room/review/submit', type='http', auth='user', website=True, methods=['POST'])
    def meeting_room_review_submit(self, **kwargs):
        record = request.env['spc.meeting.room'].sudo().browse(int(kwargs.get('record_id', 0)))
        if not record.exists(): return request.redirect('/spc/concierge-services')
        return request.redirect('/spc/apply/meeting_room/payment/%d' % record.id)

    @http.route('/spc/apply/meeting_room/payment/<int:record_id>', type='http', auth='user', website=True)
    def meeting_room_payment(self, record_id, **kwargs):
        record = request.env['spc.meeting.room'].sudo().browse(record_id)
        return request.render('spc_portal.meeting_room_payment', {'record': record}) if record.exists() else request.redirect('/spc/concierge-services')

    @http.route('/spc/apply/meeting_room/payment/submit', type='http', auth='user', website=True, methods=['POST'])
    def meeting_room_payment_submit(self, **kwargs):
        record = request.env['spc.meeting.room'].sudo().browse(int(kwargs.get('record_id', 0)))
        if not record.exists(): return request.redirect('/spc/concierge-services')
        record.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
        return request.redirect('/spc/payment/meeting_room/' + str(record.id))

    # MOFA ROUTES
    @http.route('/spc/concierge/mofa-attestation', type='http', auth='user', website=True)
    def mofa_detail(self, **kwargs):
        return request.render('spc_portal.mofa_detail', {})

    @http.route('/spc/apply/mofa/step1', type='http', auth='user', website=True)
    def mofa_step1(self, **kwargs):
        countries = request.env['res.country'].sudo().search([], order='name asc')

        _price_mofa = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'mofa'),
            ('is_active', '=', True)
        ], limit=1)
        _base_mofa = _price_mofa.amount if _price_mofa else 0.0
        return request.render('spc_portal.mofa_step1', {'countries': countries, 'base_price': _base_mofa})

    @http.route('/spc/apply/mofa/step1/<int:record_id>', type='http', auth='user', website=True)
    def mofa_step1_edit(self, record_id, **kwargs):
        countries = request.env['res.country'].sudo().search([], order='name asc')
        return request.render('spc_portal.mofa_step1', {'countries': countries})

    @http.route('/spc/apply/mofa/step1/submit', type='http', auth='user', website=True, methods=['POST'])
    def mofa_step1_submit(self, **kwargs):
        import base64 as b64
        def _int(v):
            try: return int(v)
            except: return 0
        partner = request.env.user.partner_id
        ind_count = _int(kwargs.get('individual_doc_count', 0))
        com_count = _int(kwargs.get('commercial_doc_count', 0))
        inv_count = _int(kwargs.get('invoice_doc_count', 0))
        record = request.env['spc.mofa'].sudo().create({
            'partner_id': partner.id,
            'approved_company_id': request.session.get('spc_selected_company_id'),
            'started_date': __import__('odoo').fields.Datetime.now(),
            'doc_type_individual': kwargs.get('doc_type_individual') == '1',
            'doc_type_commercial': kwargs.get('doc_type_commercial') == '1',
            'doc_type_invoice': kwargs.get('doc_type_invoice') == '1',
            'individual_doc_count': ind_count,
            'commercial_doc_count': com_count,
            'invoice_doc_count': inv_count,
            'origin_country_id': _int(kwargs.get('origin_country_id', 0)),
            'state': 'draft',
        })
        files = request.httprequest.files
        for prefix, fmodel, count in [('doc_ind', 'doc_individual_ids', ind_count),
                                       ('doc_com', 'doc_commercial_ids', com_count),
                                       ('doc_inv', 'doc_invoice_ids', inv_count)]:
            for i in range(1, count + 1):
                for f in files.getlist('%s_%d' % (prefix, i))[:1]:
                    if f and f.filename:
                        fdata = f.read()
                        if fdata:
                            att = request.env['ir.attachment'].sudo().create({
                                'name': f.filename, 'datas': b64.b64encode(fdata).decode(),
                                'res_model': 'spc.mofa', 'res_id': record.id, 'type': 'binary',
                            })
                            record.sudo().write({fmodel: [(4, att.id)]})
        return request.redirect('/spc/apply/mofa/declaration/%d' % record.id)

    @http.route('/spc/apply/mofa/declaration/<int:record_id>', type='http', auth='user', website=True)
    def mofa_declaration(self, record_id, **kwargs):
        record = request.env['spc.mofa'].sudo().browse(record_id)

        _price_mofa = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'mofa'),
            ('is_active', '=', True)
        ], limit=1)
        _base_mofa = _price_mofa.amount if _price_mofa else 0.0
        return request.render('spc_portal.mofa_declaration', {'record': record, 'base_price': _base_mofa}) if record.exists() else request.redirect('/spc/concierge-services')

    @http.route('/spc/apply/mofa/declaration/submit', type='http', auth='user', website=True, methods=['POST'])
    def mofa_declaration_submit(self, **kwargs):
        record = request.env['spc.mofa'].sudo().browse(int(kwargs.get('record_id', 0)))
        if not record.exists(): return request.redirect('/spc/concierge-services')
        record.sudo().write({'declaration_accepted': bool(kwargs.get('declaration_accepted'))})
        return request.redirect('/spc/apply/mofa/review/%d' % record.id)

    @http.route('/spc/apply/mofa/review/<int:record_id>', type='http', auth='user', website=True)
    def mofa_review(self, record_id, **kwargs):
        record = request.env['spc.mofa'].sudo().browse(record_id)

        _price_mofa = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'mofa'),
            ('is_active', '=', True)
        ], limit=1)
        _base_mofa = _price_mofa.amount if _price_mofa else 0.0
        return request.render('spc_portal.mofa_review', {'record': record, 'base_price': _base_mofa}) if record.exists() else request.redirect('/spc/concierge-services')

    @http.route('/spc/apply/mofa/review/submit', type='http', auth='user', website=True, methods=['POST'])
    def mofa_review_submit(self, **kwargs):
        record = request.env['spc.mofa'].sudo().browse(int(kwargs.get('record_id', 0)))
        if not record.exists(): return request.redirect('/spc/concierge-services')
        return request.redirect('/spc/apply/mofa/payment/%d' % record.id)

    @http.route('/spc/apply/mofa/payment/<int:record_id>', type='http', auth='user', website=True)
    def mofa_payment(self, record_id, **kwargs):
        record = request.env['spc.mofa'].sudo().browse(record_id)
        return request.render('spc_portal.mofa_payment', {'record': record}) if record.exists() else request.redirect('/spc/concierge-services')

    @http.route('/spc/apply/mofa/payment/submit', type='http', auth='user', website=True, methods=['POST'])
    def mofa_payment_submit(self, **kwargs):
        record = request.env['spc.mofa'].sudo().browse(int(kwargs.get('record_id', 0)))
        if not record.exists(): return request.redirect('/spc/concierge-services')
        record.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
        return request.redirect('/spc/payment/mofa/' + str(record.id))

    # BANKING ASSISTANCE ROUTES
    @http.route('/spc/concierge/banking', type='http', auth='user', website=True)
    def banking_detail(self, **kwargs):
        banking_type = kwargs.get('type', 'new')
        titles = {'new': 'New', 'old': 'New (old)'}
        tags = {'new': 'New', 'old': 'New'}
        return request.render('spc_portal.banking_detail', {
            'banking_type': banking_type,
            'banking_title': titles.get(banking_type, 'New'),
            'banking_tag': tags.get(banking_type, 'New'),
        })

    @http.route('/spc/apply/banking/step1', type='http', auth='user', website=True)
    def banking_step1(self, **kwargs):
        banking_type = kwargs.get('type', 'new')

        _price_banking_assistance = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'banking_assistance'),
            ('is_active', '=', True)
        ], limit=1)
        _base_banking_assistance = _price_banking_assistance.amount if _price_banking_assistance else 0.0
        return request.render('spc_portal.banking_step1', {'banking_type': banking_type, 'base_price': _base_banking_assistance})

    @http.route('/spc/apply/banking/step1/<int:record_id>', type='http', auth='user', website=True)
    def banking_step1_edit(self, record_id, **kwargs):
        record = request.env['spc.banking.assistance'].sudo().browse(record_id)
        return request.render('spc_portal.banking_step1', {
            'banking_type': record.banking_type if record.exists() else 'new',
            'record': record if record.exists() else None,
        })

    @http.route('/spc/apply/banking/step1/submit', type='http', auth='user', website=True, methods=['POST'])
    def banking_step1_submit(self, **kwargs):
        partner = request.env.user.partner_id
        account_type = kwargs.get('account_type', '')
        amount = 2000.0 if account_type == 'corporate' else 1000.0
        from odoo import fields as odoo_fields
        record = request.env['spc.banking.assistance'].sudo().create({
            'partner_id': partner.id,
            'approved_company_id': request.session.get('spc_selected_company_id'),
            'banking_type': kwargs.get('banking_type', 'new'),
            'account_type': account_type,
            'preferred_bank': kwargs.get('preferred_bank', ''),
            'amount': amount,
            'state': 'draft',
            'started_date': odoo_fields.Datetime.now(),
        })
        if account_type == 'corporate':
            return request.redirect('/spc/apply/banking/corp/step1/%d' % record.id)
        return request.redirect('/spc/apply/banking/step2/%d' % record.id)

    @http.route('/spc/apply/banking/step2/<int:record_id>', type='http', auth='user', website=True)
    def banking_step2(self, record_id, **kwargs):
        record = request.env['spc.banking.assistance'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/concierge-services')

        _price_banking_assistance = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'banking_assistance'),
            ('is_active', '=', True)
        ], limit=1)
        _base_banking_assistance = _price_banking_assistance.amount if _price_banking_assistance else 0.0
        return request.render('spc_portal.banking_step2', {'record': record, 'base_price': _base_banking_assistance})

    @http.route('/spc/apply/banking/step2/submit', type='http', auth='user', website=True, methods=['POST'])
    def banking_step2_submit(self, **kwargs):
        import base64 as b64
        record = request.env['spc.banking.assistance'].sudo().browse(int(kwargs.get('record_id', 0)))
        if not record.exists():
            return request.redirect('/spc/concierge-services')
        files = request.httprequest.files
        for fname, fmodel in [('doc_eid','doc_eid_ids'),('doc_passport','doc_passport_ids'),('doc_salary','doc_salary_ids')]:
            for f in files.getlist(fname)[:5]:
                if f and f.filename:
                    fdata = f.read()
                    if fdata:
                        att = request.env['ir.attachment'].sudo().create({
                            'name': f.filename, 'datas': b64.b64encode(fdata).decode(),
                            'res_model': 'spc.banking.assistance', 'res_id': record.id, 'type': 'binary',
                        })
                        record.sudo().write({fmodel: [(4, att.id)]})
        return request.redirect('/spc/apply/banking/step3/%d' % record.id)

    @http.route('/spc/apply/banking/step3/<int:record_id>', type='http', auth='user', website=True)
    def banking_step3(self, record_id, **kwargs):
        record = request.env['spc.banking.assistance'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/concierge-services')

        _price_banking_assistance = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'banking_assistance'),
            ('is_active', '=', True)
        ], limit=1)
        _base_banking_assistance = _price_banking_assistance.amount if _price_banking_assistance else 0.0
        return request.render('spc_portal.banking_step3', {'record': record, 'base_price': _base_banking_assistance})

    @http.route('/spc/apply/banking/step3/submit', type='http', auth='user', website=True, methods=['POST'])
    def banking_step3_submit(self, **kwargs):
        record = request.env['spc.banking.assistance'].sudo().browse(int(kwargs.get('record_id', 0)))
        if not record.exists():
            return request.redirect('/spc/concierge-services')
        record.sudo().write({
            'need_bank_account': kwargs.get('need_bank_account', ''),
            'preferred_financial_provider': kwargs.get('preferred_financial_provider', ''),
        })
        return request.redirect('/spc/apply/banking/review/%d' % record.id)

    @http.route('/spc/apply/banking/review/<int:record_id>', type='http', auth='user', website=True)
    def banking_review(self, record_id, **kwargs):
        record = request.env['spc.banking.assistance'].sudo().browse(record_id)

        _price_banking_assistance = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'banking_assistance'),
            ('is_active', '=', True)
        ], limit=1)
        _base_banking_assistance = _price_banking_assistance.amount if _price_banking_assistance else 0.0
        return request.render('spc_portal.banking_review', {'record': record, 'base_price': _base_banking_assistance}) if record.exists() else request.redirect('/spc/concierge-services')

    @http.route('/spc/apply/banking/review/submit', type='http', auth='user', website=True, methods=['POST'])
    def banking_review_submit(self, **kwargs):
        record = request.env['spc.banking.assistance'].sudo().browse(int(kwargs.get('record_id', 0)))
        if not record.exists(): return request.redirect('/spc/concierge-services')
        return request.redirect('/spc/apply/banking/payment/%d' % record.id)

    @http.route('/spc/apply/banking/payment/<int:record_id>', type='http', auth='user', website=True)
    def banking_payment(self, record_id, **kwargs):
        record = request.env['spc.banking.assistance'].sudo().browse(record_id)
        return request.render('spc_portal.banking_payment', {'record': record}) if record.exists() else request.redirect('/spc/concierge-services')

    @http.route('/spc/apply/banking/payment/submit', type='http', auth='user', website=True, methods=['POST'])
    def banking_payment_submit(self, **kwargs):
        record = request.env['spc.banking.assistance'].sudo().browse(int(kwargs.get('record_id', 0)))
        if not record.exists(): return request.redirect('/spc/concierge-services')
        record.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
        return request.redirect('/spc/payment/banking_assistance/' + str(record.id))

    # BANKING CORPORATE ROUTES
    @http.route('/spc/apply/banking/corp/step1/<int:record_id>', type='http', auth='user', website=True)
    def banking_corp_step1(self, record_id, **kwargs):
        record = request.env['spc.banking.assistance'].sudo().browse(record_id)
        if not record.exists(): return request.redirect('/spc/concierge-services')
        companies = []
        try:
            partner = request.env.user.partner_id
            co_list = request.env['spc.license.reissue'].sudo().search([('partner_id','=',partner.id)], limit=10)
            companies = [{'name': c.company_name} for c in co_list if c.company_name]
        except Exception as _e:
            import logging; logging.getLogger(__name__).error("DRAFT CREATE ERROR [%d]: %s", 7, _e)
        return request.render('spc_portal.banking_step1_corp', {'record': record, 'companies': companies})

    @http.route('/spc/apply/banking/corp/step1/submit', type='http', auth='user', website=True, methods=['POST'])
    def banking_corp_step1_submit(self, **kwargs):
        def _int(v):
            try: return int(v)
            except: return 1
        record = request.env['spc.banking.assistance'].sudo().browse(int(kwargs.get('record_id', 0)))
        if not record.exists(): return request.redirect('/spc/concierge-services')
        sh_count = _int(kwargs.get('shareholder_count', 1))
        record.sudo().write({
            'company_registered_spc': kwargs.get('company_registered_spc', ''),
            'company_name_spc': kwargs.get('company_name_spc') or kwargs.get('company_name_manual') or kwargs.get('company_name_dropdown', ''),
            'multi_shareholder': kwargs.get('multi_shareholder', 'no'),
            'shareholder_count': sh_count,
            'shareholder_1_name': kwargs.get('shareholder_1_name', ''),
            'shareholder_2_name': kwargs.get('shareholder_2_name', ''),
            'shareholder_3_name': kwargs.get('shareholder_3_name', ''),
            'shareholder_4_name': kwargs.get('shareholder_4_name', ''),
        })
        return request.redirect('/spc/apply/banking/corp/docs/%d' % record.id)

    @http.route('/spc/apply/banking/corp/docs/<int:record_id>', type='http', auth='user', website=True)
    def banking_corp_docs(self, record_id, **kwargs):
        record = request.env['spc.banking.assistance'].sudo().browse(record_id)
        if not record.exists(): return request.redirect('/spc/concierge-services')
        return request.render('spc_portal.banking_corp_docs', {'record': record})

    @http.route('/spc/apply/banking/corp/docs/submit', type='http', auth='user', website=True, methods=['POST'])
    def banking_corp_docs_submit(self, **kwargs):
        import base64 as b64
        record = request.env['spc.banking.assistance'].sudo().browse(int(kwargs.get('record_id', 0)))
        if not record.exists(): return request.redirect('/spc/concierge-services')
        files = request.httprequest.files
        for fname, fmodel in [('doc_business_plan','doc_business_plan_ids'),('doc_business_license','doc_business_license_ids'),
                               ('doc_formation_cert','doc_formation_cert_ids'),('doc_share_cert','doc_share_cert2_ids'),
                               ('doc_tenancy','doc_tenancy_ids')]:
            for f in files.getlist(fname)[:5]:
                if f and f.filename:
                    fdata = f.read()
                    if fdata:
                        att = request.env['ir.attachment'].sudo().create({
                            'name': f.filename, 'datas': b64.b64encode(fdata).decode(),
                            'res_model': 'spc.banking.assistance', 'res_id': record.id, 'type': 'binary',
                        })
                        record.sudo().write({fmodel: [(4, att.id)]})
        return request.redirect('/spc/apply/banking/corp/shareholder/1/%d' % record.id)

    @http.route('/spc/apply/banking/corp/shareholder/<int:sh_num>/<int:record_id>', type='http', auth='user', website=True)
    def banking_shareholder_docs(self, sh_num, record_id, **kwargs):
        record = request.env['spc.banking.assistance'].sudo().browse(record_id)
        if not record.exists(): return request.redirect('/spc/concierge-services')
        return request.render('spc_portal.banking_shareholder_docs', {'record': record, 'sh_num': sh_num})

    @http.route('/spc/apply/banking/corp/shareholder/<int:sh_num>/submit', type='http', auth='user', website=True, methods=['POST'])
    def banking_shareholder_docs_submit(self, sh_num, **kwargs):
        import base64 as b64
        record = request.env['spc.banking.assistance'].sudo().browse(int(kwargs.get('record_id', 0)))
        if not record.exists(): return request.redirect('/spc/concierge-services')
        sh_count = record.shareholder_count or 1
        fmap = {
            1: ('doc_sh1_eid_ids','doc_sh1_passport_ids','doc_sh1_bank_ids','doc_sh1_cv_ids'),
            2: ('doc_sh2_eid_ids','doc_sh2_passport_ids','doc_sh2_bank_ids','doc_sh2_cv_ids'),
            3: ('doc_sh3_eid_ids','doc_sh3_passport_ids','doc_sh3_bank_ids','doc_sh3_cv_ids'),
            4: ('doc_sh4_eid_ids','doc_sh4_passport_ids','doc_sh4_bank_ids','doc_sh4_cv_ids'),
        }
        fields = fmap.get(sh_num, fmap[1])
        files = request.httprequest.files
        for fname, fmodel in [('doc_sh_eid',fields[0]),('doc_sh_passport',fields[1]),
                               ('doc_sh_bank',fields[2]),('doc_sh_cv',fields[3])]:
            for f in files.getlist(fname)[:5]:
                if f and f.filename:
                    fdata = f.read()
                    if fdata:
                        att = request.env['ir.attachment'].sudo().create({
                            'name': f.filename, 'datas': b64.b64encode(fdata).decode(),
                            'res_model': 'spc.banking.assistance', 'res_id': record.id, 'type': 'binary',
                        })
                        record.sudo().write({fmodel: [(4, att.id)]})
        if sh_num < sh_count:
            return request.redirect('/spc/apply/banking/corp/shareholder/%d/%d' % (sh_num + 1, record.id))
        return request.redirect('/spc/apply/banking/step3/%d' % record.id)

    # =====================================================
    # BANKING OLD FLOW ROUTES
    # =====================================================

    @http.route('/spc/apply/banking/old/start', type='http', auth='user', website=True)
    def banking_old_start(self, **kwargs):
        record = request.env['spc.banking.assistance'].sudo().create({
            'partner_id': request.env.user.partner_id.id,
            'approved_company_id': request.session.get('spc_selected_company_id'),
            'banking_type': 'old',
            'amount': 2010.0,
        })
        return request.redirect('/spc/apply/banking/old/docs/%d' % record.id)

    @http.route('/spc/apply/banking/old/docs/<int:record_id>', type='http', auth='user', website=True)
    def banking_old_docs(self, record_id, **kwargs):
        record = request.env['spc.banking.assistance'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/concierge-services')

        _price_banking_assistance = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'banking_assistance'),
            ('is_active', '=', True)
        ], limit=1)
        _base_banking_assistance = _price_banking_assistance.amount if _price_banking_assistance else 0.0
        return request.render('spc_portal.banking_old_step1', {'record': record, 'base_price': _base_banking_assistance})

    @http.route('/spc/apply/banking/old/docs/submit', type='http', auth='user', website=True, methods=['POST'])
    def banking_old_docs_submit(self, **kwargs):
        import base64
        record_id = int(kwargs.get('record_id', 0))
        record = request.env['spc.banking.assistance'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/concierge-services')
        def _save(file_key, field_name):
            files = request.httprequest.files.getlist(file_key)
            ids = []
            for f in files:
                if f and f.filename:
                    att = request.env['ir.attachment'].sudo().create({
                        'name': f.filename,
                        'datas': base64.b64encode(f.read()).decode(),
                        'res_model': 'spc.banking.assistance',
                        'res_id': record.id,
                        'type': 'binary',
                    })
                    ids.append(att.id)
            if ids:
                record.sudo().write({field_name: [(4, i) for i in ids]})
        _save('doc_old_trade_license', 'doc_old_trade_license_ids')
        _save('doc_old_formation_cert', 'doc_old_formation_cert_ids')
        _save('doc_old_share_cert', 'doc_old_share_cert_ids')
        _save('doc_old_lease_agreement', 'doc_old_lease_agreement_ids')
        _save('doc_old_memorandum', 'doc_old_memorandum_ids')
        _save('doc_old_good_standing', 'doc_old_good_standing_ids')
        _save('doc_old_incumbency', 'doc_old_incumbency_ids')
        record.sudo().write({'old_remarks': kwargs.get('old_remarks', '')})
        return request.redirect('/spc/apply/banking/old/corp/%d' % record_id)

    @http.route('/spc/apply/banking/old/corp/<int:record_id>', type='http', auth='user', website=True)
    def banking_old_corp(self, record_id, **kwargs):
        record = request.env['spc.banking.assistance'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/concierge-services')

        _price_banking_assistance = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'banking_assistance'),
            ('is_active', '=', True)
        ], limit=1)
        _base_banking_assistance = _price_banking_assistance.amount if _price_banking_assistance else 0.0
        return request.render('spc_portal.banking_old_step2', {'record': record, 'base_price': _base_banking_assistance})

    @http.route('/spc/apply/banking/old/corp/submit', type='http', auth='user', website=True, methods=['POST'])
    def banking_old_corp_submit(self, **kwargs):
        record_id = int(kwargs.get('record_id', 0))
        record = request.env['spc.banking.assistance'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/concierge-services')
        vals = {'need_bank_account_old': kwargs.get('need_bank_account_old', 'no')}
        if kwargs.get('need_bank_account_old') == 'yes':
            vals['preferred_financial_provider_old'] = kwargs.get('preferred_financial_provider_old') or False
        record.sudo().write(vals)
        return request.redirect('/spc/apply/banking/old/declaration/%d' % record_id)

    @http.route('/spc/apply/banking/old/declaration/<int:record_id>', type='http', auth='user', website=True)
    def banking_old_declaration(self, record_id, **kwargs):
        record = request.env['spc.banking.assistance'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/concierge-services')

        _price_banking_assistance = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'banking_assistance'),
            ('is_active', '=', True)
        ], limit=1)
        _base_banking_assistance = _price_banking_assistance.amount if _price_banking_assistance else 0.0
        return request.render('spc_portal.banking_old_declaration', {'record': record, 'base_price': _base_banking_assistance})

    @http.route('/spc/apply/banking/old/declaration/submit', type='http', auth='user', website=True, methods=['POST'])
    def banking_old_declaration_submit(self, **kwargs):
        record_id = int(kwargs.get('record_id', 0))
        record = request.env['spc.banking.assistance'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/concierge-services')
        record.sudo().write({'old_declaration_accepted': True})
        return request.redirect('/spc/apply/banking/old/review/%d' % record_id)

    @http.route('/spc/apply/banking/old/review/<int:record_id>', type='http', auth='user', website=True)
    def banking_old_review(self, record_id, **kwargs):
        record = request.env['spc.banking.assistance'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/concierge-services')

        _price_banking_assistance = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'banking_assistance'),
            ('is_active', '=', True)
        ], limit=1)
        _base_banking_assistance = _price_banking_assistance.amount if _price_banking_assistance else 0.0
        return request.render('spc_portal.banking_old_review', {'record': record, 'base_price': _base_banking_assistance})

    @http.route('/spc/apply/banking/old/review/submit', type='http', auth='user', website=True, methods=['POST'])
    def banking_old_review_submit(self, **kwargs):
        record_id = int(kwargs.get('record_id', 0))
        return request.redirect('/spc/apply/banking/old/payment/%d' % record_id)

    @http.route('/spc/apply/banking/old/payment/<int:record_id>', type='http', auth='user', website=True)
    def banking_old_payment(self, record_id, **kwargs):
        record = request.env['spc.banking.assistance'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/concierge-services')
        return request.render('spc_portal.banking_old_payment', {'record': record})

    @http.route('/spc/apply/banking/old/payment/submit', type='http', auth='user', website=True, methods=['POST'])
    def banking_old_payment_submit(self, **kwargs):
        record_id = int(kwargs.get('record_id', 0))
        record = request.env['spc.banking.assistance'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/concierge-services')
        record.sudo().write({'state': 'submitted', 'payment_status': 'paid'})
        return request.redirect('/spc/payment/banking_assistance_old/' + str(record.id))


    # ══════════════════════════════════════════════════
    # VIP MEDICAL AND EID
    # ══════════════════════════════════════════════════
    @http.route('/spc/concierge/vip-medical-eid/detail', type='http', auth='public', website=True, csrf=False)
    def vip_medical_eid_detail(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.vip_medical_eid_detail', {})

    @http.route('/spc/concierge/vip-medical-eid/step1', type='http', auth='public', website=True, csrf=False)
    def vip_medical_eid_step1(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record_id = int(kw.get('record_id', 0))
        record = request.env['spc.vip.medical.eid'].sudo().browse(record_id) if record_id else None

        _vip_price = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'vip_medical_eid'),
            ('is_active', '=', True)
        ], limit=1)
        _vip_base = _vip_price.amount if _vip_price else 0.0
        return request.render('spc_portal.vip_medical_eid_step1', {'record': record, 'base_price': _vip_base})

    @http.route('/spc/concierge/vip-medical-eid/step1/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def vip_medical_eid_step1_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        partner_id = request.session.get('spc_selected_customer_id') or request.session.get('spc_partner_id')
        vals = {
            'partner_id': partner_id,
            'approved_company_id': request.session.get('spc_selected_company_id'),
            'applicant_select': kw.get('applicant_select',''),
            'first_name': kw.get('first_name',''),
            'last_name': kw.get('last_name',''),
            'contact_number': kw.get('contact_number',''),
            'email': kw.get('email',''),
            'preferred_date': kw.get('preferred_date') or False,
            'building_villa': kw.get('building_villa',''),
            'city': kw.get('city',''),
            'nearest_landmark': kw.get('nearest_landmark',''),
            'state': 'draft',
        }
        record = request.env['spc.vip.medical.eid'].sudo().create(vals)
        return request.redirect('/spc/concierge/vip-medical-eid/step2/%d' % record.id)

    @http.route('/spc/concierge/vip-medical-eid/step2/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def vip_medical_eid_step2(self, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record = request.env['spc.vip.medical.eid'].sudo().browse(record_id)

        _vip_price = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'vip_medical_eid'),
            ('is_active', '=', True)
        ], limit=1)
        _vip_base = _vip_price.amount if _vip_price else 0.0
        return request.render('spc_portal.vip_medical_eid_step2', {'record': record, 'base_price': _vip_base})

    @http.route('/spc/concierge/vip-medical-eid/step2/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def vip_medical_eid_step2_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record_id = int(kw.get('record_id', 0))
        record = request.env['spc.vip.medical.eid'].sudo().browse(record_id)
        # Handle file uploads
        import base64
        for fname, fkey in [('doc_passport_photo','passport_photo'), ('doc_entry_visa','entry_visa')]:
            f = request.httprequest.files.get(fkey)
            if f and f.filename:
                record.write({fname: base64.b64encode(f.read()), fname+'_name': f.filename})
        record.write({'state': 'submitted'})
        return request.redirect('/spc/concierge/vip-medical-eid/review/%d' % record_id)

    @http.route('/spc/concierge/vip-medical-eid/review/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def vip_medical_eid_review(self, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record = request.env['spc.vip.medical.eid'].sudo().browse(record_id)

        _vip_price = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'vip_medical_eid'),
            ('is_active', '=', True)
        ], limit=1)
        _vip_base = _vip_price.amount if _vip_price else 0.0
        return request.render('spc_portal.vip_medical_eid_review', {'record': record, 'base_price': _vip_base})

    @http.route('/spc/concierge/vip-medical-eid/payment/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def vip_medical_eid_payment(self, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record = request.env['spc.vip.medical.eid'].sudo().browse(record_id)
        return request.redirect('/spc/payment/vip_medical_eid/' + str(record.id))

    # ══════════════════════════════════════════════════
    # COMPANY STAMP
    # ══════════════════════════════════════════════════
    @http.route('/spc/concierge/company-stamp/detail', type='http', auth='public', website=True, csrf=False)
    def company_stamp_detail(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.company_stamp_detail', {})

    @http.route('/spc/concierge/company-stamp/step1', type='http', auth='public', website=True, csrf=False)
    def company_stamp_step1(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record_id = int(kw.get('record_id', 0))
        record = request.env['spc.company.stamp'].sudo().browse(record_id) if record_id else None

        _cs_price = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'company_stamp'),
            ('is_active', '=', True)
        ], limit=1)
        _cs_base = _cs_price.amount if _cs_price else 0.0
        return request.render('spc_portal.company_stamp_step1', {'record': record, 'base_price': _cs_base})

    @http.route('/spc/concierge/company-stamp/step1/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def company_stamp_step1_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        partner_id = request.session.get('spc_selected_customer_id') or request.session.get('spc_partner_id')
        vals = {
            'partner_id': partner_id,
            'approved_company_id': request.session.get('spc_selected_company_id'),
            'license_number': kw.get('license_number',''),
            'company_name': kw.get('company_name',''),
            'remarks': kw.get('remarks',''),
            'state': 'draft',
        }
        record = request.env['spc.company.stamp'].sudo().create(vals)
        return request.redirect('/spc/concierge/company-stamp/step2/%d' % record.id)

    @http.route('/spc/concierge/company-stamp/step2/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def company_stamp_step2(self, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record = request.env['spc.company.stamp'].sudo().browse(record_id)

        _cs_price = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'company_stamp'),
            ('is_active', '=', True)
        ], limit=1)
        _cs_base = _cs_price.amount if _cs_price else 0.0
        return request.render('spc_portal.company_stamp_step2', {'record': record, 'base_price': _cs_base})

    @http.route('/spc/concierge/company-stamp/step2/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def company_stamp_step2_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record_id = int(kw.get('record_id', 0))
        record = request.env['spc.company.stamp'].sudo().browse(record_id)
        record.write({'declaration_accepted': bool(kw.get('terms_agreed')), 'state': 'submitted'})
        return request.redirect('/spc/concierge/company-stamp/review/%d' % record_id)

    @http.route('/spc/concierge/company-stamp/review/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def company_stamp_review(self, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record = request.env['spc.company.stamp'].sudo().browse(record_id)

        _cs_price = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'company_stamp'),
            ('is_active', '=', True)
        ], limit=1)
        _cs_base = _cs_price.amount if _cs_price else 0.0
        return request.render('spc_portal.company_stamp_review', {'record': record, 'base_price': _cs_base})

    @http.route('/spc/concierge/company-stamp/payment/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def company_stamp_payment(self, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record = request.env['spc.company.stamp'].sudo().browse(record_id)
        return request.redirect('/spc/payment/company_stamp/' + str(record.id))

    # ══════════════════════════════════════════════════
    # DEPENDENT VISA
    # ══════════════════════════════════════════════════
    @http.route('/spc/concierge/dependent-visa/detail', type='http', auth='public', website=True, csrf=False)
    def dependent_visa_detail(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.dependent_visa_detail', {})

    @http.route('/spc/concierge/dependent-visa/step1', type='http', auth='public', website=True, csrf=False)
    def dependent_visa_step1(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record_id = int(kw.get('record_id', 0))
        record = request.env['spc.dependent.visa'].sudo().browse(record_id) if record_id else None

        _dv_price = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'dependent_visa'),
            ('is_active', '=', True)
        ], limit=1)
        _dv_base = _dv_price.amount if _dv_price else 0.0
        return request.render('spc_portal.dependent_visa_step1', {'record': record, 'base_price': _dv_base})

    @http.route('/spc/concierge/dependent-visa/step1/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def dependent_visa_step1_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        import base64
        partner_id = request.session.get('spc_selected_customer_id') or request.session.get('spc_partner_id')
        vals = {
            'partner_id': partner_id,
            'approved_company_id': request.session.get('spc_selected_company_id'),
            'sponsor_has_spc_visa': kw.get('sponsor_has_spc_visa',''),
            'sponsor_type': kw.get('sponsor_type',''),
            'sponsor_gender': kw.get('sponsor_gender',''),
            'sponsor_first_name': kw.get('sponsor_first_name',''),
            'sponsor_last_name': kw.get('sponsor_last_name',''),
            'sponsor_marital_status': kw.get('sponsor_marital_status',''),
            'tenancy_under_sponsor': kw.get('tenancy_under_sponsor',''),
            'sponsor_select': kw.get('sponsor_select',''),
            'salary': float(kw.get('salary') or 0),
            'designation': kw.get('designation',''),
            'state': 'draft',
        }
        record = request.env['spc.dependent.visa'].sudo().create(vals)
        # Handle file uploads
        for fname, fkey in [
            ('doc_passport_copy','passport_copy'),
            ('doc_residence_visa','residence_visa'),
            ('doc_emirates_id','emirates_id'),
            ('doc_tenancy_contract','tenancy_contract'),
            ('doc_utility_bill','utility_bill'),
            ('doc_trade_license','trade_license'),
        ]:
            f = request.httprequest.files.get(fkey)
            if f and f.filename:
                record.write({fname: base64.b64encode(f.read()), fname+'_name': f.filename})
        return request.redirect('/spc/concierge/dependent-visa/step2/%d' % record.id)


    @http.route('/spc/concierge/dependent-visa/step2/<int:record_id>', type='http', auth='user', website=True)
    def dependent_visa_step2(self, record_id, **kw):
        record = request.env['spc.dependent.visa'].sudo().browse(record_id)

        _dv_price = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'dependent_visa'),
            ('is_active', '=', True)
        ], limit=1)
        _dv_base = _dv_price.amount if _dv_price else 0.0
        return request.render('spc_portal.dependent_visa_step2', {'record': record, 'base_price': _dv_base})

    @http.route('/spc/concierge/dependent-visa/step2/submit', type='http', auth='user', website=True, methods=['POST'])
    def dependent_visa_step2_submit(self, **kw):
        record_id = int(kw.get('record_id', 0))
        record = request.env['spc.dependent.visa'].sudo().browse(record_id)
        vals = {
            'dep_first_name': kw.get('dep_first_name', ''),
            'dep_last_name': kw.get('dep_last_name', ''),
            'dep_father_name': kw.get('dep_father_name', ''),
            'dep_mother_name': kw.get('dep_mother_name', ''),
            'dep_mobile': kw.get('dep_mobile', ''),
            'dep_nationality': kw.get('dep_nationality', ''),
            'dep_prev_nationality': kw.get('dep_prev_nationality', ''),
            'dep_marital_status': kw.get('dep_marital_status', ''),
            'dep_religion': kw.get('dep_religion', ''),
        }
        files = ['dep_passport', 'dep_photo', 'dep_passport_special', 'dep_noc']
        for f in files:
            if f in request.httprequest.files:
                file_obj = request.httprequest.files[f]
                if file_obj.filename:
                    import base64
                    vals[f'doc_{f}'] = base64.b64encode(file_obj.read())
                    vals[f'doc_{f}_name'] = file_obj.filename
        record.sudo().write(vals)
        return request.redirect(f'/spc/concierge/dependent-visa/step3/{record.id}')

    @http.route('/spc/concierge/dependent-visa/step3/<int:record_id>', type='http', auth='user', website=True)
    def dependent_visa_step3(self, record_id, **kw):
        record = request.env['spc.dependent.visa'].sudo().browse(record_id)

        _dv_price = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'dependent_visa'),
            ('is_active', '=', True)
        ], limit=1)
        _dv_base = _dv_price.amount if _dv_price else 0.0
        return request.render('spc_portal.dependent_visa_step3', {'record': record, 'base_price': _dv_base})

    @http.route('/spc/concierge/dependent-visa/step3/submit', type='http', auth='user', website=True, methods=['POST'])
    def dependent_visa_step3_submit(self, **kw):
        record_id = int(kw.get('record_id', 0))
        record = request.env['spc.dependent.visa'].sudo().browse(record_id)
        vals = {
            'applicant_location': kw.get('applicant_location', ''),
            'current_status': kw.get('current_status', ''),
            'change_of_status': kw.get('change_of_status', ''),
        }
        files = ['cancelled_visa_doc', 'valid_visa_doc']
        for f in files:
            if f in request.httprequest.files:
                file_obj = request.httprequest.files[f]
                if file_obj.filename:
                    import base64
                    vals[f'doc_{f}'] = base64.b64encode(file_obj.read())
                    vals[f'doc_{f}_name'] = file_obj.filename
        record.sudo().write(vals)
        return request.redirect(f'/spc/concierge/dependent-visa/step4/{record.id}')

    @http.route('/spc/concierge/dependent-visa/step4/<int:record_id>', type='http', auth='user', website=True)
    def dependent_visa_step4(self, record_id, **kw):
        record = request.env['spc.dependent.visa'].sudo().browse(record_id)

        _dv_price = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'dependent_visa'),
            ('is_active', '=', True)
        ], limit=1)
        _dv_base = _dv_price.amount if _dv_price else 0.0
        return request.render('spc_portal.dependent_visa_step4', {'record': record, 'base_price': _dv_base})

    @http.route('/spc/concierge/dependent-visa/step4/submit', type='http', auth='user', website=True, methods=['POST'])
    def dependent_visa_step4_submit(self, **kw):
        record_id = int(kw.get('record_id', 0))
        record = request.env['spc.dependent.visa'].sudo().browse(record_id)
        vals = {
            'additional_info': kw.get('additional_info', ''),
            'crm_comments': kw.get('crm_comments', ''),
        }
        if 'remark_doc' in request.httprequest.files:
            file_obj = request.httprequest.files['remark_doc']
            if file_obj.filename:
                import base64
                vals['doc_remark'] = base64.b64encode(file_obj.read())
                vals['doc_remark_name'] = file_obj.filename
        record.sudo().write(vals)
        return request.redirect(f'/spc/concierge/dependent-visa/step5/{record.id}')

    @http.route('/spc/concierge/dependent-visa/step5/<int:record_id>', type='http', auth='user', website=True)
    def dependent_visa_step5(self, record_id, **kw):
        record = request.env['spc.dependent.visa'].sudo().browse(record_id)

        _dv_price = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'dependent_visa'),
            ('is_active', '=', True)
        ], limit=1)
        _dv_base = _dv_price.amount if _dv_price else 0.0
        return request.render('spc_portal.dependent_visa_step5', {'record': record, 'base_price': _dv_base})

    @http.route('/spc/concierge/dependent-visa/step5/submit', type='http', auth='user', website=True, methods=['POST'])
    def dependent_visa_step5_submit(self, **kw):
        record_id = int(kw.get('record_id', 0))
        record = request.env['spc.dependent.visa'].sudo().browse(record_id)
        record.sudo().write({'dep_declaration_accepted': kw.get('dep_terms_agreed') == 'yes'})
        return request.redirect(f'/spc/concierge/dependent-visa/review/{record.id}')

    @http.route('/spc/concierge/dependent-visa/review/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def dependent_visa_review(self, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record = request.env['spc.dependent.visa'].sudo().browse(record_id)
        return request.render('spc_portal.dependent_visa_review', {'record': record})

    @http.route('/spc/concierge/dependent-visa/payment/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def dependent_visa_payment(self, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record = request.env['spc.dependent.visa'].sudo().browse(record_id)
        return request.redirect('/spc/payment/dependent_visa/' + str(record.id))

    @http.route('/spc/concierge/doc-delivery/driver/detail', type='http', auth='public', website=True, csrf=False)
    def doc_delivery_driver_detail(self, **kw):
        return request.render('spc_portal.doc_delivery_driver_detail', {})

    @http.route('/spc/concierge/doc-delivery/courier/detail', type='http', auth='public', website=True, csrf=False)
    def doc_delivery_courier_detail(self, **kw):
        return request.render('spc_portal.doc_delivery_courier_detail', {})

    @http.route('/spc/concierge/doc-delivery/driver/step1', type='http', auth='public', website=True, csrf=False)
    def doc_delivery_driver_step1(self, **kw):
        record_id = int(kw.get('record_id', 0))
        record = request.env['spc.document.delivery'].sudo().browse(record_id) if record_id else None

        _price_document_delivery = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'document_delivery'),
            ('is_active', '=', True)
        ], limit=1)
        _base_document_delivery = _price_document_delivery.amount if _price_document_delivery else 0.0
        return request.render('spc_portal.doc_delivery_step1', {'dtype': 'driver', 'record': record, 'base_price': _base_document_delivery})

    @http.route('/spc/concierge/doc-delivery/step1/submit', type='http', auth='public', website=False, csrf=False, methods=['POST'])
    def doc_delivery_step1_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        partner_id = request.session.get('spc_selected_customer_id') or request.session.get('spc_partner_id')
        import datetime
        def parse_date(d):
            try: return datetime.datetime.strptime(d, '%Y-%m-%d').date() if d else False
            except: return False
        vals = {
            'partner_id': partner_id,
            'delivery_type': kw.get('delivery_type', 'driver'),
            'collection_date': parse_date(kw.get('collection_date','')),
            'collection_time_frame': kw.get('collection_time_frame',''),
            'collection_address': kw.get('collection_address',''),
            'delivery_date': parse_date(kw.get('delivery_date','')),
            'delivery_time_frame': kw.get('delivery_time_frame',''),
            'delivery_address': kw.get('delivery_address',''),
            'remarks': kw.get('remarks',''),
            'state': 'draft',
        }
        record = request.env['spc.document.delivery'].sudo().create(vals)
        return request.redirect('/spc/concierge/doc-delivery/step2/%d' % record.id)

    @http.route('/spc/concierge/doc-delivery/step2/<int:record_id>', type='http', auth='public', website=False)
    def doc_delivery_step2(self, record_id, **kw):
        record = request.env['spc.document.delivery'].sudo().browse(record_id)

        _price_document_delivery = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'document_delivery'),
            ('is_active', '=', True)
        ], limit=1)
        _base_document_delivery = _price_document_delivery.amount if _price_document_delivery else 0.0
        return request.render('spc_portal.doc_delivery_step2', {'record': record, 'base_price': _base_document_delivery})

    @http.route('/spc/concierge/doc-delivery/step2/submit', type='http', auth='public', website=False, csrf=False, methods=['POST'])
    def doc_delivery_step2_submit(self, **kw):
        record_id = int(kw.get('record_id', 0))
        record = request.env['spc.document.delivery'].sudo().browse(record_id)
        record.sudo().write({'declaration_accepted': kw.get('terms_agreed') == 'yes'})
        return request.redirect('/spc/concierge/doc-delivery/review/%d' % record.id)

    @http.route('/spc/concierge/doc-delivery/review/<int:record_id>', type='http', auth='public', website=False)
    def doc_delivery_review(self, record_id, **kw):
        record = request.env['spc.document.delivery'].sudo().browse(record_id)

        _price_document_delivery = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'document_delivery'),
            ('is_active', '=', True)
        ], limit=1)
        _base_document_delivery = _price_document_delivery.amount if _price_document_delivery else 0.0
        return request.render('spc_portal.doc_delivery_review', {'record': record, 'base_price': _base_document_delivery})

    @http.route('/spc/concierge/doc-delivery/payment/<int:record_id>', type='http', auth='public', website=False)
    def doc_delivery_payment(self, record_id, **kw):
        record = request.env['spc.document.delivery'].sudo().browse(record_id)
        return request.redirect('/spc/payment/document_delivery/' + str(record_id))


    # ══════════════════════════════════════════════════
    # DRIVING LICENSE
    # ══════════════════════════════════════════════════
    @http.route('/spc/concierge/driving-license', type='http', auth='public', website=True, csrf=False)
    def driving_license_list(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.driving_license_list', {})

    @http.route('/spc/concierge/driving-license/<string:dl_type>/detail', type='http', auth='public', website=True, csrf=False)
    def driving_license_detail(self, dl_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.driving_license_detail', {'dl_type': dl_type})

    @http.route('/spc/concierge/driving-license/<string:dl_type>/step1', type='http', auth='public', website=True, csrf=False)
    def driving_license_step1(self, dl_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        saved = request.session.get('dl_step1_%s' % dl_type, {})

        _price_driving_license = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'driving_license'),
            ('is_active', '=', True)
        ], limit=1)
        _base_driving_license = _price_driving_license.amount if _price_driving_license else 0.0
        return request.render('spc_portal.driving_license_step1', {'dl_type': dl_type, 'saved': saved, 'base_price': _base_driving_license})

    @http.route('/spc/concierge/driving-license/<string:dl_type>/step1/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def driving_license_step1_submit(self, dl_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        import base64
        fee_map = {'new':1890,'amendment':378,'duplicate':1285,'renewal':1285,'transfer':1010}
        partner_id = request.session.get('spc_partner_id')
        first_name = kw.get('first_name','') or kw.get('t_first_name','')
        last_name = kw.get('last_name','') or kw.get('t_last_name','')
        email = kw.get('email','') or kw.get('t_email','')
        phone = kw.get('phone','') or kw.get('t_phone','')
        phone_cc = kw.get('phone_country_code','+971') or kw.get('t_phone_country_code','+971')
        dob = kw.get('date_of_birth') or kw.get('t_date_of_birth') or False
        request.session['dl_step1_%s' % dl_type] = {
            'first_name': first_name, 'last_name': last_name, 'email': email,
            'phone': phone, 'phone_country_code': phone_cc, 'date_of_birth': dob or '',
            'remarks': kw.get('remarks',''), 'license_country': kw.get('license_country',''),
            'country_in_transfer_list': kw.get('country_in_transfer_list',''),
        }
        vals = {
            'partner_id': partner_id,
            'approved_company_id': request.session.get('spc_selected_company_id'),
            'license_type': dl_type,
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone_country_code': phone_cc,
            'phone': phone,
            'date_of_birth': dob,
            'remarks': kw.get('remarks',''),
            'license_country': kw.get('license_country',''),
            'country_in_transfer_list': kw.get('country_in_transfer_list',''),
            'amount': fee_map.get(dl_type, 0),
            'partner_id': request.session.get('spc_selected_customer_id'),
            'approved_company_id': request.session.get('spc_selected_company_id'),
            'state': 'draft',
        }
        from odoo import fields as odoo_fields
        if 'started_date' not in vals:
            vals['started_date'] = odoo_fields.Datetime.now()
        record = request.env['spc.driving.license'].sudo().create(vals)
        for fname, fkey in [
            ('doc_passport','passport'),('doc_emirates_id','emirates_id'),
            ('doc_residence_visa','residence_visa'),('doc_driving_license','driving_license'),
            ('doc_license_translation','license_translation'),
        ]:
            f = request.httprequest.files.get(fkey)
            if f and f.filename:
                record.write({fname: base64.b64encode(f.read()), fname+'_name': f.filename})
        if dl_type == 'transfer':
            return request.redirect('/spc/concierge/driving-license/transfer/step2/%d' % record.id)
        return request.redirect('/spc/concierge/driving-license/%s/declaration/%d' % (dl_type, record.id))

    @http.route('/spc/concierge/driving-license/transfer/step2/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def driving_license_transfer_step2(self, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record = request.env['spc.driving.license'].sudo().browse(record_id)
        return request.render('spc_portal.driving_license_transfer_step2', {'record': record})

    @http.route('/spc/concierge/driving-license/transfer/step2/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def driving_license_transfer_step2_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        import base64
        record_id = int(kw.get('record_id', 0))
        record = request.env['spc.driving.license'].sudo().browse(record_id)
        record.write({
            'doc_submission_ack': bool(kw.get('doc_ack')),
            'remarks': kw.get('comments',''),
        })
        for fname, fkey in [
            ('doc_passport','passport'),('doc_emirates_id','emirates_id'),
            ('doc_residence_visa','residence_visa'),('doc_driving_license','driving_license'),
            ('doc_license_translation','license_translation'),
        ]:
            f = request.httprequest.files.get(fkey)
            if f and f.filename:
                record.write({fname: base64.b64encode(f.read()), fname+'_name': f.filename})
        return request.redirect('/spc/concierge/driving-license/transfer/declaration/%d' % record_id)

    @http.route('/spc/concierge/driving-license/<string:dl_type>/declaration/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def driving_license_declaration(self, dl_type, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record = request.env['spc.driving.license'].sudo().browse(record_id)

        _price_driving_license = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'driving_license'),
            ('is_active', '=', True)
        ], limit=1)
        _base_driving_license = _price_driving_license.amount if _price_driving_license else 0.0
        return request.render('spc_portal.driving_license_declaration', {'record': record, 'dl_type': dl_type, 'base_price': _base_driving_license})

    @http.route('/spc/concierge/driving-license/<string:dl_type>/declaration/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def driving_license_declaration_submit(self, dl_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record_id = int(kw.get('record_id', 0))
        record = request.env['spc.driving.license'].sudo().browse(record_id)
        record.write({'declaration_accepted': bool(kw.get('terms_agreed')), 'state': 'submitted'})
        return request.redirect('/spc/concierge/driving-license/%s/review/%d' % (dl_type, record_id))

    @http.route('/spc/concierge/driving-license/<string:dl_type>/review/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def driving_license_review(self, dl_type, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record = request.env['spc.driving.license'].sudo().browse(record_id)

        _price_driving_license = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'driving_license'),
            ('is_active', '=', True)
        ], limit=1)
        _base_driving_license = _price_driving_license.amount if _price_driving_license else 0.0
        return request.render('spc_portal.driving_license_review', {'record': record, 'dl_type': dl_type, 'base_price': _base_driving_license})

    @http.route('/spc/concierge/driving-license/<string:dl_type>/payment/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def driving_license_payment(self, dl_type, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record = request.env['spc.driving.license'].sudo().browse(record_id)
        return request.redirect('/spc/payment/driving_license/' + str(record_id))

    @http.route('/spc/concierge/doc-delivery/courier/step1', type='http', auth='public', website=True, csrf=False)
    def doc_delivery_courier_step1(self, **kw):
        record_id = int(kw.get('record_id', 0))
        record = request.env['spc.document.delivery'].sudo().browse(record_id) if record_id else None

        _price_document_delivery_courier = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'document_delivery_courier'),
            ('is_active', '=', True)
        ], limit=1)
        _base_document_delivery_courier = _price_document_delivery_courier.amount if _price_document_delivery_courier else 0.0
        return request.render('spc_portal.doc_delivery_courier_step1', {'record': record, 'base_price': _base_document_delivery_courier})

    @http.route('/spc/concierge/doc-delivery/courier/step1/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def doc_delivery_courier_step1_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        partner_id = request.session.get('spc_selected_customer_id') or request.session.get('spc_partner_id')
        import datetime
        def parse_date(d):
            try: return datetime.datetime.strptime(d, '%Y-%m-%d').date() if d else False
            except: return False
        vals = {
            'partner_id': partner_id,
            'delivery_type': 'courier',
            'delivery_standard': kw.get('delivery_standard', ''),
            'collection_date': parse_date(kw.get('collection_date', '')),
            'collection_time_frame': kw.get('collection_time_frame', ''),
            'collection_address': kw.get('collection_address', ''),
            'delivery_date': parse_date(kw.get('delivery_date', '')),
            'delivery_time_frame': kw.get('delivery_time_frame', ''),
            'delivery_address': kw.get('delivery_address', ''),
            'remarks': kw.get('remarks', ''),
            'state': 'draft',
        }
        record = request.env['spc.document.delivery'].sudo().create(vals)
        return request.redirect('/spc/concierge/doc-delivery/courier/step2/%d' % record.id)

    @http.route('/spc/concierge/doc-delivery/courier/step2/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def doc_delivery_courier_step2(self, record_id, **kw):
        record = request.env['spc.document.delivery'].sudo().browse(record_id)

        _price_document_delivery_courier = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'document_delivery_courier'),
            ('is_active', '=', True)
        ], limit=1)
        _base_document_delivery_courier = _price_document_delivery_courier.amount if _price_document_delivery_courier else 0.0
        return request.render('spc_portal.doc_delivery_courier_step2', {'record': record, 'base_price': _base_document_delivery_courier})

    @http.route('/spc/concierge/doc-delivery/courier/step2/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def doc_delivery_courier_step2_submit(self, **kw):
        record_id = int(kw.get('record_id', 0))
        record = request.env['spc.document.delivery'].sudo().browse(record_id)
        record.sudo().write({'declaration_accepted_courier': kw.get('terms_agreed') == 'yes'})
        return request.redirect('/spc/concierge/doc-delivery/courier/step3/%d' % record.id)

    @http.route('/spc/concierge/doc-delivery/courier/step3/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def doc_delivery_courier_step3(self, record_id, **kw):
        record = request.env['spc.document.delivery'].sudo().browse(record_id)

        _price_document_delivery_courier = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'document_delivery_courier'),
            ('is_active', '=', True)
        ], limit=1)
        _base_document_delivery_courier = _price_document_delivery_courier.amount if _price_document_delivery_courier else 0.0
        return request.render('spc_portal.doc_delivery_courier_step3', {'record': record, 'base_price': _base_document_delivery_courier})

    @http.route('/spc/concierge/doc-delivery/courier/step3/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def doc_delivery_courier_step3_submit(self, **kw):
        record_id = int(kw.get('record_id', 0))
        record = request.env['spc.document.delivery'].sudo().browse(record_id)
        vals = {'return_reason': kw.get('return_reason', '')}
        if 'supporting_doc' in request.httprequest.files:
            f = request.httprequest.files['supporting_doc']
            if f.filename:
                import base64
                vals['doc_supporting'] = base64.b64encode(f.read())
                vals['doc_supporting_name'] = f.filename
        record.sudo().write(vals)
        return request.redirect('/spc/concierge/doc-delivery/courier/review/%d' % record.id)

    @http.route('/spc/concierge/doc-delivery/courier/review/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def doc_delivery_courier_review(self, record_id, **kw):
        record = request.env['spc.document.delivery'].sudo().browse(record_id)

        _price_document_delivery_courier = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'document_delivery_courier'),
            ('is_active', '=', True)
        ], limit=1)
        _base_document_delivery_courier = _price_document_delivery_courier.amount if _price_document_delivery_courier else 0.0
        return request.render('spc_portal.doc_delivery_courier_review', {'record': record, 'base_price': _base_document_delivery_courier})

    @http.route('/spc/concierge/doc-delivery/courier/payment/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def doc_delivery_courier_payment(self, record_id, **kw):
        record = request.env['spc.document.delivery'].sudo().browse(record_id)
        return request.redirect('/spc/payment/document_delivery_courier/' + str(record_id))


    # ══════════════════════════════════════════════════
    # PHONE ANSWERING
    # ══════════════════════════════════════════════════
    @http.route('/spc/concierge/phone-answering/new/detail', type='http', auth='public', website=True, csrf=False)
    def phone_answering_detail(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.phone_answering_detail', {})

    @http.route('/spc/concierge/phone-answering/step1', type='http', auth='public', website=True, csrf=False)
    def phone_answering_step1(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record_id = int(kw.get('record_id', 0))
        record = request.env['spc.phone.answering'].sudo().browse(record_id) if record_id else None

        _price_phone_answering = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'phone_answering'),
            ('is_active', '=', True)
        ], limit=1)
        _base_phone_answering = _price_phone_answering.amount if _price_phone_answering else 0.0
        return request.render('spc_portal.phone_answering_step1', {'record': record, 'base_price': _base_phone_answering})

    @http.route('/spc/concierge/phone-answering/step1/submit', type='http', auth='public', website=False, csrf=False, methods=['POST'])
    def phone_answering_step1_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        partner_id = request.session.get('spc_selected_customer_id') or request.session.get('spc_partner_id')
        vals = {
            'partner_id': partner_id,
            'approved_company_id': request.session.get('spc_selected_company_id'),
            'company_brand_name': kw.get('company_brand_name', ''),
            'contact_first_name': kw.get('contact_first_name', ''),
            'contact_last_name': kw.get('contact_last_name', ''),
            'contact_phone_code': kw.get('contact_phone_code', '+971'),
            'contact_phone': kw.get('contact_phone', ''),
            'contact_email': kw.get('contact_email', ''),
            'preferred_greeting': kw.get('preferred_greeting', ''),
            'call_instructions': kw.get('call_instructions', ''),
            'address_line1': kw.get('address_line1', ''),
            'address_line2': kw.get('address_line2', ''),
            'city': kw.get('city', ''),
            'country': kw.get('country', ''),
            'amount': 10.0,
            'state': 'draft',
        }
        from odoo import fields as odoo_fields
        if 'started_date' not in vals:
            vals['started_date'] = odoo_fields.Datetime.now()
        record = request.env['spc.phone.answering'].sudo().create(vals)
        return request.redirect('/spc/concierge/phone-answering/step2/%d' % record.id)

    @http.route('/spc/concierge/phone-answering/step2/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def phone_answering_step2(self, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record = request.env['spc.phone.answering'].sudo().browse(record_id)

        _price_phone_answering = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'phone_answering'),
            ('is_active', '=', True)
        ], limit=1)
        _base_phone_answering = _price_phone_answering.amount if _price_phone_answering else 0.0
        return request.render('spc_portal.phone_answering_step2', {'record': record, 'base_price': _base_phone_answering})

    @http.route('/spc/concierge/phone-answering/step2/submit', type='http', auth='public', website=False, csrf=False, methods=['POST'])
    def phone_answering_step2_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record_id = int(kw.get('record_id', 0))
        record = request.env['spc.phone.answering'].sudo().browse(record_id)
        fee_map = {'1': 315.0, '3': 945.0, '6': 1890.0, '9': 2835.0, '12': 3780.0}
        months = kw.get('months_required', '1')
        record.sudo().write({
            'months_required': months,
            'working_days': kw.get('working_days', ''),
            'working_hours_from': kw.get('working_hours_from', ''),
            'working_hours_to': kw.get('working_hours_to', ''),
            'remarks': kw.get('remarks', ''),
            'company_website': kw.get('company_website', ''),
            'additional_instructions': kw.get('additional_instructions', ''),
            'amount': fee_map.get(months, 10.0),
        })
        return request.redirect('/spc/concierge/phone-answering/declaration/%d' % record.id)

    @http.route('/spc/concierge/phone-answering/declaration/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def phone_answering_declaration(self, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record = request.env['spc.phone.answering'].sudo().browse(record_id)

        _price_phone_answering = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'phone_answering'),
            ('is_active', '=', True)
        ], limit=1)
        _base_phone_answering = _price_phone_answering.amount if _price_phone_answering else 0.0
        return request.render('spc_portal.phone_answering_declaration', {'record': record, 'base_price': _base_phone_answering})

    @http.route('/spc/concierge/phone-answering/declaration/submit', type='http', auth='public', website=False, csrf=False, methods=['POST'])
    def phone_answering_declaration_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record_id = int(kw.get('record_id', 0))
        record = request.env['spc.phone.answering'].sudo().browse(record_id)
        record.sudo().write({'declaration_accepted': kw.get('terms_agreed') == 'yes', 'state': 'submitted'})
        return request.redirect('/spc/concierge/phone-answering/review/%d' % record.id)

    @http.route('/spc/concierge/phone-answering/review/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def phone_answering_review(self, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record = request.env['spc.phone.answering'].sudo().browse(record_id)

        _price_phone_answering = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'phone_answering'),
            ('is_active', '=', True)
        ], limit=1)
        _base_phone_answering = _price_phone_answering.amount if _price_phone_answering else 0.0
        return request.render('spc_portal.phone_answering_review', {'record': record, 'base_price': _base_phone_answering})

    @http.route('/spc/concierge/phone-answering/payment/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def phone_answering_payment(self, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.redirect('/spc/payment/phone_answering/' + str(record_id))

    # ══════════════════════════════════════════════════
    # PO BOX
    # ══════════════════════════════════════════════════
    @http.route('/spc/concierge/po-box/new/detail', type='http', auth='public', website=True, csrf=False)
    def po_box_new_detail(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.po_box_new_detail', {})

    @http.route('/spc/concierge/po-box/renewal/detail', type='http', auth='public', website=True, csrf=False)
    def po_box_renewal_detail(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.po_box_renewal_detail', {})

    @http.route('/spc/concierge/po-box/step1', type='http', auth='public', website=True, csrf=False)
    def po_box_step1(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        stype = kw.get('type', 'new')

        _price_po_box = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'po_box'),
            ('is_active', '=', True)
        ], limit=1)
        _base_po_box = _price_po_box.amount if _price_po_box else 0.0
        return request.render('spc_portal.po_box_step1', {'stype': stype, 'base_price': _base_po_box})

    @http.route('/spc/concierge/po-box/step1/submit', type='http', auth='public', website=False, csrf=False, methods=['POST'])
    def po_box_step1_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        partner_id = request.session.get('spc_selected_customer_id') or request.session.get('spc_partner_id')
        package = kw.get('package_type', 'bronze')
        fee_map = {'light': 1500.0, 'bronze': 3000.0}
        vals = {
            'partner_id': partner_id,
            'approved_company_id': request.session.get('spc_selected_company_id'),
            'service_type': kw.get('service_type', 'new'),
            'package_type': package,
            'prev_pobox_number': kw.get('prev_pobox_number', ''),
            'prev_pobox_emirate': kw.get('prev_pobox_emirate', ''),
            'manager_fullname': kw.get('manager_fullname', ''),
            'manager_phone_code': kw.get('manager_phone_code', '+971'),
            'manager_phone': kw.get('manager_phone', ''),
            'manager_sponsor': kw.get('manager_sponsor', ''),
            'remarks': kw.get('remarks', ''),
            'amount': fee_map.get(package, 1500.0),
            'state': 'draft',
        }
        from odoo import fields as odoo_fields
        if 'started_date' not in vals:
            vals['started_date'] = odoo_fields.Datetime.now()
        record = request.env['spc.po.box'].sudo().create(vals)
        return request.redirect('/spc/concierge/po-box/declaration/%d' % record.id)

    @http.route('/spc/concierge/po-box/declaration/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def po_box_declaration(self, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record = request.env['spc.po.box'].sudo().browse(record_id)

        _price_po_box = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'po_box'),
            ('is_active', '=', True)
        ], limit=1)
        _base_po_box = _price_po_box.amount if _price_po_box else 0.0
        return request.render('spc_portal.po_box_declaration', {'record': record, 'base_price': _base_po_box})

    @http.route('/spc/concierge/po-box/declaration/submit', type='http', auth='public', website=False, csrf=False, methods=['POST'])
    def po_box_declaration_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record_id = int(kw.get('record_id', 0))
        record = request.env['spc.po.box'].sudo().browse(record_id)
        record.sudo().write({
            'declaration_accepted': kw.get('terms_agreed') == 'yes',
            'state': 'submitted',
        })
        return request.redirect('/spc/concierge/po-box/payment/%d' % record.id)

    @http.route('/spc/concierge/po-box/payment/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def po_box_payment(self, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record = request.env['spc.po.box'].sudo().browse(record_id)
        return request.redirect('/spc/payment/po_box/' + str(record_id))

    # ══════════════════════════════════════════════════
    # MOVEMENT REPORT
    # ══════════════════════════════════════════════════
    @http.route('/spc/employee-management/movement-report/detail', type='http', auth='public', website=True, csrf=False)
    def movement_report_detail(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.movement_report_detail', {})

    @http.route('/spc/employee-management/movement-report/step1', type='http', auth='public', website=True, csrf=False)
    def movement_report_step1(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record_id = int(kw.get('record_id', 0))
        record = request.env['spc.movement.report'].sudo().browse(record_id) if record_id else None
        partners = []
        partner_id = request.session.get('spc_selected_customer_id') or request.session.get('spc_partner_id')
        if partner_id:
            partners = request.env['res.partner'].sudo().browse(partner_id).child_ids

        _price_movement_report = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'movement_report'),
            ('is_active', '=', True)
        ], limit=1)
        _base_movement_report = _price_movement_report.amount if _price_movement_report else 0.0
        return request.render('spc_portal.movement_report_step1', {'record': record, 'partners': partners, 'base_price': _base_movement_report})

    @http.route('/spc/employee-management/movement-report/step1/submit', type='http', auth='public', website=False, csrf=False, methods=['POST'])
    def movement_report_step1_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        partner_id = request.session.get('spc_selected_customer_id') or request.session.get('spc_partner_id')
        import base64
        passport_file = request.httprequest.files.get('passport_copy')
        passport_data = False
        passport_fname = False
        if passport_file and passport_file.filename:
            passport_data = base64.b64encode(passport_file.read())
            passport_fname = passport_file.filename

        vals = {
            'partner_id': partner_id,
            'approved_company_id': request.session.get('spc_selected_company_id'),
            'first_name': kw.get('first_name', ''),
            'last_name': kw.get('last_name', ''),
            'passport_number': kw.get('passport_number', ''),
            'email': kw.get('email', ''),
            'phone_code': kw.get('phone_code', '+971'),
            'phone': kw.get('phone', ''),
            'date_of_birth': kw.get('date_of_birth') or False,
            'start_date': kw.get('start_date') or False,
            'end_date': kw.get('end_date') or False,
            'remarks': kw.get('remarks', ''),
            'amount': 765.0,
            'state': 'draft',
        }
        if passport_data:
            vals['passport_copy'] = passport_data
            vals['passport_copy_filename'] = passport_fname
        from odoo import fields as odoo_fields
        if 'started_date' not in vals:
            vals['started_date'] = odoo_fields.Datetime.now()
        record = request.env['spc.movement.report'].sudo().create(vals)
        return request.redirect('/spc/employee-management/movement-report/declaration/%d' % record.id)

    @http.route('/spc/employee-management/movement-report/declaration/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def movement_report_declaration(self, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record = request.env['spc.movement.report'].sudo().browse(record_id)

        _price_movement_report = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'movement_report'),
            ('is_active', '=', True)
        ], limit=1)
        _base_movement_report = _price_movement_report.amount if _price_movement_report else 0.0
        return request.render('spc_portal.movement_report_declaration', {'record': record, 'base_price': _base_movement_report})

    @http.route('/spc/employee-management/movement-report/declaration/submit', type='http', auth='public', website=False, csrf=False, methods=['POST'])
    def movement_report_declaration_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record_id = int(kw.get('record_id', 0))
        record = request.env['spc.movement.report'].sudo().browse(record_id)
        record.sudo().write({
            'declaration_accepted': kw.get('terms_agreed') == 'yes',
            'state': 'submitted',
        })
        return request.redirect('/spc/employee-management/movement-report/review/%d' % record.id)

    @http.route('/spc/employee-management/movement-report/review/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def movement_report_review(self, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record = request.env['spc.movement.report'].sudo().browse(record_id)
        return request.render('spc_portal.movement_report_review', {'record': record})

    @http.route('/spc/employee-management/movement-report/payment/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def movement_report_payment(self, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record = request.env['spc.movement.report'].sudo().browse(record_id)
        return request.redirect('/spc/payment/movement_report/' + str(record_id))




    # ══════════════════════════════════════════════════
    # GENERIC TRACKING DETAIL
    # ══════════════════════════════════════════════════
    @http.route('/spc/request-tracking/detail/<string:model_key>/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def tracking_detail_generic(self, model_key, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        model_name = model_key.replace('_', '.', model_key.count('_') - model_key.replace('spc_','').count('_'))
        # Convert model_key back to model name: spc_license_reissue -> spc.license.reissue
        model_name = model_key.replace('_', '.', 1)
        # Actually replace all underscores after spc
        parts = model_key.split('_')
        model_name = parts[0] + '.' + '.'.join(parts[1:])
        try:
            record = request.env[model_name].sudo().browse(record_id)
            if not record.exists():
                return request.redirect('/spc/request-tracking')
            return request.render('spc_portal.tracking_detail_generic', {
                'record': record,
                'model_name': model_name,
                'getattr': getattr,
            })
        except Exception as e:
            import logging
            logging.getLogger(__name__).error('tracking_detail_generic error: %s', e, exc_info=True)
            return request.redirect('/spc/request-tracking')

    # ══════════════════════════════════════════════════
    # LR TRACKING DETAIL
    # ══════════════════════════════════════════════════
    @http.route('/spc/request-tracking/lr-detail/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def lr_tracking_detail(self, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record = request.env['spc.license.reissue'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/spc/request-tracking')
        return request.render('spc_portal.lr_tracking_detail', {'record': record, 'getattr': getattr})

    # ══════════════════════════════════════════════════
    # UID MERGING
    # ══════════════════════════════════════════════════
    @http.route('/spc/employee-management/uid-merging/detail', type='http', auth='public', website=True, csrf=False)
    def uid_merging_detail(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.uid_merging_detail', {})

    @http.route('/spc/employee-management/uid-merging/step1', type='http', auth='public', website=True, csrf=False)
    def uid_merging_step1(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        partner_id = request.session.get('spc_selected_customer_id') or request.session.get('spc_partner_id')
        partners = []
        if partner_id:
            partners = request.env['res.partner'].sudo().browse(partner_id).child_ids

        _price_uid_merging = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'uid_merging'),
            ('is_active', '=', True)
        ], limit=1)
        _base_uid_merging = _price_uid_merging.amount if _price_uid_merging else 0.0
        return request.render('spc_portal.uid_merging_step1', {'partners': partners, 'base_price': _base_uid_merging})

    @http.route('/spc/employee-management/uid-merging/step1/submit', type='http', auth='public', website=False, csrf=False, methods=['POST'])
    def uid_merging_step1_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        partner_id = request.session.get('spc_selected_customer_id') or request.session.get('spc_partner_id')
        import base64
        passport_file = request.httprequest.files.get('passport_copy')
        passport_data = False
        passport_fname = False
        if passport_file and passport_file.filename:
            passport_data = base64.b64encode(passport_file.read())
            passport_fname = passport_file.filename
        visa_doc = request.httprequest.files.get('visa_cancellation_doc')
        visa_data = False
        visa_fname = False
        if visa_doc and visa_doc.filename:
            visa_data = base64.b64encode(visa_doc.read())
            visa_fname = visa_doc.filename
        from odoo import fields as odoo_fields
        employee_id = kw.get('employee_id', '')
        vals = {
            'partner_id': partner_id,
            'approved_company_id': request.session.get('spc_selected_company_id'),
            'first_name': kw.get('first_name', ''),
            'last_name': kw.get('last_name', ''),
            'contact_number': kw.get('contact_number', ''),
            'phone_code': kw.get('phone_code', '+971'),
            'email': kw.get('email', ''),
            'date_of_birth': kw.get('date_of_birth') or False,
            'visa_application_number': kw.get('visa_application_number', ''),
            'comments': kw.get('comments', ''),
            'manual_employee_name': kw.get('manual_employee_name', ''),
            'amount': 400.0,
            'state': 'draft',
            'started_date': odoo_fields.Datetime.now(),
        }
        if employee_id and str(employee_id).isdigit():
            vals['employee_id'] = int(employee_id)
        if passport_data:
            vals['passport_copy'] = passport_data
            vals['passport_copy_filename'] = passport_fname
        if visa_data:
            vals['visa_cancellation_doc'] = visa_data
            vals['visa_cancellation_doc_filename'] = visa_fname
        vals['approved_company_id'] = request.session.get('spc_selected_company_id')
        record = request.env['spc.uid.merging'].sudo().create(vals)
        return request.redirect('/spc/employee-management/uid-merging/declaration/%d' % record.id)

    @http.route('/spc/employee-management/uid-merging/declaration/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def uid_merging_declaration(self, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record = request.env['spc.uid.merging'].sudo().browse(record_id)

        _price_uid_merging = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'uid_merging'),
            ('is_active', '=', True)
        ], limit=1)
        _base_uid_merging = _price_uid_merging.amount if _price_uid_merging else 0.0
        return request.render('spc_portal.uid_merging_declaration', {'record': record, 'base_price': _base_uid_merging})

    @http.route('/spc/employee-management/uid-merging/declaration/submit', type='http', auth='public', website=False, csrf=False, methods=['POST'])
    def uid_merging_declaration_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record_id = int(kw.get('record_id', 0))
        record = request.env['spc.uid.merging'].sudo().browse(record_id)
        record.sudo().write({'declaration_accepted': kw.get('terms_agreed') == 'yes'})
        return request.redirect('/spc/employee-management/uid-merging/review/%d' % record.id)

    @http.route('/spc/employee-management/uid-merging/review/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def uid_merging_review(self, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record = request.env['spc.uid.merging'].sudo().browse(record_id)

        _price_uid_merging = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'uid_merging'),
            ('is_active', '=', True)
        ], limit=1)
        _base_uid_merging = _price_uid_merging.amount if _price_uid_merging else 0.0
        return request.render('spc_portal.uid_merging_review', {'record': record, 'base_price': _base_uid_merging})

    @http.route('/spc/employee-management/uid-merging/payment/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def uid_merging_payment(self, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record = request.env['spc.uid.merging'].sudo().browse(record_id)
        return request.redirect('/spc/payment/uid_merging/' + str(record_id))

    @http.route('/spc/employee-management/uid-merging/payment/submit', type='http', auth='public', website=False, csrf=False, methods=['POST'])
    def uid_merging_payment_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record_id = int(kw.get('record_id', 0))
        record = request.env['spc.uid.merging'].sudo().browse(record_id)
        record.sudo().write({
            'state': 'submitted',
            'payment_method': kw.get('payment_method', ''),
            'payment_status': 'paid',
        })
        return request.redirect('/spc/payment/uid_merging')

    # ══════════════════════════════════════════════════
    # EID APPOINTMENT
    # ══════════════════════════════════════════════════
    @http.route('/spc/employee-management/eid-appointment/detail', type='http', auth='public', website=True, csrf=False)
    def eid_appointment_detail(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.eid_appointment_detail', {})

    @http.route('/spc/employee-management/eid-appointment/step1', type='http', auth='public', website=True, csrf=False)
    def eid_appointment_step1(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        partner_id = request.session.get('spc_selected_customer_id') or request.session.get('spc_partner_id')
        employees = []
        investors = []
        students = []
        if partner_id:
            partner = request.env['res.partner'].sudo().browse(partner_id)
            employees = partner.child_ids.filtered(lambda p: p.active)
            investors = partner.child_ids.filtered(lambda p: p.active)
            students = partner.child_ids.filtered(lambda p: p.active)

        _price_eid_appointment = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'eid_appointment'),
            ('is_active', '=', True)
        ], limit=1)
        _base_eid_appointment = _price_eid_appointment.amount if _price_eid_appointment else 0.0
        return request.render('spc_portal.eid_appointment_step1', {
            'employees': employees,
            'investors': investors,
            'students': students,
            'base_price': _base_eid_appointment,
        })

    @http.route('/spc/employee-management/eid-appointment/step1/submit', type='http', auth='public', website=False, csrf=False, methods=['POST'])
    def eid_appointment_step1_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        partner_id = request.session.get('spc_selected_customer_id') or request.session.get('spc_partner_id')
        vals = {
            'partner_id': partner_id,
            'approved_company_id': request.session.get('spc_selected_company_id'),
            'applicant_type': kw.get('applicant_type', ''),
            'first_name': kw.get('first_name', ''),
            'last_name': kw.get('last_name', ''),
            'email': kw.get('email', ''),
            'manual_employee_name': kw.get('manual_employee_name', ''),
            'manual_investor_name': kw.get('manual_investor_name', ''),
            'manual_partner_name': kw.get('manual_partner_name', ''),
            'manual_student_name': kw.get('manual_student_name', ''),
            'remarks': kw.get('remarks', ''),
            'amount': 360.0,
            'state': 'draft',
        }
        emp_id = kw.get('employee_profile_id')
        inv_id = kw.get('investor_profile_id')
        par_id = kw.get('partner_profile_id')
        stu_id = kw.get('student_profile_id')
        if emp_id and emp_id.isdigit(): vals['employee_profile_id'] = int(emp_id)
        if inv_id and inv_id.isdigit(): vals['investor_profile_id'] = int(inv_id)
        if par_id and par_id.isdigit(): vals['partner_profile_id'] = int(par_id)
        if stu_id and stu_id.isdigit(): vals['student_profile_id'] = int(stu_id)
        from odoo import fields as odoo_fields
        if 'started_date' not in vals:
            vals['started_date'] = odoo_fields.Datetime.now()
        record = request.env['spc.eid.appointment'].sudo().create(vals)
        return request.redirect('/spc/employee-management/eid-appointment/declaration/%d' % record.id)

    @http.route('/spc/employee-management/eid-appointment/declaration/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def eid_appointment_declaration(self, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record = request.env['spc.eid.appointment'].sudo().browse(record_id)

        _price_eid_appointment = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'eid_appointment'),
            ('is_active', '=', True)
        ], limit=1)
        _base_eid_appointment = _price_eid_appointment.amount if _price_eid_appointment else 0.0
        return request.render('spc_portal.eid_appointment_declaration', {'record': record, 'base_price': _base_eid_appointment})

    @http.route('/spc/employee-management/eid-appointment/declaration/submit', type='http', auth='public', website=False, csrf=False, methods=['POST'])
    def eid_appointment_declaration_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record_id = int(kw.get('record_id', 0))
        record = request.env['spc.eid.appointment'].sudo().browse(record_id)
        record.sudo().write({
            'declaration_accepted': kw.get('terms_agreed') == 'yes',
            'state': 'submitted',
        })
        return request.redirect('/spc/employee-management/eid-appointment/review/%d' % record.id)

    @http.route('/spc/employee-management/eid-appointment/review/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def eid_appointment_review(self, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record = request.env['spc.eid.appointment'].sudo().browse(record_id)

        _price_eid_appointment = request.env['spc.service.price'].sudo().search([
            ('service_type', '=', 'eid_appointment'),
            ('is_active', '=', True)
        ], limit=1)
        _base_eid_appointment = _price_eid_appointment.amount if _price_eid_appointment else 0.0
        return request.render('spc_portal.eid_appointment_review', {'record': record, 'base_price': _base_eid_appointment})

    @http.route('/spc/employee-management/eid-appointment/payment/<int:record_id>', type='http', auth='public', website=True, csrf=False)
    def eid_appointment_payment(self, record_id, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        record = request.env['spc.eid.appointment'].sudo().browse(record_id)
        return request.redirect('/spc/payment/eid_appointment/' + str(record_id))

    @http.route('/spc/notifications', type='json', auth='public', website=True, csrf=False)
    def get_notifications(self, **kw):
        if not self._check_spc_session():
            return {'notifications': [], 'unread_count': 0}
        partner_id = request.session.get('spc_selected_customer_id') or request.session.get('spc_partner_id')
        company_id = request.session.get('spc_selected_company_id')
        if not partner_id or not company_id:
            return {'notifications': [], 'unread_count': 0}
        notifications = request.env['spc.notification'].sudo().search([
            ('partner_id', '=', partner_id),
            ('approved_company_id', '=', company_id),
        ], order='create_date desc', limit=20)
        result = []
        for n in notifications:
            result.append({
                'id': n.id,
                'message': n.message,
                'is_read': n.is_read,
                'date': n.create_date.strftime('%d %b %Y, %I:%M %p') if n.create_date else '',
            })
        unread = len([n for n in result if not n['is_read']])
        return {'notifications': result, 'unread_count': unread}

    @http.route('/spc/notifications/mark-read', type='json', auth='public', website=True, csrf=False)
    def mark_notifications_read(self, notification_ids=None, **kw):
        if not self._check_spc_session():
            return {'success': False}
        if notification_ids:
            request.env['spc.notification'].sudo().browse(notification_ids).write({'is_read': True})
        return {'success': True}
