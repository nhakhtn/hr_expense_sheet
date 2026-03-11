# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HrExpenseSheet(models.Model):
    _name = 'hr.expense.sheet'
    _description = 'Expense Sheet'
    _order = 'create_date desc'

    name = fields.Char(
        string='Expense Sheet',
        required=True,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        default=lambda self: self.env.user.employee_id,
        readonly=True,
    )
    is_owner = fields.Boolean(
        string='Is Owner',
        compute='_compute_is_owner',
        store=False,
    )
    can_edit = fields.Boolean(
        string='Can Edit',
        compute='_compute_can_edit',
        store=False,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='employee_id.department_id',
        readonly=True,
        store=True,
    )
    manager_id = fields.Many2one(
        'hr.employee',
        string='Manager',
        help='Manager who approves this expense sheet',
        readonly=True,
        compute='_compute_manager_id',
        store=True,
    )

    @api.depends('employee_id')
    def _compute_manager_id(self):
        for sheet in self:
            if sheet.employee_id:
                # Use expense_manager_id if set, otherwise fall back to parent_id
                if sheet.employee_id.expense_manager_id:
                    # Convert user to employee
                    sheet.manager_id = sheet.employee_id.expense_manager_id.employee_id
                else:
                    sheet.manager_id = sheet.employee_id.parent_id
            else:
                sheet.manager_id = False
    expense_ids = fields.One2many(
        'hr.expense',
        'sheet_id',
        string='Expenses',
        copy=False,
    )
    expense_count = fields.Integer(
        string='Expense Count',
        compute='_compute_expense_count',
        store=True,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('posted', 'Posted'),
        ('paid', 'Paid'),
        ('refused', 'Refused'),
    ], string='Status',
        default='draft',
        readonly=True,
        copy=False,
    )
    # Monetary fields
    amount_total = fields.Monetary(
        string='Total Amount',
        compute='_compute_amount',
        store=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    # Dates
    date_submit = fields.Date(
        string='Submit Date',
        readonly=True,
        copy=False,
    )
    date_approve = fields.Date(
        string='Approval Date',
        readonly=True,
        copy=False,
    )
    date_post = fields.Date(
        string='Post Date',
        readonly=True,
        copy=False,
    )
    date_paid = fields.Date(
        string='Paid Date',
        readonly=True,
        copy=False,
    )
    # Accounting
    account_move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        copy=False,
        readonly=True,
    )
    account_payment_id = fields.Many2one(
        'account.payment',
        string='Payment',
        copy=False,
        readonly=True,
    )
    # Notes
    note = fields.Text(
        string='Internal Notes',
    )
    refusal_reason = fields.Text(
        string='Refusal Reason',
        readonly=True,
        copy=False,
    )

    # Compute methods
    @api.depends('expense_ids.total_amount', 'expense_ids.total_amount_currency')
    def _compute_amount(self):
        for sheet in self:
            total = sum(sheet.expense_ids.mapped('total_amount'))
            sheet.amount_total = total

    @api.depends('expense_ids')
    def _compute_expense_count(self):
        for sheet in self:
            sheet.expense_count = len(sheet.expense_ids)

    def _compute_is_owner(self):
        for sheet in self:
            sheet.is_owner = (sheet.employee_id.user_id == self.env.user)

    def _compute_can_edit(self):
        for sheet in self:
            is_owner = (sheet.employee_id.user_id == self.env.user)
            is_manager = self.env.user.has_group('hr_expense.group_hr_expense_team_approver')
            # Can edit if owner (draft/submitted) or manager (any state)
            if is_owner and sheet.state in ('draft', 'submitted'):
                sheet.can_edit = True
            elif is_manager:
                sheet.can_edit = True
            else:
                sheet.can_edit = False

    # Constrains
    @api.constrains('employee_id', 'expense_ids')
    def _check_expense_employee(self):
        for sheet in self:
            for expense in sheet.expense_ids:
                if expense.employee_id != sheet.employee_id:
                    raise ValidationError(
                        _("All expenses must belong to the same employee as the sheet.")
                    )

    # Onchange methods
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.manager_id = self.employee_id.parent_id
            self.currency_id = self.employee_id.company_id.currency_id or self.env.company.currency_id

    # CRUD methods
    def unlink(self):
        for sheet in self:
            # Check if user is the owner or has manager access
            is_owner = (sheet.employee_id.user_id == self.env.user)
            is_manager = self.env.user.has_group('hr_expense.group_hr_expense_team_approver')
            if not is_owner and not is_manager:
                raise UserError(_('You can only delete your own expense sheets.'))
            if sheet.state not in ('draft', 'submitted'):
                raise UserError(_('You can only delete draft or submitted expense sheets.'))
        return super().unlink()

    # Action methods
    def action_submit(self):
        """Submit the expense sheet for approval."""
        self.ensure_one()
        if not self.expense_ids:
            raise UserError(_('Please add at least one expense to submit.'))

        # Check all expenses have non-zero total
        for expense in self.expense_ids:
            if expense.total_amount <= 0:
                raise UserError(
                    _("Expense '%s' has zero total. Please enter a valid amount.")
                    % expense.name
                )
            if expense.state != 'draft':
                raise UserError(
                    _("Expense '%s' is not in draft state. Please reset it to draft first.")
                    % expense.name
                )

        # Submit all expenses
        self.expense_ids.action_submit()

        # Update sheet state
        self.write({
            'state': 'submitted',
            'date_submit': fields.Date.today(),
        })


        return True

    def action_approve(self):
        """Approve the expense sheet."""
        self.ensure_one()
        if self.state != 'submitted':
            return False

        # Approve all expenses
        for expense in self.expense_ids:
            if expense.state != 'submitted':
                continue
            try:
                expense.action_approve()
            except Exception as e:
                raise UserError(
                    _("Cannot approve expense '%s': %s") % (expense.name, str(e))
                )

        # Update sheet state
        self.write({
            'state': 'approved',
            'date_approve': fields.Date.today(),
        })


        return True

    def action_refuse(self, refusal_reason=False):
        """Refuse the expense sheet."""
        self.ensure_one()

        # Refuse all expenses using Odoo's internal _do_refuse method
        for expense in self.expense_ids:
            if expense.state in ('submitted', 'approved'):
                expense.sudo()._do_refuse(refusal_reason or '')

        # Update sheet state
        self.write({
            'state': 'refused',
            'refusal_reason': refusal_reason,
        })

        return True

    def action_post(self):
        """Create journal entries for all approved expenses."""
        self.ensure_one()
        if self.state != 'approved':
            return False

        # Post all expenses
        for expense in self.expense_ids:
            if expense.state != 'approved':
                continue
            try:
                expense.action_post()
            except Exception as e:
                raise UserError(
                    _("Cannot post expense '%s': %s") % (expense.name, str(e))
                )

        # Update sheet state
        self.write({
            'state': 'posted',
            'date_post': fields.Date.today(),
        })

        return True

    def action_pay(self):
        """Register payment for all posted expenses."""
        self.ensure_one()
        if self.state != 'posted':
            return False

        # Pay all expenses
        for expense in self.expense_ids:
            if expense.state != 'posted':
                continue
            try:
                expense.action_pay()
            except Exception as e:
                raise UserError(
                    _("Cannot pay expense '%s': %s") % (expense.name, str(e))
                )

        # Update sheet state
        self.write({
            'state': 'paid',
            'date_paid': fields.Date.today(),
        })

        return True

    def action_reset_draft(self):
        """Reset the expense sheet to draft state."""
        for expense in self.expense_ids:
            if expense.state in ('approved', 'posted', 'paid'):
                # Need to reset expenses first
                expense.action_reset()

        self.write({'state': 'draft'})
        return True

    def action_view_expenses(self):
        """Open the expenses in the sheet."""
        self.ensure_one()
        return {
            'name': _('Expenses'),
            'view_mode': 'tree,form',
            'res_model': 'hr.expense',
            'domain': [('id', 'in', self.expense_ids.ids)],
            'type': 'ir.actions.act_window',
            'context': {'default_sheet_id': self.id},
        }

    def action_view_journal_entry(self):
        """Open the journal entry."""
        self.ensure_one()
        if not self.account_move_id:
            return False
        return {
            'name': _('Journal Entry'),
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.account_move_id.id,
            'type': 'ir.actions.act_window',
        }

    def action_view_payment(self):
        """Open the payment."""
        self.ensure_one()
        if not self.account_payment_id:
            return False
        return {
            'name': _('Payment'),
            'view_mode': 'form',
            'res_model': 'account.payment',
            'res_id': self.account_payment_id.id,
            'type': 'ir.actions.act_window',
        }

    # Button handlers for XML views
    def button_submit(self):
        return self.action_submit()

    def button_delete(self):
        # Delete all expenses in the sheet first
        for sheet in self:
            sheet.expense_ids.unlink()
            sheet.unlink()
        # Return action to redirect to list view
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.expense.sheet',
            'view_mode': 'list,form',
            'target': 'main',
        }

    def button_approve(self):
        return self.action_approve()

    def button_refuse(self):
        # This will be handled by a wizard in the UI
        return {
            'name': _('Refuse Expense Sheet'),
            'view_mode': 'form',
            'res_model': 'hr.expense.sheet.refuse.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'default_sheet_id': self.id},
        }

    def button_post(self):
        return self.action_post()

    def button_pay(self):
        return self.action_pay()

    def button_reset_draft(self):
        return self.action_reset_draft()
