from odoo import _, api, fields, models
from dateutil.relativedelta import relativedelta

class GenerateOvertimeRecapitulation(models.TransientModel):
    _name = 'generate.overtime.recapitulation'
    _description = 'Generate Overtime Recapitulation'
    
    start_date = fields.Date('Start Date', default=fields.Date().today().replace(day=1))
    end_date = fields.Date('End Date', default=fields.Date().today() + relativedelta(months=+1, day=1, days=-1))

        
    def download_xlsx_report(self):
        months = ['Januari','Februari','Maret','April','Mei','Juni','Juli','Agustus','September','Oktober','November', 'Desember']
        
        template_report = 'nti_overtime.overtime_recapitulation_report'
        self.env.ref(template_report).print_report_name = "'Laporan Lembur - %s %s'" % (months[self.end_date.month-1], str(self.end_date.year))
        return self.env.ref(template_report).report_action(self)
    

    