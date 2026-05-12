from odoo import models, fields, api

class PendingDetailsDoc(models.Model):
    _name = 'spc.pending.details.doc'
    _description = 'Pending Details and Docs'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    customer_name = fields.Char(string='Customer Name', related='partner_id.name', store=True)
    pending_doc_name_type = fields.Char(string='Pending Documents Name and Type')
    count = fields.Integer(string='Count', default=0)
    pending_details = fields.Text(string='Pending Details')
    document_line_ids = fields.One2many('spc.pending.doc.line', 'parent_id', string='Document Uploads')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('submitted', 'Submitted'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft')
    is_submitted = fields.Boolean(string='Submitted by Customer', default=False)

    def action_send(self):
        self.write({'state': 'sent'})
        return True

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        return True

    @api.onchange('count')
    def _onchange_count(self):
        if self.count and self.count > 0:
            current = len(self.document_line_ids)
            if self.count > current:
                for i in range(self.count - current):
                    self.document_line_ids = [(0, 0, {
                        'sequence': current + i + 1,
                        'name': 'Document %d' % (current + i + 1)
                    })]
            elif self.count < current:
                to_remove = self.document_line_ids[self.count:]
                self.document_line_ids = [(3, rec.id) for rec in to_remove]


class PendingDocLine(models.Model):
    _name = 'spc.pending.doc.line'
    _description = 'Pending Document Upload Line'
    _order = 'sequence'

    parent_id = fields.Many2one('spc.pending.details.doc', string='Parent', ondelete='cascade')
    sequence = fields.Integer(string='Sequence')
    name = fields.Char(string='Label')
    document = fields.Binary(string='Upload Document', attachment=True)
    document_filename = fields.Char(string='Filename')


class ReceivedDetails(models.Model):
    _name = 'spc.received.details'
    _description = 'Received Details from Customer'

    pending_id = fields.Many2one('spc.pending.details.doc', string='Pending Request', ondelete='cascade')
    customer_name = fields.Char(string='Customer Name', related='pending_id.customer_name', store=True)
    partner_id = fields.Many2one('res.partner', string='Customer', related='pending_id.partner_id', store=True)
    pending_doc_name_type = fields.Char(string='Document Name and Type', related='pending_id.pending_doc_name_type', store=True)
    pending_details = fields.Text(string='Customer Pending Details')
    received_line_ids = fields.One2many('spc.received.doc.line', 'received_id', string='Uploaded Documents')
    state = fields.Selection([('received', 'Received')], string='Status', default='received')
    submission_date = fields.Datetime(string='Submission Date', default=fields.Datetime.now)


class ReceivedDocLine(models.Model):
    _name = 'spc.received.doc.line'
    _description = 'Received Document Line'
    _order = 'sequence'

    received_id = fields.Many2one('spc.received.details', string='Received Details', ondelete='cascade')
    sequence = fields.Integer(string='Sequence')
    name = fields.Char(string='Label')
    document = fields.Binary(string='Uploaded Document', attachment=True)
    document_filename = fields.Char(string='Filename')
