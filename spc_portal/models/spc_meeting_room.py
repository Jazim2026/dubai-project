from odoo import models, fields, api

class SpcMeetingRoom(models.Model):
    _name = 'spc.meeting.room'
    _description = 'Meeting Room Booking'
    _rec_name = 'name'
    _order = 'create_date desc'

    name = fields.Char('Reference', readonly=True, default='New')
    partner_id = fields.Many2one('res.partner', 'Customer')
    state = fields.Selection([
        ('draft','Draft'),('submitted','Submitted'),
        ('confirmed','Confirmed'),('cancelled','Cancelled'),
    ], default='draft')

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
