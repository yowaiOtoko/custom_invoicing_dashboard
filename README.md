# Custom Invoicing Dashboard

Odoo 19 backend dashboard module focused on invoicing and quotations.

## Features

- Dashboard action for internal users
- KPI cards for revenue, unpaid invoices, and draft quotations
- Quick actions to create invoice and quotation
- Recent invoices and quotations tables
- Company settings shortcut button
- Post-init hook to set dashboard as home action for internal users

## Installation

1. Copy module into your custom addons path.
2. Update apps list in Odoo.
3. Install module: Custom Invoicing Dashboard.
4. Ensure dependencies are installed: base, account, sale, web.

## Usage

1. Open Invoicing Dashboard from the backend menu.
2. Use quick action buttons to create invoices and quotations.
3. Click row in recent tables to open document form view.
4. Use Company settings button when shown.

## Permissions needed

Users should be internal users with access to:

- Invoicing app data
- Sales app data
- Company settings (only for users allowed to edit company data)

## Notes

- Module designed for Odoo 19.
- Frontend uses Owl components loaded in web.assets_backend.
