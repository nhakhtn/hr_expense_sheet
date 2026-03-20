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

    @api.depends('total_amount_currency', 'tax_ids', 'currency_id', 'company_id')
    def _compute_total_amount(self):
        """Override to support tax-included total: when user enters total with tax,
        calculate tax backward from the total.

        For tax-included expenses (no product, user enters total directly):
        - User enters: total_amount_currency = 500,000 VND (total including tax)
        - We calculate: untaxed = total / (1 + tax_rate)
        - Tax = total - untaxed
        """
        AccountTax = self.env['account.tax']
        for expense in self:
            if not expense.company_id:
                continue

            # Check if this is a tax-included case (no product, user enters total directly)
            if not expense.product_id and expense.total_amount_currency and expense.tax_ids:
                # Calculate total tax rate from all selected taxes
                # Note: This works for multiple percentage taxes on the same base
                # For compound taxes or fixed taxes, the calculation may vary
                tax_rate = sum(tax.amount for tax in expense.tax_ids) / 100.0

                if tax_rate > 0:
                    # Backward calculation from tax-included total
                    # total = untaxed * (1 + tax_rate)
                    # untaxed = total / (1 + tax_rate)
                    total_excluded = expense.total_amount_currency / (1 + tax_rate)
                    tax_amount = expense.total_amount_currency - total_excluded

                    expense.tax_amount = tax_amount
                    expense.untaxed_amount = total_excluded
                else:
                    # Zero percent tax - no calculation needed
                    expense.tax_amount = 0
                    expense.untaxed_amount = expense.total_amount_currency

                expense.total_amount = expense.total_amount_currency
                continue

            # Default Odoo behavior for other cases (with product or no tax)
            if expense.is_multiple_currency:
                base_line = expense._prepare_base_line_for_taxes_computation(
                    price_unit=expense.total_amount_currency * expense.currency_rate,
                    quantity=1.0,
                    currency_id=expense.company_currency_id,
                    rate=1.0,
                )
                AccountTax._add_tax_details_in_base_line(base_line, expense.company_id)
                AccountTax._round_base_lines_tax_details([base_line], expense.company_id)
                expense.total_amount = base_line['tax_details']['total_included_currency']
                expense.tax_amount = base_line['tax_details']['total_currency']
                expense.untaxed_amount = base_line['tax_details']['total_excluded_currency']
            else:
                expense.total_amount = expense.total_amount_currency

    @api.depends('quantity', 'price_unit', 'tax_ids', 'product_id')
    def _compute_total_amount_currency(self):
        """Override to preserve user-entered total_amount_currency when no product is selected."""
        for expense in self:
            # If no product and user has entered total_amount_currency, preserve it
            if not expense.product_id and expense.total_amount_currency:
                # Don't recalculate - keep user's input
                continue
            # Default Odoo behavior
            super(HrExpense, expense)._compute_total_amount_currency()

    def action_refuse_expense(self, refusal_reason=False):
        """Refuse expense but keep it in the sheet."""
        for expense in self:
            if expense.sheet_id and expense.state in ('submitted', 'approved'):
                # Keep in sheet, just mark as refused
                expense.sudo()._do_refuse(refusal_reason or 'Refused by approver')
        return True
