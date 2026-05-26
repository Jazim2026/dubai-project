from odoo import models, fields, api

class SpcNotification(models.Model):
    _name = 'spc.notification'
    _description = 'SPC Notification'
    _order = 'create_date desc'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    approved_company_id = fields.Many2one('spc.approved.company', string='Company', required=True)
    message = fields.Text(string='Message', required=True)
    is_read = fields.Boolean(string='Read', default=False)
    sent_by = fields.Many2one('res.users', string='Sent By', default=lambda self: self.env.user)
    source_model = fields.Char(string='Source Model')
    source_id = fields.Integer(string='Source ID')


class SpcSendNotificationWizard(models.TransientModel):
    _name = 'spc.send.notification.wizard'
    _description = 'Send Notification Wizard'

    @api.model
    def _domain_partner_id(self):
        partner_ids = self.env['spc.approved.company'].sudo().search(
            [('partner_id', '!=', False), ('active', '=', True)]
        ).mapped('partner_id.id')
        return [('id', 'in', partner_ids)]

    partner_id = fields.Many2one(
        'res.partner',
        string='SPC Customer',
        required=True,
        domain=_domain_partner_id,
    )
    approved_company_id = fields.Many2one(
        'spc.approved.company',
        string='Company Name',
        required=True,
        domain="[('partner_id', '=', partner_id)]"
    )
    message = fields.Text(string='Message', required=True)
    source_model = fields.Char(string='Source Model')
    source_id = fields.Integer(string='Source ID')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.approved_company_id = False
        if self.partner_id:
            return {'domain': {'approved_company_id': [('partner_id', '=', self.partner_id.id), ('active', '=', True)]}}
        return {'domain': {'approved_company_id': [('id', '=', False)]}}

    def action_send(self):
        self.env['spc.notification'].create({
            'partner_id': self.partner_id.id,
            'approved_company_id': self.approved_company_id.id,
            'message': self.message,
            'sent_by': self.env.user.id,
            'source_model': self.source_model,
            'source_id': self.source_id,
        })
        return {'type': 'ir.actions.act_window_close'}
