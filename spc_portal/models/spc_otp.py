# -*- coding: utf-8 -*-
import random
import string
from datetime import datetime, timedelta
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class SpcOtp(models.Model):
    _name = 'spc.otp'
    _description = 'SPC Portal OTP'
    _rec_name = 'email'

    email = fields.Char(string='Email', required=True)
    otp_code = fields.Char(string='OTP Code', required=True)
    is_verified = fields.Boolean(string='Verified', default=False)
    expiry_time = fields.Datetime(string='Expiry Time')
    attempt_count = fields.Integer(string='Attempts', default=0)

    @api.model
    def generate_otp(self, email):
        # Delete old OTPs
        self.search([('email', '=', email), ('is_verified', '=', False)]).unlink()

        otp_code = ''.join(random.choices(string.digits, k=6))
        expiry_time = datetime.now() + timedelta(minutes=10)

        record = self.create({
            'email': email,
            'otp_code': otp_code,
            'expiry_time': expiry_time,
        })
        record._send_otp_email()
        return record

    def _send_otp_email(self):
        try:
            template = self.env.ref('spc_portal.mail_template_spc_otp', raise_if_not_found=False)
            if template:
                template.send_mail(self.id, force_send=True)
            else:
                mail = self.env['mail.mail'].create({
                    'subject': 'Your OTP Code - SPC Free Zone',
                    'email_to': self.email,
                    'email_from': 'odooadam21@gmail.com',
                    'body_html': f'''
                        <div style="font-family:Arial,sans-serif;max-width:500px;margin:0 auto;padding:30px;">
                            <h2 style="color:#1a3c6e;">SPC | Free Zone</h2>
                            <p style="color:#374151;">Your OTP verification code:</p>
                            <div style="background:linear-gradient(135deg,#1a3c6e,#2a6db5);border-radius:8px;padding:20px;text-align:center;margin:20px 0;">
                                <span style="color:white;font-size:38px;font-weight:bold;letter-spacing:12px;">{self.otp_code}</span>
                            </div>
                            <p style="color:#6b7280;font-size:13px;">Valid for <b>10 minutes</b>. Do not share this code.</p>
                        </div>
                    ''',
                })
                mail.send()
        except Exception as e:
            _logger.error("OTP email error: %s", e)

    @api.model
    def verify_otp(self, email, otp_code):
        record = self.search([
            ('email', '=', email),
            ('is_verified', '=', False),
        ], limit=1, order='id desc')

        if not record:
            return False, 'No OTP found. Please request a new one.'

        if datetime.now() > record.expiry_time:
            record.unlink()
            return False, 'OTP expired. Please request a new one.'

        if record.attempt_count >= 5:
            record.unlink()
            return False, 'Too many attempts. Please request a new OTP.'

        if record.otp_code != otp_code:
            record.attempt_count += 1
            remaining = 5 - record.attempt_count
            return False, f'Invalid OTP. {remaining} attempts remaining.'

        record.is_verified = True
        return True, 'OTP verified successfully.'
