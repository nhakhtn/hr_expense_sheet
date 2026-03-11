# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrExpenseSheetRefuseWizard(models.TransientModel):
    _name = 'hr.expense.sheet.refuse.wizard'
    _description = 'Refuse Expense Sheet Wizard'

    sheet_id = fields.Many2one(
        'hr.expense.sheet',
        string='Expense Sheet',
        required=True,
        default=lambda self: self.env.context.get('default_sheet_id'),
    )
    refusal_reason = fields.Text(
        string='Reason for Refusal',
        required=True,
    )

    def action_refuse(self):
        """Refuse the expense sheet."""
        self.ensure_one()
        self.sheet_id.action_refuse(self.refusal_reason)
        return True
