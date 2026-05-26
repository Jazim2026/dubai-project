# -*- coding: utf-8 -*-
from odoo import models, fields

class SpcPendingDetailsDoc(models.Model):
    _name = 'spc.pending.details.doc'
    _description = 'SPC Pending Details Doc'

    partner_id = fields.Many2one('res.partner', string='Partner', required=True, ondelete='restrict')
    customer_name = fields.Char(string='Customer Name')
    pending_doc_name_type = fields.Char(string='Document Type')
    pending_details = fields.Text(string='Pending Details')
    state = fields.Char(string='State')
    count = fields.Integer(string='Count')
    is_submitted = fields.Boolean(string='Submitted', default=False)
