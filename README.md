# hr_expense_sheet - Expense Sheet Extension for Odoo

## Overview

This module extends Odoo's native HR Expense functionality with additional features for managing expense sheets.

## Features

### 1. Tax-Included Expense Calculation

**Problem:**
When creating an expense without a product, users often need to enter a total amount that already includes tax (common in Vietnam and other countries). However, Odoo's default behavior calculates tax on top of the base amount, not backward from the total.

**Solution:**
This module calculates tax backward from the total when:
- No product is selected (user enters amount directly)
- User enters `total_amount_currency` as the total including tax
- A tax is selected

**Example:**
- User enters: `total_amount_currency` = 500,000 VND (total including tax)
- User selects: 10% VAT
- System calculates:
  - Untaxed amount = 500,000 / 1.1 = 454,545 VND
  - Tax amount = 500,000 - 454,545 = 45,455 VND

### 2. Expense Sheet Management

- Submit expenses for approval
- Approve/Refuse expenses
- Post journal entries
- Register payments
- View all expenses in a sheet

## Installation

1. Copy this module to your Odoo addons directory
2. Update apps list
3. Search for "hr_expense_sheet" and install

## Usage

### Creating an Expense with Tax-Included Total

1. Go to **Expenses > Expense Sheets**
2. Create a new expense sheet
3. Add a new expense line
4. **Leave Product empty** (important!)
5. Enter the **Total (Currency)** amount (e.g., 500,000 VND)
6. Select a tax (e.g., 10% VAT)
7. The system automatically calculates:
   - **Tax Amount**: ~45,455 VND (calculated backward)
   - **Total**: 500,000 VND

### Multiple Taxes

The module supports multiple tax selection. The tax rate is calculated as the sum of all selected tax percentages:

- Example: 10% VAT + 5% other tax = 15% total rate
- Formula: `untaxed = total / 1.15`

## Technical Details

### Modified Files

1. **models/hr_expense.py**
   - Extended `hr.expense` model
   - Added `_compute_total_amount()` method for backward tax calculation
   - Added `_compute_total_amount_currency()` to preserve user input

2. **views/hr_expense_sheet_views.xml**
   - Added form view for expense line with:
     - Hidden currency fields: `currency_id`, `company_currency_id`, `is_multiple_currency`
     - User-editable `total_amount_currency` field
     - Readonly `tax_amount` and `total_amount` fields

### Key Methods

#### `_compute_total_amount()`

```python
@api.depends('total_amount_currency', 'tax_ids', 'currency_id', 'company_id')
def _compute_total_amount(self):
    """Calculate tax backward from tax-included total."""
    for expense in self:
        if not expense.product_id and expense.total_amount_currency and expense.tax_ids:
            tax_rate = sum(tax.amount for tax in expense.tax_ids) / 100.0
            if tax_rate > 0:
                total_excluded = expense.total_amount_currency / (1 + tax_rate)
                tax_amount = expense.total_amount_currency - total_excluded
                expense.tax_amount = tax_amount
                expense.untaxed_amount = total_excluded
            expense.total_amount = expense.total_amount_currency
```

#### `_compute_total_amount_currency()`

```python
@api.depends('quantity', 'price_unit', 'tax_ids', 'product_id')
def _compute_total_amount_currency(self):
    """Preserve user-entered total when no product is selected."""
    for expense in self:
        if not expense.product_id and expense.total_amount_currency:
            continue  # Don't recalculate - keep user's input
        super(HrExpense, expense)._compute_total_amount_currency()
```

### XML View Changes

```xml
<!-- Hidden currency fields -->
<field name="currency_id" invisible="1"/>
<field name="company_currency_id" invisible="1"/>
<field name="is_multiple_currency" invisible="1"/>

<!-- User enters total (including tax) -->
<field name="total_amount_currency" widget="monetary" options="{'currency_field': 'currency_id'}"/>

<!-- Tax selection -->
<field name="tax_ids" widget="many2many_tags"/>

<!-- Calculated values (readonly) -->
<field name="tax_amount" readonly="1"/>
<field name="total_amount" readonly="1" widget="monetary" options="{'currency_field': 'company_currency_id'}"/>
```

## Limitations

- **Simple percentage taxes only**: The backward calculation uses `total / (1 + tax_rate)` which works for single or multiple percentage taxes on the same base
- **Compound taxes**: Not fully supported (tax-on-tax scenarios)
- **Fixed amount taxes**: Not supported in backward calculation

## Compatibility

- Odoo 19.0
- PostgreSQL database

## License

See LICENSE file for full copyright and licensing details (Odoo MIT License).

## Author

Custom module for Vietnamese localization with tax-included expense handling.
