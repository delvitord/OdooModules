from odoo import _, api, fields, models
from datetime import date,datetime
from odoo.exceptions import ValidationError

class OvertimeRequestBatch(models.TransientModel):
    _name = 'overtime.request.batch'
    _description = 'Overtime Request Batch'

    reason_id = fields.Many2one('overtime.reason', string='Reason')
    rule_id = fields.Many2one('overtime.rule', string='Rule')
    date_from = fields.Datetime('Date From')
    date_to = fields.Datetime('Date To')
    employee_ids = fields.Many2many('hr.employee', string='Employee')

    def generate_overtime_batch(self):
        ovt = self.env['hr.overtime']
        reason = self.reason_id
        rule = self.rule_id
        dfrom = self.date_from
        dto = self.date_to

        emp_ids = []
        for emp in self.employee_ids:
            emp_att = ovt.create(self.prepare_ovt(reason, rule, dfrom, dto, emp))
            emp_ids.append(emp_att.id)

        return {
            'name': 'Overtime Request',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'target': 'current',
            'res_model': 'hr.overtime',
            'domain': [('id','in',emp_ids)]
        }   
        
    def prepare_ovt(self, reason, rule, dfrom, dto, emp):
        res = {
            'employee_id': emp.id,
            'reason_id': reason.id,
            'rule_id': rule.id,
            'req_start': dfrom,
            'req_end': dto,
        }
        return res





    