# -*- coding: utf-8 -*-
import logging
import base64
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class SpcPortalController(http.Controller):

    def _check_spc_session(self):
        return bool(request.session.get('spc_otp_verified') and request.session.get('spc_uid'))

    def _spc_redirect(self):
        return request.redirect('/spc/login')

    # ── LOGIN ──
    @http.route('/spc/login', type='http', auth='public', website=True, csrf=False)
    def login_page(self, **kw):
        return request.render('spc_portal.template_spc_login', {
            'error': kw.get('error', ''),
            'email': kw.get('email', ''),
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
        customers = request.env['res.partner'].sudo().search([
            ('is_company', '=', False),
            ('active', '=', True),
        ], order='name asc')
        selected_customer_id = request.session.get('spc_selected_customer_id')
        selected_customer = None
        if selected_customer_id:
            rec = request.env['res.partner'].sudo().browse(selected_customer_id)
            if rec.exists():
                selected_customer = rec
        return request.render('spc_portal.template_spc_dashboard', {
            'company': user.company_id,
            'customers': customers,
            'selected_customer': selected_customer,
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
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        if customer_id:
            request.session['spc_selected_customer_id'] = int(customer_id)
        return request.redirect('/spc/customer-dashboard')

    @http.route('/spc/customer-dashboard', type='http', auth='public', website=True, csrf=False)
    def customer_dashboard(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        customer_id = request.session.get('spc_selected_customer_id')
        customer = None
        if customer_id:
            rec = request.env['res.partner'].sudo().browse(customer_id)
            if rec.exists():
                customer = rec
        return request.render('spc_portal.template_spc_customer_dashboard', {
            'customer': customer,
        })

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
            nr_steps = ['Legal type', 'Business activities', 'Company', 'Facility', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Bank account', 'Documents', 'Review', 'Payment']
        return request.render('spc_portal.template_setup_company_step2', {
            'service_type': service_type,
            'activities_data': activities_data,
            'categories': categories,
            'fee': fees_map.get(service_type, 0),
            'steps': nr_steps,
            'active_step': 1 if service_type == 'name_reservation' else 1,
            'current_step': 1,
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
        if service_type == 'name_reservation':
            return request.redirect('/spc/setup-new-company/apply/nr-step2/' + service_type)
        if service_type == 'pre_approval':
            return request.redirect('/spc/setup-new-company/apply/pa-step3/' + service_type)
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
        return request.render('spc_portal.template_setup_company_step6', {
            'service_type': service_type, 'form_data': {}, 'errors': [],
        })

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
        return request.render('spc_portal.template_setup_company_step7', {'service_type': service_type})

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
        return request.render('spc_portal.template_setup_company_step8', {'service_type': service_type})

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
        return request.render('spc_portal.template_setup_company_step9', {'service_type': service_type})

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
        return request.render('spc_portal.template_setup_company_step10', {'service_type': service_type})

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
        return request.render('spc_portal.template_setup_company_step11', {'service_type': service_type})

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
        return request.render('spc_portal.template_setup_company_step12', {'service_type': service_type})

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

        try:
            app = request.env['spc.company.application'].sudo().create({
                'partner_id': customer_id,
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
        return request.render('spc_portal.template_setup_company_step14', {'service_type': service_type})

    @http.route('/spc/setup-new-company/apply/step14/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def setup_company_apply_step14_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'company_new')
        return request.redirect('/spc/setup-new-company/apply/success/' + service_type)

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
        return request.render('spc_portal.template_company_management', {
            'customer': customer,
            'allocated_visa': 1, 'available_visa': 1,
            'used_visa': 0, 'in_progress_visa': 0,
            'employees': 0, 'documents': 27, 'key_stakeholders': 3,
            'service_requests': [],
        })

    @http.route('/spc/request-tracking', type='http', auth='public', website=True, csrf=False)
    def request_tracking(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        customer_id = request.session.get('spc_selected_customer_id')
        customer = None
        requests_list = []
        if customer_id:
            rec = request.env['res.partner'].sudo().browse(customer_id)
            if rec.exists():
                customer = rec
                requests_list = request.env['spc.service.request'].sudo().search([
                    ('partner_id', '=', customer.id)
                ], order='create_date desc')
        return request.render('spc_portal.template_request_tracking', {
            'customer': customer,
            'requests': requests_list,
        })

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
        return request.render('spc_portal.template_nr_step5', {'service_type': service_type})

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
        return request.render('spc_portal.template_pa_step4', {
            'service_type': service_type,
            'customer': customer,
            'countries': countries,
            'fee': 640,
            'form_data': request.session.get('pa_step4_data', {}),
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
        customer_id = request.session.get('spc_selected_customer_id')
        customer = None
        if customer_id:
            rec = request.env['res.partner'].sudo().browse(customer_id)
            if rec.exists():
                customer = rec
        return request.render('spc_portal.template_pa_payment', {
            'service_type': service_type,
            'customer': customer,
            'fee': 640,
            'steps': ['Business activities', 'Company name', 'Shareholder details', 'Declaration', 'Review application', 'Payment'],
            'current_step': 6,
            'payment_action': '/spc/setup-new-company/apply/pa-payment/submit',
        })

    @http.route('/spc/setup-new-company/apply/pa-payment/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def pa_payment_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'pre_approval')
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
                'fee': 640.0,
                'shareholder_data': str(step5) if step5 else '',
                'manager_data': str(step6) if step6 else '',
                'director_data': str(step7) if step7 else '',
                'ubo_data': str(step8) if step8 else '',
                'nature_of_business_data': str(step9) if step9 else '',
                'supporting_doc_notes': str({k: v for k, v in step10.items()}) if step10 else '',
                'shareholder_data': str(step5) if step5 else '',
                'manager_data': str(step6) if step6 else '',
                'director_data': str(step7) if step7 else '',
                'ubo_data': str(step8) if step8 else '',
                'nature_of_business_data': str(step9) if step9 else '',
                'supporting_doc_notes': str({k: v for k, v in step10.items()}) if step10 else '',
                'payment_method': kw.get('payment_method', ''),
                'payment_status': 'paid',
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
        return request.redirect('/spc/setup-new-company/apply/pa-success/' + service_type)

    @http.route('/spc/setup-new-company/apply/pa-success/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def pa_success(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_pa_success', {'service_type': service_type})

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
                'state': 'submitted',
                'idn_number': step1.get('idn_number', ''),
                'legal_type': step2.get('legal_type', ''),
                'package_type': step2.get('package_type', ''),
                'activity_names': ', '.join(step3.get('activity_names', [])),
                'shareholder_data': str(step5) if step5 else '',
                'manager_data': str(step6) if step6 else '',
                'director_data': str(step7) if step7 else '',
                'ubo_data': str(step8) if step8 else '',
                'nature_of_business_data': str(step9) if step9 else '',
                'supporting_doc_notes': str({k: v for k, v in step10.items()}) if step10 else '',
                'shareholder_data': str(step5) if step5 else '',
                'manager_data': str(step6) if step6 else '',
                'director_data': str(step7) if step7 else '',
                'ubo_data': str(step8) if step8 else '',
                'nature_of_business_data': str(step9) if step9 else '',
                'supporting_doc_notes': str({k: v for k, v in step10.items()}) if step10 else '',
                'payment_method': kw.get('payment_method', ''),
                'payment_status': 'paid',
            }
            if idn_company_id:
                try:
                    vals['idn_company_id'] = int(idn_company_id)
                except:
                    pass
            lr = request.env['spc.license.reissue'].sudo().create(vals)
            if activity_ids:
                lr.business_activity_ids = [(6, 0, activity_ids)]
            for key in ['lr_step1_data', 'lr_step2_data', 'lr_step3_data']:
                request.session.pop(key, None)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"LR save error: {e}")
        return request.redirect('/spc/company-management/apply/success/' + service_type)

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
            'current_step': 2,
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
                'state': 'submitted',
                'license_company_name': step1.get('company_name', ''),
                'legal_type': step2.get('legal_type', ''),
                'package_type': step2.get('package_type', ''),
                'activity_names': ', '.join(step3.get('activity_names', [])),
                'license_validity': step4.get('license_validity', ''),
                'facility_type': step4.get('facility_type', ''),
                'visa_allocation': int(step4.get('visa_allocation', 0) or 0),
                'shareholder_data': str(step5) if step5 else '',
                'manager_data': str(step6) if step6 else '',
                'director_data': str(step7) if step7 else '',
                'ubo_data': str(step8) if step8 else '',
                'nature_of_business_data': str(step9) if step9 else '',
                'supporting_doc_notes': str({k: v for k, v in step10.items()}) if step10 else '',
                'shareholder_data': str(step5) if step5 else '',
                'manager_data': str(step6) if step6 else '',
                'director_data': str(step7) if step7 else '',
                'ubo_data': str(step8) if step8 else '',
                'nature_of_business_data': str(step9) if step9 else '',
                'supporting_doc_notes': str({k: v for k, v in step10.items()}) if step10 else '',
                'payment_method': kw.get('payment_method', ''),
                'payment_status': 'paid',
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
            rn = request.env['spc.renewal'].sudo().create(vals)
            if activity_ids:
                rn.business_activity_ids = [(6, 0, activity_ids)]
            for key in ['rn_step1_data', 'rn_step2_data', 'rn_step3_data', 'rn_step4_data', 'rn_doc']:
                request.session.pop(key, None)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"RN save error: {e}")
        return request.redirect('/spc/company-management/apply/success/' + service_type)

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
        return request.redirect('/spc/company-management/apply/ra-step2/' + service_type)

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
        return request.redirect('/spc/company-management/apply/ra-step3/' + service_type)

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
        return request.render('spc_portal.template_setup_company_apply', {
            'customer': customer,
            'service_type': service_type,
            'fee': 0,
            'steps': ['Company', 'Renewal type', 'Legal type', 'Business activities', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Supporting documents', 'Review application', 'Payment'],
            'current_step': 3,
            'form_submit_url': '/spc/company-management/apply/ra-step3/submit',
        })

    @http.route('/spc/company-management/apply/ra-step3/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def ra_step3_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        service_type = kw.get('service_type', 'renewal_amendment')
        request.session['ra_step3_data'] = {k: v for k, v in kw.items() if isinstance(v, str)}
        return request.redirect('/spc/company-management/apply/ra-step4/' + service_type)

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
        return request.render('spc_portal.template_rn_step3', {
            'service_type': service_type,
            'activities_data': activities_data,
            'categories': categories,
            'fee': 0,
            'steps': ['Company', 'Renewal type', 'Legal type', 'Business activities', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Supporting documents', 'Review application', 'Payment'],
            'current_step': 4,
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
        return request.redirect('/spc/company-management/apply/ra-step5/' + service_type)

    @http.route('/spc/company-management/apply/ra-step5/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def ra_step5(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_setup_company_step6', {
            'service_type': service_type,
            'steps': ['Company', 'Renewal type', 'Legal type', 'Business activities', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Supporting documents', 'Review application', 'Payment'],
            'current_step': 5,
            'form_submit_url': '/spc/company-management/apply/ra-step5/submit',
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
        return request.redirect('/spc/company-management/apply/ra-step6/' + service_type)

    @http.route('/spc/company-management/apply/ra-step6/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def ra_step6(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_setup_company_step7', {
            'service_type': service_type,
            'steps': ['Company', 'Renewal type', 'Legal type', 'Business activities', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Supporting documents', 'Review application', 'Payment'],
            'current_step': 6,
            'form_submit_url': '/spc/company-management/apply/ra-step6/submit',
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
        return request.redirect('/spc/company-management/apply/ra-step7/' + service_type)

    @http.route('/spc/company-management/apply/ra-step7/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def ra_step7(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_setup_company_step8', {
            'service_type': service_type,
            'steps': ['Company', 'Renewal type', 'Legal type', 'Business activities', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Supporting documents', 'Review application', 'Payment'],
            'current_step': 7,
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
        return request.redirect('/spc/company-management/apply/ra-step8/' + service_type)

    @http.route('/spc/company-management/apply/ra-step8/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def ra_step8(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_setup_company_step9', {
            'service_type': service_type,
            'steps': ['Company', 'Renewal type', 'Legal type', 'Business activities', 'Shareholder(s)', 'Manager(s)', 'Director(s)', 'UBO', 'Nature of business', 'Supporting documents', 'Review application', 'Payment'],
            'current_step': 8,
            'form_submit_url': '/spc/company-management/apply/ra-step8/submit',
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
            }
            if step1.get('company_id'):
                try:
                    vals['company_id'] = int(step1['company_id'])
                except:
                    pass
            if board_doc.get('data'):
                vals['board_resolution_file'] = board_doc['data']
                vals['board_resolution_filename'] = board_doc.get('filename', '')
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
                        'ra_step9_data', 'ra_step10_data', 'ra_doc', 'ra_board_doc']:
                request.session.pop(key, None)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"RA save error: {e}")
        return request.redirect('/spc/company-management/apply/success/renewal_amendment')


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
        return request.redirect('/spc/company-management/apply/amd-step2/' + service_type)

    @http.route('/spc/company-management/apply/amd-step2/<string:service_type>', type='http', auth='public', website=True, csrf=False)
    def amd_step2(self, service_type, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        return request.render('spc_portal.template_amd_step2', {
            'service_type': service_type,
            'steps': ['Company', 'Company amendment(s)', 'Nature of business', 'Supporting Document', 'Review application', 'Payment'],
            'current_step': 2,
        })

    @http.route('/spc/company-management/apply/amd-step2/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def amd_step2_submit(self, **kw):
        if not self._check_spc_session():
            return request.redirect('/spc/login')
        import base64
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
            'legal_type': 'spc_portal.template_setup_company_apply',
            'business_activities': 'spc_portal.template_setup_company_step2',
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
        template = step_templates.get(step_name, 'spc_portal.template_setup_company_step10')
        return request.render(template, {
            'service_type': service_type,
            'steps': step_list,
            'current_step': current_idx,
            'form_submit_url': submit_url,
            'activities': activities,
            'activities_data': activities_data,
            'categories': categories,
            'fee': 0,
            'shareholder_count': 1,
            'manager_count': 1,
            'director_count': 1,
            'ubo_count': 1,
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
            for key in ['amd_step1_data', 'amd_step2_data', 'amd_step3_data', 'amd_step4_data', 'amd_board_doc']:
                request.session.pop(key, None)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"AMD save error: {e}")
        return request.redirect('/spc/company-management/apply/success/amendment')



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
        return request.render('spc_portal.template_ec_payment', {
            'service_type': service_type,
            'sub_type': sub_type,
            'steps': steps,
            'current_step': len(steps),
        })

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
            }
            if company_data.get('company_id'):
                try:
                    vals['company_id'] = int(company_data['company_id'])
                except:
                    pass
            request.env['spc.establishment.card'].sudo().create(vals)
            for key in ['ec_step1_data', 'ec_company_data', 'ec_decl_data']:
                request.session.pop(key, None)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"EC save error: {e}")
        return request.redirect('/spc/company-management/apply/success/ec_' + kw.get('sub_type', 'new'))

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
                'state': 'submitted',
                'document_names': step1.get('document_names', ''),
                'remarks': step1.get('remarks', ''),
                'declaration': bool(step2.get('declaration')),
                'payment_method': kw.get('payment_method', ''),
                'payment_status': 'paid',
            }
            request.env['spc.certify'].sudo().create(vals)
            for key in ['certify_step1_data', 'certify_step2_data']:
                request.session.pop(key, None)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Certify save error: {e}")
        return request.redirect('/spc/company-management/apply/success/certify')

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
            request.env['spc.visa.allocation.amendment'].sudo().create(vals)
            for key in ['va_step1_data', 'va_step2_data', 'va_step3_data', 'va_step4_data', 'va_step5_data', 'va_step6_data']:
                request.session.pop(key, None)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"VA save error: {e}")
        return request.redirect('/spc/company-management/apply/success/visa_allocation_amendment')
