# -*- coding: utf-8 -*-
{
    'name': "Overtime",

    'summary': """
        Overtime for employee.""",

    'description': """
        Overtime for employee.
    """,

    "author": "Neural Technologies Indonesia",
    "website": "http://www.nti.co.id",
    
    'category': 'Human Resources',
    'version': '14.0',

    'depends': ['base', 'hr', 'hr_attendance', 'hr_contract', 'resource', 'mail', 'report_xlsx'],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'reports/action.xml',
        'wizards/generate_overtime.xml',
        'wizards/overtime_batch.xml',
    ],
    'application': True
}
