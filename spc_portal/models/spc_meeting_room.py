from odoo import models, fields, api

class SpcMeetingRoom(models.Model):
    _name = 'spc.meeting.room'
    _description = 'Meeting Room Booking'
    _rec_name = 'name'
    _order = 'create_date desc'

    name = fields.Char('Reference', readonly=True, default='New')
    partner_id = fields.Many2one('res.partner', 'Customer')
    approved_company_id = fields.Many2one('spc.approved.company', string='Company')
    state = fields.Selection([
        ('draft','Draft'),('submitted','Submitted'),
        ('confirmed','Confirmed'),('cancelled','Cancelled'),
    ], default='draft')
    # Request Tracking
    current_step = fields.Integer(string='Current Step', default=1)
    started_date = fields.Datetime(string='Started Date', readonly=True)

    booking_date = fields.Date('Booking Date')
    booking_start_time = fields.Char('Booking Start Time')
    meeting_duration = fields.Selection([
        ('30min','30 Minutes'),('1hr','1 Hour'),('1hr30min','1.5 Hours'),
        ('2hr','2 Hours'),('2hr30min','2.5 Hours'),('3hr','3 Hours'),
        ('4hr','4 Hours'),('5hr','5 Hours'),('6hr','6 Hours'),
        ('full_day','Full Day (8 Hours)'),
    ], 'Meeting Duration')
    comments = fields.Text('Comments')

    declaration_accepted = fields.Boolean('Declaration Accepted')
    amount = fields.Float('Service Fee', default=10.0)
    payment_status = fields.Selection([('pending','Pending'),('paid','Paid')], default='pending')

    @api.model
    def create(self, vals):
        if vals.get('name','New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('spc.meeting.room') or 'New'
        return super().create(vals)

    def action_submit(self):   self.state = 'submitted'
    def action_confirm(self):  self.state = 'confirmed'
    def action_cancel(self):   self.state = 'cancelled'

    def action_approve_documents(self):
        self.state = 'documents_approved'
    def action_approve_payment(self):
        self.state = 'payment_approved'
    def action_approve_complaints(self):
        self.state = 'complaints_approved'
    def action_under_process(self):
        self.state = 'under_process'
    def action_completed(self):
        self.state = 'completed'

    def action_send_notification(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Send Notification',
            'res_model': 'spc.send.notification.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_source_model': self._name,
                'default_source_id': self.id,
            }
        }

