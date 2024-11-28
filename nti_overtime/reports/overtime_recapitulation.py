from odoo import _, api, fields, models
from odoo.exceptions import UserError
from datetime import date,datetime
import time
import base64
import babel
import logging
import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell
from xlsxwriter.utility import xl_range
_logger = logging.getLogger(__name__)
try:
    from StringIO import StringIO
except ImportError:
    from io import BytesIO

class OvertimeRecapitulationXLS(models.AbstractModel):
    _name = 'report.nti_overtime.overtime_recapitulation_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, obj):
        
        # TEMPLATE REPORT
        title_header = workbook.add_format({'font_size': 16, 'align': 'center', 'valign': 'vcenter' ,'bold': True})
        text_style = workbook.add_format({'font_size': 10, 'left': 1, 'bottom': 1, 
        'right': 1, 'top': 1, 'align': 'center', 'valign': 'vcenter', 
        'text_wrap': True, })
        text_left = workbook.add_format({'font_size': 10, 'left': 1, 'bottom': 1, 
        'right': 1, 'top': 1, 'align': 'left', 'valign': 'vcenter', 
        'text_wrap': True, })
        text_style_bor_bold = workbook.add_format({'bold': True, 'font_size': 10, 'border': 2,'align': 'center', 'valign': 'vcenter', 
        'text_wrap': True, })
        header = workbook.add_format({'font_size': 10, 'left': 1, 'bottom': 1, 
        'right': 1, 'top': 1, 'align': 'center', 'valign': 'vcenter', 
        'text_wrap': True, 'bold': True})
        sub_header = workbook.add_format({'align': 'center', 'valign': 'vcenter', 
        'size': 11, 'bold': True})
        sub_left = workbook.add_format({'align': 'left', 'valign': 'vcenter', 
        'size': 11, 'bold': True})
        sub_head_bold = workbook.add_format({'align': 'center', 'valign': 'vcenter', 
        'size': 11, 'bold': True, 'border': 2})
        cell_text_format = workbook.add_format({'align': 'left', 'valign': 'vcenter', 
        'bold': True, 'size': 12})
        cell_text_format_top_left_right = workbook.add_format({'align': 'center', 
        'valign': 'vcenter', 'bold': True, 'size': 11, 'top': 1,
        'left': 1, 'right': 1, 'bottom': 1})
        cell_text_format_top_left_right.set_bg_color('#80a7fa')
        money_format = workbook.add_format({'border': 1, 'valign': 'vcenter', 'num_format': 'Rp ###,###,###,##0'})
        money_format_bold = workbook.add_format({'align': 'right', 'valign': 'vcenter', 'bold':True, 'border': 2, 'num_format': 'Rp ###,###,###,##0'})
        text_style_bold = workbook.add_format({'font_size': 10, 'left': 1, 'bottom': 1, 'right': 1, 'top': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True, 'bold': True, 'border': 2, })
    
        query_get_employees = '''
        SELECT 
            emp.name AS employee,
            job.name AS job,
            type.name AS contract_type,
            dept.name AS department,
            (cont.wage + cont.allowance) AS amount,
            sum(ovt.final_total_hours) AS total_hours,
	        sum(ovt.total_amount) AS total_amount
		FROM hr_overtime AS ovt 
		LEFT JOIN hr_employee AS emp on ovt.employee_id = emp.id
		LEFT JOIN hr_job AS job on emp.job_id = job.id
		LEFT JOIN hr_contract AS cont on emp.contract_id = cont.id
		LEFT JOIN hr_department AS dept on emp.department_id = dept.id
		LEFT JOIN hr_contract_type AS type on cont.contract_type_id = type.id
		WHERE ovt.state = 'done' AND DATE(real_start  + interval '7 hour') >= '%s' and DATE(real_end  + interval '7 hour') <= '%s'
		GROUP BY emp.name, dept.name, job.name, type.name, cont.wage, cont.allowance
		ORDER BY dept.name, type.name, emp.name''' % (obj.start_date, obj.end_date)

        query_get_contract_type = '''
        SELECT
            contract_type.name AS contract_type
        FROM hr_overtime AS ovt
        LEFT JOIN hr_employee AS emp on ovt.employee_id = emp.id
        LEFT JOIN hr_contract AS cont on emp.contract_id = cont.id
        LEFT JOIN hr_contract_type AS contract_type on cont.contract_type_id = contract_type.id
        WHERE ovt.state = 'done' AND DATE(real_start  + interval '7 hour') >= '%s' and DATE(real_end  + interval '7 hour') <= '%s'
        GROUP BY contract_type.name''' % (obj.start_date, obj.end_date)
        
        self.env.cr.execute(query_get_employees)
        list_employees = self.env.cr.dictfetchall()

        self.env.cr.execute(query_get_contract_type)
        list_contract_types = self.env.cr.dictfetchall()

        if list_employees:
            for cont in list_contract_types:
                worksheet = workbook.add_worksheet(cont['contract_type'])
                header.set_bg_color('#95b3d7')
                money_format_bold.set_bg_color('#95b3d7')
                sub_head_bold.set_bg_color('#95b3d7')
                text_style_bold.set_bg_color('#95b3d7')
                header.set_border(1)
                sub_left.set_border(1)

                worksheet.set_column('A:A', 5)
                worksheet.set_column('B:C', 40)
                worksheet.set_column('D:Z', 15)

                worksheet.merge_range('A4:A6', 'No.', header)
                worksheet.merge_range('B4:B6', 'Nama', header)
                worksheet.merge_range('C4:C6', 'Jabatan', header)
                worksheet.merge_range('D4:D6', 'Upah', header)
                worksheet.merge_range('E4:E6', 'Total Jam Lembur', header)
                worksheet.merge_range('F4:F6', 'Total Uang Lembur', header)

                # LOGO COMPANY
                # logo_company = BytesIO(base64.b64decode(obj.env.company.logo))
                # worksheet.insert_image('A1', 'GAG.png', {'image_data': logo_company,
                #                                     'y_scale' :0.9,'x_offset': 5,
                #                                     })
                
                # HEADER TITLE
                months = ['Januari','Februari','Maret','April','Mei','Juni','Juli','Agustus','September','Oktober','November', 'Desember']
                
                worksheet.set_row(0, 35)
                worksheet.merge_range(0, 2, 0, 5, 'Laporan Lembur Periode %s'% (months[obj.end_date.month-1] + ' ' + str(obj.end_date.year)), title_header)

                depts = []
                row = 6
                f_row = 0
                l_row = 0
                num = 1
                row_tot = []
                
                for rec in list_employees:
                    if rec['contract_type'] == cont['contract_type']:
                        
                        emp_job = list(rec['job'].values())[0] if rec['job'] else '-'
                        
                        if rec['department'] not in depts:
                            data_length = len(rec) - 1
                            
                            if not depts:
                                depts.append(rec['department'])
                                worksheet.merge_range(row, 0, row, data_length-1, rec['department'], sub_left)
                                row += 1
                                
                            else:
                                depts.append(rec['department'])

                                worksheet.merge_range(row, 0, row, 2, ' ', sub_head_bold)
                                for line in range(3, data_length):
                                    if line == 4 :
                                        worksheet.write(row, line, '=SUM(%s:%s)' % (xl_rowcol_to_cell(f_row, line),xl_rowcol_to_cell(l_row, line)), text_style_bold)
                                    elif line != 4 :
                                        worksheet.write(row, line, '=SUM(%s:%s)' % (xl_rowcol_to_cell(f_row, line),xl_rowcol_to_cell(l_row, line)), money_format_bold)
                                row_tot.append(row)

                                row += 1
                                worksheet.merge_range(row, 0, row, data_length-1, rec['department'], sub_left)
                                row += 1
                                
                            if rec['department']:
                                worksheet.write(row, 0, num, text_style)
                                worksheet.write(row, 1, rec['employee'], text_left)
                                worksheet.write(row, 2, emp_job, text_left)
                                worksheet.write(row, 3, rec['amount'], money_format)
                                worksheet.write(row, 4, rec['total_hours'], text_style)
                                worksheet.write(row, 5, rec['total_amount'], money_format)
                            
                                f_row = row
                                l_row = row
                                row += 1
                                num += 1
                                
                            else:
                                continue
                            
                        else:
                            worksheet.write(row, 0, num, text_style)
                            worksheet.write(row, 1, rec['employee'], text_left)
                            worksheet.write(row, 2, emp_job, text_left)
                            worksheet.write(row, 3, rec['amount'], money_format)
                            worksheet.write(row, 4, rec['total_hours'], text_style)
                            worksheet.write(row, 5, rec['total_amount'], money_format)
                            row += 1
                            l_row += 1
                            num += 1
                            
                    else:
                        continue
                    
                worksheet.merge_range(row, 0, row, 2, ' ', sub_head_bold)
                data_length = len(rec) - 1
                for line in range(3, data_length):
                    if line == 4:
                        worksheet.write(row, line, '=SUM(%s:%s)' % (xl_rowcol_to_cell(f_row, line),xl_rowcol_to_cell(l_row, line)), text_style_bold)
                    elif line != 4:    
                        worksheet.write(row, line, '=SUM(%s:%s)' % (xl_rowcol_to_cell(f_row, line),xl_rowcol_to_cell(l_row, line)), money_format_bold)
                row_tot.append(row)

                row += 1
                data_length = len(rec) - 1
                for l in range(3, data_length):
                    sum_formula = ''
                    for r in row_tot:
                        if not sum_formula:
                            sum_formula = xl_rowcol_to_cell(r, l)
                        else:
                            sum_formula = str(sum_formula) + '+' + xl_rowcol_to_cell(r, l)
                    if l == 4:
                        worksheet.write(row, l, '=%s' % sum_formula, text_style_bold)
                    elif l != 4:
                        worksheet.write(row, l, '=%s' % sum_formula, money_format_bold)
                worksheet.merge_range(row, 0, row, 2, 'Total', sub_head_bold)
                    
        else:
            worksheet = workbook.add_worksheet('No Datas Available')
            header.set_bg_color('#95b3d7')
            money_format_bold.set_bg_color('#95b3d7')
            sub_head_bold.set_bg_color('#95b3d7')
            text_style_bold.set_bg_color('#95b3d7')
            header.set_border(1)
            sub_left.set_border(1)

            worksheet.set_column('A:A', 5)
            worksheet.set_column('B:C', 40)
            worksheet.set_column('D:Z', 15)

            worksheet.merge_range('A4:A6', 'No.', header)
            worksheet.merge_range('B4:B6', 'Nama', header)
            worksheet.merge_range('C4:C6', 'Jabatan', header)
            worksheet.merge_range('D4:D6', 'Upah', header)
            worksheet.merge_range('E4:E6', 'Total Jam Lembur', header)
            worksheet.merge_range('F4:F6', 'Total Uang Lembur', header)
            
            # LOGO COMPANY
            # logo_company = BytesIO(base64.b64decode(obj.env.company.logo))
            # worksheet.insert_image('A1', 'GAG.png', {'image_data': logo_company,
            #                                     'y_scale' :0.9,'x_offset': 5,
            #                                     })
            
            # HEADER TITLE
            months = ['Januari','Februari','Maret','April','Mei','Juni','Juli','Agustus','September','Oktober','November', 'Desember']
            
            worksheet.set_row(0, 35)
            worksheet.merge_range(0, 2, 0, 5, 'Laporan Lembur Periode %s'% (months[obj.end_date.month-1] + ' ' + str(obj.end_date.year)), title_header)