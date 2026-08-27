# -*- coding: utf-8 -*-
# Copyright (C) 2026 yowaiOtoko
# License LGPL-3 or later (https://www.gnu.org/licenses/lgpl.html)

import io
import zipfile

from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestAccountingExport(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Guarantee the access check in the export model passes for the test user.
        cls.env.user.group_ids |= cls.env.ref('account.group_account_invoice')
        cls.export_model = cls.env['custom_invoicing_dashboard.accounting_export']

    def _make_invoice(self, date, amount=120.0, move_type='out_invoice'):
        return self.init_invoice(
            move_type,
            partner=self.partner_a,
            invoice_date=date,
            amounts=[amount],
            post=True,
        )

    def test_get_page_data_and_count(self):
        self._make_invoice('2026-03-15')
        data = self.export_model.get_page_data()
        self.assertIn(2026, data['years'])
        self.assertGreaterEqual(data['invoice_count'], 1)
        self.assertEqual(
            self.export_model.count_moves('2026-01-01', '2026-12-31'), 1
        )
        self.assertEqual(
            self.export_model.count_moves('2025-01-01', '2025-12-31'), 0
        )

    def test_fec_layout(self):
        self._make_invoice('2026-03-15', 120.0)
        data = self.export_model.generate_fec('2026-01-01', '2026-12-31')
        text = data.decode('utf-8')
        lines = [line for line in text.split('\r\n') if line]
        self.assertEqual(
            lines[0],
            'JournalCode|JournalLib|EcritureNum|EcritureDate|CompteNum|CompteLib'
            '|CompAuxNum|CompAuxLib|PieceRef|PieceDate|EcritureLib|Debit|Credit'
            '|EcritureLet|DateLet|ValidDate|Montantdevise|Idevise',
        )
        self.assertGreater(len(lines), 1)
        self.assertTrue(all(line.count('|') == 17 for line in lines[1:]))

    def test_fec_filters_period(self):
        self._make_invoice('2026-03-15', 120.0)
        self._make_invoice('2025-03-15', 50.0)
        text = self.export_model.generate_fec('2026-01-01', '2026-12-31').decode('utf-8')
        self.assertIn('20260315', text)
        self.assertNotIn('20250315', text)

    def test_fec_excludes_non_posted_and_bills(self):
        # a draft invoice must not be exported
        self.init_invoice(
            'out_invoice', partner=self.partner_a,
            invoice_date='2026-06-01', amounts=[10.0], post=False,
        )
        # a vendor bill must not be exported
        self._make_invoice('2026-06-02', 20.0, move_type='in_invoice')
        text = self.export_model.generate_fec('2026-01-01', '2026-12-31').decode('utf-8')
        self.assertNotIn('20260601', text)
        self.assertNotIn('20260602', text)

    def test_sage(self):
        self._make_invoice('2026-03-15', 120.0)
        text = self.export_model.generate_sage('2026-01-01', '2026-12-31').decode('utf-8')
        lines = [line for line in text.split('\r\n') if line]
        self.assertGreater(len(lines), 1)
        self.assertTrue(any(line.startswith('100;') for line in lines))
        self.assertTrue(
            any(line.startswith('110;') or line.startswith('120;') for line in lines)
        )

    def test_csv(self):
        self._make_invoice('2026-03-15', 120.0)
        data = self.export_model.generate_csv('2026-01-01', '2026-12-31')
        self.assertTrue(data.startswith(b'\xef\xbb\xbf'))
        text = data.decode('utf-8-sig')
        self.assertTrue(
            text.startswith(
                'Journal;Date;Pièce;Référence;Tiers;Compte;Libellé;Débit;Crédit;Échéance;TVA'
            )
        )
        self.assertGreater(text.count('\r\n'), 1)
        # empty values must not leak the string 'False'
        self.assertNotIn('False', text)

    def test_xlsx(self):
        self._make_invoice('2026-03-15', 120.0)
        data = self.export_model.generate_xlsx('2026-01-01', '2026-12-31')
        # xlsx files are zip archives
        self.assertTrue(data.startswith(b'PK'))

    def test_pdf_zip(self):
        self._make_invoice('2026-03-15', 120.0)
        data = self.export_model.generate_pdf_zip('2026-01-01', '2026-12-31')
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = zf.namelist()
            self.assertTrue(any(name.endswith('.pdf') for name in names))

    def test_pdf_zip_no_invoice_raises(self):
        with self.assertRaises(Exception):
            self.export_model.generate_pdf_zip('2026-01-01', '2026-12-31')

    def test_pennylane_csv(self):
        self._make_invoice('2026-03-15', 120.0)
        data = self.export_model.generate_pennylane_csv('2026-01-01', '2026-12-31')
        self.assertTrue(data.startswith(b'\xef\xbb\xbf'))
        text = data.decode('utf-8-sig')
        self.assertTrue(
            text.startswith(
                'Date;Numéro de pièce;Libellé;Numéro de compte;Code journal;Débit;Crédit;TVA;Code pays;Devise'
            )
        )
        self.assertNotIn('False', text)

    def test_fec_pdf_zip(self):
        self._make_invoice('2026-03-15', 120.0)
        data = self.export_model.generate_fec_pdf_zip('2026-01-01', '2026-12-31')
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = zf.namelist()
            self.assertTrue(any(n.startswith('FEC_') for n in names))
            self.assertTrue(any(n.endswith('.pdf') for n in names))

    def test_prepare_file_dispatch(self):
        self._make_invoice('2026-03-15', 120.0)
        for fmt, ext in (
            ('fec', '.txt'), ('sage', '.txt'), ('csv', '.csv'),
            ('xlsx', '.xlsx'), ('pdf', '.zip'),
            ('fecpdf', '.zip'), ('pennylane', '.csv'),
        ):
            data, filename, mimetype = self.export_model._prepare_file(
                fmt, '2026-01-01', '2026-12-31'
            )
            self.assertTrue(filename.endswith(ext))
            self.assertTrue(data)
            self.assertTrue(mimetype)
