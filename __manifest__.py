# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Expense Sheet',
    'version': '19.0.1.0.5',
    'category': 'Human Resources/Expenses',
    'summary': 'Group multiple expenses into sheets for batch approval - version 5',
    'description': """
Expense Sheet Module
===================

This module allows employees to group multiple expenses into a sheet for batch
approval and payment processing.

Features:
- Create expense sheets to group multiple expenses
- Submit entire sheet for approval at once
- Approve/refuse entire sheet
- Post journal entries for all expenses in sheet
- Register payment for all expenses in sheet
    """,
    'website': 'https://www.odoo.com',
    'depends': ['hr_expense'],
    'data': [
        'security/ir.model.access.csv',
        'security/hr_expense_sheet_security.xml',
        'views/hr_expense_sheet_views.xml',
        'views/hr_expense_views.xml',
        'wizard/hr_expense_sheet_refuse_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
