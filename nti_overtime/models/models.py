from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from _datetime import datetime, date, timedelta
import pytz

class HrOvertime(models.Model):
    _name = 'hr.overtime'
    _description = 'Overtime'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(tracking=1, readonly=True, states={"draft": [("readonly", False)]}, copy=False)
    employee_id = fields.Many2one('hr.employee', domain=lambda self: self.domain_employee(), string='Employee',tracking=True, readonly=True, states={"draft": [("readonly", False)]})
    job_id = fields.Many2one('hr.job', string='Job Position', related='employee_id.job_id', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('approved', 'Approved'),
        ('realized', 'Realized'),
        ('done', 'Done'),
        ('reject', 'Rejected'),
    ], string='Status', tracking=1, default='draft', copy=False)
    reason_id = fields.Many2one('overtime.reason', string='Reason', tracking=1, readonly=True, states={"draft": [("readonly", False)]}, ondelete='restrict')
    description = fields.Text(tracking=1, readonly=True, states={"draft": [("readonly", False)]})
    rule_id = fields.Many2one('overtime.rule', string='Overtime Rule', tracking=1, ondelete='restrict', copy=False)
    req_start = fields.Datetime('Request Date Start',tracking=1, readonly=True, states={"draft": [("readonly", False)]})
    req_end = fields.Datetime('Request Date End',tracking=1, readonly=True, states={"draft": [("readonly", False)]})
    real_start = fields.Datetime('Realization Date Start',tracking=1)
    real_end = fields.Datetime('Realization Date End',tracking=1)
    is_realization = fields.Boolean('Is Realization', copy=False)
    total_ovt = fields.Float(string="Total Hours",compute='get_total_overtime')
    total_amount = fields.Float(string="Total Amount")
    hourly_pay = fields.Float('Hourly Pay')
    break_time = fields.Float('Break Time')
    is_back_payment = fields.Boolean('Back Payment')
    payment_date = fields.Date('Payment Date')
    final_total_hours = fields.Float('Final Total Hours')
    overtime_detail_line_ids = fields.One2many('overtime.detail', 'overtime_id', string='Overtime Detail')
    rule_type = fields.Selection(related='rule_id.type')

    # @api.constrains('state')
    # def _constrains_state_for_rule(self):
    #     for rec in self:
    #         if not rec.rule_id:
    #             raise ValidationError("You can't request overtime.\nRule is not set.")
    
    def domain_employee(self):
        self = self.sudo()
        ids = self.env['hr.employee'].search([('contract_id.state','=','open')]).ids
        return [('id','in',ids)]
    
    def get_hourly_pay(self):
        result = self.employee_id.contract_id.wage * 1/173
        return result
    
    def get_resource_calendar(self):
        return self.employee_id.resource_calendar_id

    def get_holiday_status(self, start, end):
        resource_calendar = self.get_resource_calendar()
        user_tz = pytz.timezone(self.employee_id.user_id.tz or 'Asia/Jakarta')
        actual_start = fields.Datetime.context_timestamp(self, start).astimezone(user_tz)
        actual_end = fields.Datetime.context_timestamp(self, end).astimezone(user_tz)
        holiday = str(int(actual_start.strftime("%w")) - 1) not in resource_calendar.attendance_ids.mapped('dayofweek')
        if not holiday:
            for hol in resource_calendar.global_leave_ids:
                date_from = fields.Datetime.context_timestamp(self, hol.date_from).astimezone(user_tz)
                date_to = fields.Datetime.context_timestamp(self, hol.date_to).astimezone(user_tz)
                if actual_start.date() >= date_from.date() and actual_end.date() <= date_to.date():
                    holiday = True
                    break
        return holiday
    
    def get_rule_domain(self, employee, holiday):
        return [('is_public_holiday','=',holiday), '|', ('job_ids','=', False), ('job_ids','in', employee.job_id.ids)]

    def get_default_rule(self, employee, holiday):
        self = self.sudo()
        domain = self.get_rule_domain(employee, holiday)
        rule = self.env['overtime.rule'].search(domain, limit=1, order='sequence asc').id
        return rule
    
    def set_overtime_rule(self, get_holiday=True, holiday=False):
        self = self.sudo()
        if get_holiday:
            holiday = self.get_holiday_status(self.req_start, self.req_end)

        if holiday == True:
            if self.employee_id.default_rule_hol_ovt_id:
                self.rule_id =  self.employee_id.default_rule_hol_ovt_id.id
            else:
                self.rule_id = self.get_default_rule(self.employee_id, holiday)
        else:
            if self.employee_id.default_rule_ovt_id:
                self.rule_id =  self.employee_id.default_rule_ovt_id.id
            else:
                self.rule_id = self.get_default_rule(self.employee_id, holiday)
    
    @api.onchange('employee_id', 'req_start', 'req_end')
    def _onchange_employee_id(self):
        self.rule_id = False
        if self.employee_id and not self.rule_id:
            if self.req_start and self.req_end:
                self.set_overtime_rule()

    def compute_amount(self):
        fix_total_ovt = self.total_ovt
        if self.break_time > 0 and self.total_ovt > 0:
            fix_total_ovt = self.total_ovt - self.break_time
        
        if self.rule_id.type == 'fix':
            self.total_amount = self.rule_id.fix_amount
        elif self.rule_id.type == 'base':
            self.total_amount =  fix_total_ovt * self.rule_id.base_amount
        else:
            self.overtime_detail_line_ids = [(5,0,0)]
            hourly_pay = self.get_hourly_pay()
            self.hourly_pay = hourly_pay
            last_hours = 0
            last_multiplier = 0
            total_amount = 0
            
            remaining_hours = fix_total_ovt
            sorted_line_ids = self.rule_id.line_ids.sorted(key=lambda x: x.overtime_hour)
            
            for rule in sorted_line_ids:
                if fix_total_ovt >= rule.overtime_hour:
                    total_amount += rule.multiplier * hourly_pay
                    last_hours = rule.overtime_hour
                    remaining_hours = fix_total_ovt - rule.overtime_hour
                    self.overtime_detail_line_ids = [(0,0, {
                        'overtime_hour': rule.overtime_hour,
                        'total': rule.multiplier * hourly_pay,
                    })]
                elif remaining_hours <= rule.overtime_hour:
                    last_hours = rule.overtime_hour
                    total_amount += rule.multiplier * remaining_hours * hourly_pay
                    self.overtime_detail_line_ids = [(0,0, {
                        'overtime_hour': rule.overtime_hour,
                        'total': rule.multiplier * remaining_hours * hourly_pay,
                    })]
                    break

            etc_hours = last_hours
            self.total_amount = total_amount
            self.final_total_hours = fix_total_ovt
        

    @api.onchange('req_start', 'req_end', 'real_start', 'real_end')
    def date_constrains(self):
        if self.req_start and self.req_end:
            if self.req_start > self.req_end:
                raise ValidationError(("Invalid date."))
        if self.real_start and self.real_end:
            if self.real_start > self.real_end:
                raise ValidationError(("Invalid date."))

    @api.constrains('req_start', 'req_end', 'real_start', 'real_end')
    def _check_date(self):
        for req in self:
            if req.req_start and req.req_end:
                domain = [
                    ('req_start', '<=', req.req_end),
                    ('req_end', '>=', req.req_start),
                    ('employee_id', '=', req.employee_id.id),
                    ('id', '!=', req.id),
                    ('state', 'not in', ['refused']),
                ]
                nholidays = self.search_count(domain)
                if nholidays:
                    raise ValidationError(_(
                        'You can not have 2 Overtime requests that overlaps on same day!'))
            if req.real_start and req.real_end:
                domain = [
                    ('real_start', '<=', req.real_end),
                    ('real_end', '>=', req.real_start),
                    ('employee_id', '=', req.employee_id.id),
                    ('id', '!=', req.id),
                    ('state', 'not in', ['refused']),
                ]
                nholidays = self.search_count(domain)
                if nholidays:
                    raise ValidationError(_(
                        'You can not have 2 Overtime requests that overlaps on same day!'))

    @api.depends('real_start', 'real_end')
    def get_total_overtime(self):
        for rec in self:
            if rec.real_start and rec.real_end:
                conv = rec.real_end - rec.real_start 
                # 0.5 = 30: 30/60
                rounding_minutes = float(rec.rule_id.minute/60)
                actual = conv.total_seconds() / 3600.0
                diff = actual % 1
                if rec.rule_id.rounding_type == 'normal':
                    if rec.rule_id.overtime_rounding == 'custom':
                        if diff < rounding_minutes:
                            rec.total_ovt = (actual - diff)
                        elif diff > rounding_minutes:
                            rec.total_ovt = (actual - diff) + (rounding_minutes*2)
                        else:
                            rec.total_ovt = actual
                    else:
                        if diff < rounding_minutes:
                            rec.total_ovt = actual - diff
                        elif diff > rounding_minutes:
                            rec.total_ovt = (actual - diff) + 1.0
                        else:
                            rec.total_ovt = actual
                elif rec.rule_id.rounding_type == 'up':
                    if rec.rule_id.overtime_rounding == 'custom':
                        if diff < rounding_minutes:
                            rec.total_ovt = (actual - diff) + (rounding_minutes)
                        elif diff > rounding_minutes:
                            rec.total_ovt = (actual - diff) + (rounding_minutes*2)
                        else:
                            rec.total_ovt = actual
                    else:
                        rec.total_ovt = (actual - diff) + 1.0
                elif rec.rule_id.rounding_type == 'down':
                    if rec.rule_id.overtime_rounding == 'custom':
                        if diff < rounding_minutes:
                            rec.total_ovt = (actual - diff) - (rounding_minutes)
                        elif diff > rounding_minutes:
                            rec.total_ovt = (actual - diff) - (rounding_minutes*2)
                        else:
                            rec.total_ovt = actual
                    else:
                        rec.total_ovt = (actual - diff) - 1.0
                elif rec.rule_id.rounding_type == 'actual':
                    rec.total_ovt = actual
                else:
                    rec.total_ovt = 0
                
            else:
                rec.total_ovt = 0

    def button_submit(self):
        for rec in self:
            rec.write({'state': 'submit'})

    def button_reject(self):
        for rec in self:
            rec.write({'state': 'reject'})

    def button_draft(self):
        for rec in self:
            rec.write({'state': 'draft', 'is_realization': False})

    def prepare_realization_data(self, real_start, real_end):
        data = {'is_realization': True, 'real_start': real_start, 'real_end': real_end}
        return data

    def realization(self):
        for rec in self:
            rec.write(self.prepare_realization_data(rec.req_start, rec.req_end))

    def button_approve(self):
        for rec in self:
            rec.realization()
            rec.write({'state': 'approved'})
        
    def button_realized(self):
        for rec in self:
            rec.compute_amount()
            rec.write({'state': 'realized'})
    
    def button_done(self):
        for rec in self:
            rec.compute_amount()
            rec.write({'state': 'done'})

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('hr.overtime')
        return super(HrOvertime, self).create(vals)

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(("You can't delete this document when state is not draft."))
        return super(HrOvertime, self).unlink()
class OvertimeReason(models.Model):
    _name = 'overtime.reason'
    _description = 'Overtime Reason'
    
    name = fields.Char('')

class OvertimeDetail(models.Model):
    _name = 'overtime.detail'
    _description = 'Overtime Detail'

    overtime_id = fields.Many2one('hr.overtime', string='Overtime', ondelete='cascade')
    overtime_hour = fields.Char('Overtime Hour')
    total = fields.Float('Total')

    @api.onchange('overtime_hour')
    def _onchange_overtime_hour(self):
        if self.overtime_hour:
            try:
                int(self.overtime_hour)
            except:
                raise ValidationError('Overtime hour should be a number')

class OvertimeRule(models.Model):
    _name = 'overtime.rule'
    _description = 'Overtime Rule'
    
    name = fields.Char('')
    sequence = fields.Integer('')
    rounding_type = fields.Selection([
        ('normal', 'Normal'),
        ('up', 'Up'),
        ('down', 'Down'),
        ('actual', 'Actual'),
    ], string='Rounding Precision', default='normal')
    overtime_rounding = fields.Selection([
        ('actual', 'Actual'),
        ('custom', 'Custom'),
    ], string='Rounding Minutes', default='custom')
    minute = fields.Integer(string="Amount", default=30)
    is_public_holiday = fields.Boolean('Public Holiday Rule?')
    line_ids = fields.One2many('overtime.rule.line', 'rule_id', string='Rules Line', copy=True)
    type = fields.Selection([
        ('fix', 'Fix Amount'),
        ('rule', 'By Rule'),
        ('base', 'Base Amount')
    ], string='Type', default='rule', tracking=1)
    fix_amount = fields.Float('Fix Amount')
    job_ids = fields.Many2many('hr.job', string='Job Position')
    base_amount = fields.Float('Base Amount', default=0)

    @api.onchange('minute')
    def _onchange_minute(self):
        if self.minute >= 60:
            raise ValidationError(("You can't set minute to 60 or higher.\nIf you want to set 60, please select 'Actual' on Rounding Minutes."))

class OvertimeRuleLine(models.Model):
    _name = 'overtime.rule.line'
    _description = 'Overtime Rule Line'

    rule_id = fields.Many2one('overtime.rule', string='Rule')
    name = fields.Char('')
    overtime_hour = fields.Float('Overtime Hour')
    multiplier = fields.Float(string='Multiplier')
    
class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    
    default_rule_ovt_id = fields.Many2one('overtime.rule', string='Overtime Rule')    
    default_rule_hol_ovt_id = fields.Many2one('overtime.rule', string='Default Overtime Public Holiday Rule')    