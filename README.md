# Custom Invoicing Dashboard

Odoo 19 backend dashboard module focused on invoicing and quotations.

## Features

- Dashboard action for internal users
- KPI cards for revenue, unpaid invoices, and draft quotations
- Quick actions to create invoice and quotation
- Recent invoices and quotations tables
- Company settings shortcut button
- **Export comptable page**: export customer invoice journal entries in FEC, Sage, CSV, XLSX, or the invoice PDFs as a ZIP, for the current/previous year, year-to-date, last 6 months, a specific year, or a custom date range
- Post-init hook to set dashboard as home action for internal users

## Installation

1. Copy module into your custom addons path.
2. Update apps list in Odoo.
3. Install module: Custom Invoicing Dashboard.
4. Ensure dependencies are installed: base, account, sale, web. `xlsxwriter` (standard Odoo dependency) is required for the XLSX export.

## Usage

1. Open Invoicing Dashboard from the backend menu.
2. Use quick action buttons to create invoices and quotations.
3. Click row in recent tables to open document form view.
4. Use Company settings button when shown.
5. Click **Export comptable** to open the accounting export page, pick a period preset and a format, then click **Export**.

## Export comptable

The page exports **posted customer invoices and credit notes** (`out_invoice`/`out_refund`) of the selected period (accounting date), for all accessible companies. Supported formats:

- **FEC** (`*.txt`): DGFiP layout, 18 columns separated by `|`, UTF-8, invoice-scoped (not the full ledger).
- **Sage** (`*.txt`): line-coded exchange file (`100` = pièce, `110` = débit, `120` = crédit), `;` separator, comma decimal. The layout is isolated in `_sage_row()`/`generate_sage()` so it can be tuned to the accountant's Sage import profile.
- **CSV** (`*.csv`): journal lines, `;` separator, comma decimal, UTF-8 BOM (Excel-friendly).
- **XLSX** (`*.xlsx`): same data in a styled workbook.
- **PDF** (`*.zip`): a ZIP archive containing each invoice rendered as its standard PDF.
- **FEC + PDFs** (`*.zip`): a ZIP with the invoice-scoped **FEC** file plus each invoice PDF — the packaging used to hand journal entries and supporting invoices to an expert-comptable suite (Cegid, ACD, RCA and Isacompta all ingest FEC).
- **Pennylane** (`*.csv`): journal lines matching Pennylane's documented import template (`Date`, `Numéro de pièce`, `Libellé`, `Numéro de compte`, `Code journal`, `Débit`, `Crédit`, `TVA`, `Code pays`, `Devise`), `;` separator, comma decimal, UTF-8 BOM.

## Permissions needed

Users should be internal users with access to:

- Invoicing app data
- Sales app data
- Company settings (only for users allowed to edit company data)
- The Export comptable page is available to the same accounting groups as the dashboard (`account.group_account_invoice`, `account.group_account_readonly`)

## Notes

- Module designed for Odoo 19.
- Frontend uses Owl components loaded in web.assets_backend.
