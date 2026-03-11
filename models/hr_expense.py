# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    sheet_id = fields.Many2one(
        'hr.expense.sheet',
        string='Expense Sheet',
        index=True,
        copy=False,
    )
    is_owner = fields.Boolean(
        string='Is Owner',
        compute='_compute_is_owner',
        store=False,
    )

    @api.depends('sheet_id', 'sheet_id.employee_id')
    def _compute_is_owner(self):
        for expense in self:
            if expense.sheet_id:
                expense.is_owner = (expense.sheet_id.employee_id.user_id == self.env.user)
            else:
                expense.is_owner = (expense.employee_id.user_id == self.env.user)

    def action_remove_from_sheet(self, refusal_reason=False):
        """Remove expense from sheet and set to refused."""
        for expense in self:
            if expense.sheet_id:
                expense.sudo().write({
                    'sheet_id': False,
                    'state': 'draft',
                })
                # Set approval_state to refused
                expense.sudo()._do_refuse(refusal_reason or 'Removed from sheet by approver')
        return True
