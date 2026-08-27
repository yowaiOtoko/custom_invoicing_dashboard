# -*- coding: utf-8 -*-
# Copyright (C) 2026 yowaiOtoko
# License LGPL-3 or later (https://www.gnu.org/licenses/lgpl.html)

import csv
import io
import re
import zipfile
from io import BytesIO

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class CustomInvoicingAccountingExport(models.AbstractModel):
    _name = 'custom_invoicing_dashboard.accounting_export'
    _description = 'Accounting export (customer invoices)'

    # FEC layout, see DGFiP spec / l10n_fr_account wizard
    FEC_HEADER = [
        'JournalCode', 'JournalLib', 'EcritureNum', 'EcritureDate',
        'CompteNum', 'CompteLib', 'CompAuxNum', 'CompAuxLib',
        'PieceRef', 'PieceDate', 'EcritureLib', 'Debit', 'Credit',
        'EcritureLet', 'DateLet', 'ValidDate', 'Montantdevise', 'Idevise',
    ]

    CSV_HEADER = [
        'Journal', 'Date', 'Pièce', 'Référence', 'Tiers', 'Compte',
        'Libellé', 'Débit', 'Crédit', 'Échéance', 'TVA',
    ]

    # Pennylane journal-entry import template (help.pennylane.com "Importer des
    # écritures"): Date, Numéro de compte, Débit/Crédit are mandatory; the rest
    # are optional. Journal code must be letters only, max 5 chars.
    PENNYLANE_HEADER = [
        'Date', 'Numéro de pièce', 'Libellé', 'Numéro de compte',
        'Code journal', 'Débit', 'Crédit', 'TVA', 'Code pays', 'Devise',
    ]

    # ------- Access -------

    def _check_export_access(self):
        user = self.env.user
        if user._is_public():
            raise AccessError(self.env._('You are not allowed to access this export.'))
        if not (
            user.has_group('account.group_account_invoice')
            or user.has_group('account.group_account_readonly')
        ):
            raise AccessError(self.env._('You are not allowed to access this export.'))

    def _company_domain(self):
        return [('company_id', 'in', self.env.companies.ids)]

    def _move_domain(self, date_from, date_to):
        return self._company_domain() + [
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]

    # ------- Page data -------

    @api.model
    def get_page_data(self):
        self._check_export_access()
        Move = self.env['account.move']
        domain = self._company_domain() + [
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('state', '=', 'posted'),
        ]
        moves = Move.search(domain)
        years = sorted({d.year for d in moves.mapped('invoice_date') if d})
        return {
            'years': years,
            'invoice_count': len(moves),
        }

    @api.model
    def count_moves(self, date_from, date_to):
        self._check_export_access()
        date_from = fields.Date.to_date(date_from)
        date_to = fields.Date.to_date(date_to)
        if not date_from or not date_to:
            raise UserError(self.env._('Both start and end dates are required.'))
        if date_from > date_to:
            raise UserError(self.env._('The start date must be before the end date.'))
        return self.env['account.move'].search_count(self._move_domain(date_from, date_to))

    # ------- Helpers -------

    def _invoice_lines(self, date_from, date_to):
        moves = self.env['account.move'].search(
            self._move_domain(date_from, date_to),
            order='date, name',
        )
        return moves.line_ids.filtered(
            lambda line: line.display_type not in ('line_section', 'line_note')
        )

    @staticmethod
    def _sanitize(value):
        if not value:
            return ''
        return re.sub(r'[\t\r\n]', ' ', str(value).replace('|', '/')).strip()

    @staticmethod
    def _fmt_date_compact(value):
        return value.strftime('%Y%m%d') if value else ''

    @staticmethod
    def _fmt_date_fr(value):
        return value.strftime('%d/%m/%Y') if value else ''

    @staticmethod
    def _fmt_decimal(amount):
        return ('%.2f' % abs(amount or 0.0)).replace('.', ',')

    @staticmethod
    def _fmt_fec_amount(amount):
        amount = abs(amount or 0.0)
        if not amount:
            return '0,00'
        # 15 integer digits + decimal comma (mirrors DGFiP '000000000000000D99')
        return ('%018.2f' % amount).replace('.', ',')

    # ------- FEC (invoice-scoped) -------

    def _fec_line_vals(self, line):
        move = line.move_id
        partner = line.partner_id
        account = line.account_id
        is_aux = account.account_type in ('asset_receivable', 'liability_payable')
        ref = move.ref or '-'
        if line.name:
            label = line.name
        elif is_aux and partner:
            label = '%s - %s' % (partner.name or '', move.ref or move.name)
        else:
            label = move.ref or move.name
        full_reconcile = line.full_reconcile_id
        return [
            self._sanitize(move.journal_id.code),
            self._sanitize(move.journal_id.name),
            self._sanitize(move.name),
            self._fmt_date_compact(move.date),
            self._sanitize(account.code),
            self._sanitize(account.name),
            self._sanitize(partner.ref) if is_aux and partner and partner.ref
            else (str(partner.id) if is_aux and partner else ''),
            self._sanitize(partner.name) if is_aux and partner else '',
            self._sanitize(ref),
            self._fmt_date_compact(move.invoice_date or move.date),
            self._sanitize(label),
            self._fmt_fec_amount(line.debit),
            self._fmt_fec_amount(line.credit),
            str(full_reconcile.id) if full_reconcile else '',
            self._fmt_date_compact(full_reconcile.create_date.date()) if full_reconcile else '',
            self._fmt_date_compact(move.date),
            self._fmt_fec_amount(line.amount_currency) if line.amount_currency and line.currency_id else '',
            line.currency_id.name if line.currency_id else '',
        ]

    def generate_fec(self, date_from, date_to):
        self._check_export_access()
        date_from = fields.Date.to_date(date_from)
        date_to = fields.Date.to_date(date_to)
        lines = self._invoice_lines(date_from, date_to)
        out = io.StringIO()
        writer = csv.writer(out, delimiter='|', lineterminator='\r\n')
        writer.writerow(self.FEC_HEADER)
        for line in lines:
            writer.writerow(self._fec_line_vals(line))
        return out.getvalue().encode('utf-8')

    # ------- Sage 'Ligne' (delimited, line-coded) -------
    # 100 = en-tête de pièce, 110 = ligne débit, 120 = ligne crédit.
    # Layout isolated here so it can be tuned to the accountant's Sage
    # import profile without touching the rest of the module.

    def _sage_row(self, *values):
        return ';'.join('' if v is None else str(v) for v in values)

    def generate_sage(self, date_from, date_to):
        self._check_export_access()
        date_from = fields.Date.to_date(date_from)
        date_to = fields.Date.to_date(date_to)
        moves = self.env['account.move'].search(
            self._move_domain(date_from, date_to),
            order='date, name',
        )
        rows = []
        for move in moves:
            move_label = self._sanitize(move.ref or move.name)
            rows.append(self._sage_row(
                '100',
                self._fmt_date_fr(move.date),
                self._sanitize(move.name),
                move_label,
                self._sanitize(move.journal_id.code),
            ))
            for line in move.line_ids.filtered(
                lambda l: l.display_type not in ('line_section', 'line_note')
            ):
                partner = line.partner_id
                code = '110' if line.debit else '120'
                amount = line.debit or line.credit
                rows.append(self._sage_row(
                    code,
                    self._sanitize(line.account_id.code),
                    self._sanitize(line.name or move_label),
                    self._fmt_decimal(amount),
                    self._sanitize(partner.name) if partner else '',
                ))
        return ('\r\n'.join(rows) + ('\r\n' if rows else '')).encode('utf-8')

    # ------- CSV / XLSX (journal lines) -------

    def _csv_line_vals(self, line):
        move = line.move_id
        partner = line.partner_id
        taxes = line.tax_ids
        return {
            'Journal': self._sanitize(move.journal_id.code or move.journal_id.name),
            'Date': self._fmt_date_fr(move.date),
            'Pièce': self._sanitize(move.name),
            'Référence': self._sanitize(move.ref),
            'Tiers': self._sanitize(partner.name) if partner else '',
            'Compte': self._sanitize(line.account_id.code),
            'Libellé': self._sanitize(line.name),
            'Débit': self._fmt_decimal(line.debit),
            'Crédit': self._fmt_decimal(line.credit),
            'Échéance': self._fmt_date_fr(line.date_maturity),
            'TVA': self._sanitize(', '.join(taxes.mapped('name'))) if taxes else '',
        }

    def generate_csv(self, date_from, date_to):
        self._check_export_access()
        date_from = fields.Date.to_date(date_from)
        date_to = fields.Date.to_date(date_to)
        lines = self._invoice_lines(date_from, date_to)
        out = io.StringIO()
        writer = csv.DictWriter(
            out, fieldnames=self.CSV_HEADER, delimiter=';', lineterminator='\r\n',
        )
        writer.writeheader()
        for line in lines:
            writer.writerow(self._csv_line_vals(line))
        # UTF-8 BOM so MS Excel (fr) opens accents correctly.
        return b'\xef\xbb\xbf' + out.getvalue().encode('utf-8')

    def generate_xlsx(self, date_from, date_to):
        self._check_export_access()
        if xlsxwriter is None:
            raise UserError(
                self.env._("The 'xlsxwriter' Python library is required for the XLSX export.")
            )
        date_from = fields.Date.to_date(date_from)
        date_to = fields.Date.to_date(date_to)
        lines = self._invoice_lines(date_from, date_to)
        buf = BytesIO()
        workbook = xlsxwriter.Workbook(buf, {'in_memory': True})
        sheet = workbook.add_worksheet('Export comptable')
        header_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#635bff', 'font_color': '#ffffff', 'border': 1,
        })
        date_fmt = workbook.add_format({'num_format': 'dd/mm/yyyy'})
        money_fmt = workbook.add_format({'num_format': '#,##0.00'})
        widths = {
            'Journal': 10, 'Date': 12, 'Pièce': 16, 'Référence': 16, 'Tiers': 30,
            'Compte': 12, 'Libellé': 40, 'Débit': 14, 'Crédit': 14, 'Échéance': 12, 'TVA': 20,
        }
        for col, header in enumerate(self.CSV_HEADER):
            sheet.write(0, col, header, header_fmt)
            sheet.set_column(col, col, widths[header])
        row = 1
        for line in lines:
            for col, header in enumerate(self.CSV_HEADER):
                if header == 'Date':
                    if line.move_id.date:
                        sheet.write_datetime(row, col, line.move_id.date, date_fmt)
                elif header == 'Échéance':
                    if line.date_maturity:
                        sheet.write_datetime(row, col, line.date_maturity, date_fmt)
                elif header == 'Débit':
                    sheet.write_number(row, col, line.debit, money_fmt)
                elif header == 'Crédit':
                    sheet.write_number(row, col, line.credit, money_fmt)
                else:
                    sheet.write(row, col, self._csv_line_vals(line)[header])
            row += 1
        workbook.close()
        return buf.getvalue()

    # ------- Pennylane (CSV, documented import template) -------

    @staticmethod
    def _pennylane_journal_code(move):
        code = re.sub(r'[^A-Za-z]', '', move.journal_id.code or '').upper()
        return code[:5]

    def _pennylane_line_vals(self, line):
        move = line.move_id
        return {
            'Date': self._fmt_date_fr(move.date),
            'Numéro de pièce': self._sanitize(move.name),
            'Libellé': self._sanitize(line.name or move.ref or move.name),
            'Numéro de compte': self._sanitize(line.account_id.code),
            'Code journal': self._pennylane_journal_code(move),
            'Débit': self._fmt_decimal(line.debit),
            'Crédit': self._fmt_decimal(line.credit),
            'TVA': '',
            'Code pays': '',
            'Devise': line.currency_id.name if line.currency_id else '',
        }

    def generate_pennylane_csv(self, date_from, date_to):
        self._check_export_access()
        date_from = fields.Date.to_date(date_from)
        date_to = fields.Date.to_date(date_to)
        lines = self._invoice_lines(date_from, date_to)
        out = io.StringIO()
        writer = csv.DictWriter(
            out, fieldnames=self.PENNYLANE_HEADER,
            delimiter=';', lineterminator='\r\n',
        )
        writer.writeheader()
        for line in lines:
            writer.writerow(self._pennylane_line_vals(line))
        # UTF-8 BOM so MS Excel (fr) opens accents correctly.
        return b'\xef\xbb\xbf' + out.getvalue().encode('utf-8')

    # ------- PDF (individual invoice PDFs, zipped) -------

    def generate_pdf_zip(self, date_from, date_to):
        self._check_export_access()
        date_from = fields.Date.to_date(date_from)
        date_to = fields.Date.to_date(date_to)
        moves = self.env['account.move'].search(
            self._move_domain(date_from, date_to),
            order='date, name',
        )
        if not moves:
            raise UserError(self.env._('No invoice in the selected period.'))
        buf = BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for move in moves:
                pdf = self.env['ir.actions.report']._render_qweb_pdf(
                    'account.account_invoices', move.ids
                )[0]
                base = move._get_report_base_filename() or move.name
                filename = re.sub(r'[/\\:]+', '_', base) + '.pdf'
                zf.writestr(filename, pdf)
        return buf.getvalue()

    # ------- Cabinet softwares (FEC + invoice PDFs, zipped) -------
    # Expert-comptable suites (Cegid, ACD, RCA, Isacompta, ...) all ingest the
    # universal FEC standard (Cegid Loop and Isacompta document native FEC
    # import; ACD imports FEC + images; RCA interfaces standard formats).
    # iPaidThat ships such exports as "FEC + invoice images" in a ZIP - that is
    # exactly what we produce here. A single button covers them all.

    def generate_fec_pdf_zip(self, date_from, date_to):
        self._check_export_access()
        date_from = fields.Date.to_date(date_from)
        date_to = fields.Date.to_date(date_to)
        moves = self.env['account.move'].search(
            self._move_domain(date_from, date_to),
            order='date, name',
        )
        if not moves:
            raise UserError(self.env._('No invoice in the selected period.'))
        buf = BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            fec_name = 'FEC_%s_%s.txt' % (
                date_from.strftime('%Y%m%d'), date_to.strftime('%Y%m%d')
            )
            zf.writestr(fec_name, self.generate_fec(date_from, date_to))
            for move in moves:
                pdf = self.env['ir.actions.report']._render_qweb_pdf(
                    'account.account_invoices', move.ids
                )[0]
                base = move._get_report_base_filename() or move.name
                filename = re.sub(r'[/\\:]+', '_', base) + '.pdf'
                zf.writestr(filename, pdf)
        return buf.getvalue()

    # ------- Dispatch -------

    def _prepare_file(self, fmt, date_from, date_to):
        self._check_export_access()
        date_from = fields.Date.to_date(date_from)
        date_to = fields.Date.to_date(date_to)
        if not date_from or not date_to:
            raise UserError(self.env._('Both start and end dates are required.'))
        if date_from > date_to:
            raise UserError(self.env._('The start date must be before the end date.'))
        period = '%s_%s' % (date_from.strftime('%Y%m%d'), date_to.strftime('%Y%m%d'))
        if fmt == 'fec':
            data = self.generate_fec(date_from, date_to)
            filename = 'FEC_%s.txt' % period
            mimetype = 'text/plain; charset=utf-8'
        elif fmt == 'sage':
            data = self.generate_sage(date_from, date_to)
            filename = 'SAGE_%s.txt' % period
            mimetype = 'text/plain; charset=utf-8'
        elif fmt == 'csv':
            data = self.generate_csv(date_from, date_to)
            filename = 'export_comptable_%s.csv' % period
            mimetype = 'text/csv; charset=utf-8'
        elif fmt == 'xlsx':
            data = self.generate_xlsx(date_from, date_to)
            filename = 'export_comptable_%s.xlsx' % period
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif fmt == 'pdf':
            data = self.generate_pdf_zip(date_from, date_to)
            filename = 'factures_%s.zip' % period
            mimetype = 'application/zip'
        elif fmt == 'fecpdf':
            data = self.generate_fec_pdf_zip(date_from, date_to)
            filename = 'fec_factures_%s.zip' % period
            mimetype = 'application/zip'
        elif fmt == 'pennylane':
            data = self.generate_pennylane_csv(date_from, date_to)
            filename = 'pennylane_%s.csv' % period
            mimetype = 'text/csv; charset=utf-8'
        else:
            raise UserError(self.env._('Unknown export format.'))
        return data, filename, mimetype
