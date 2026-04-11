from odoo import api, models
from odoo.exceptions import AccessError
from odoo.tools.misc import formatLang, format_date


class CustomInvoicingDashboard(models.AbstractModel):
    _name = 'custom_invoicing_dashboard.dashboard'
    _description = 'Invoicing dashboard data service'

    def _check_dashboard_access(self):
        user = self.env.user
        if user._is_public():
            raise AccessError(self.env._('You are not allowed to access this dashboard.'))
        if not (
            user.has_group('account.group_account_invoice')
            or user.has_group('account.group_account_readonly')
        ):
            raise AccessError(self.env._('You are not allowed to access this dashboard.'))

    def _company_domain(self):
        return [('company_id', 'in', self.env.companies.ids)]

    def _invoice_base_domain(self):
        return self._company_domain() + [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
        ]

    def _unpaid_payment_states(self):
        return ('not_paid', 'partial', 'in_payment', 'blocked')

    def _format_money(self, amount):
        return formatLang(
            self.env,
            amount,
            currency_obj=self.env.company.currency_id,
        )

    def _payment_state_label(self, state):
        env = self.env
        sel = env['account.move'].fields_get(['payment_state'])['payment_state'].get('selection') or []
        return dict(sel).get(state, state or '')

    def _sale_state_label(self, state):
        env = self.env
        sel = env['sale.order'].fields_get(['state'])['state'].get('selection') or []
        return dict(sel).get(state, state or '')

    @api.model
    def get_dashboard_data(self):
        self._check_dashboard_access()
        env = self.env
        Move = env['account.move']
        Order = env['sale.order']

        invoice_domain = self._invoice_base_domain()
        revenue_groups = Move.read_group(
            invoice_domain,
            ['amount_total_signed:sum'],
            [],
        )
        raw_sum = revenue_groups[0].get('amount_total_signed_sum') if revenue_groups else 0.0
        total_revenue = abs(raw_sum or 0.0)

        unpaid_domain = invoice_domain + [
            ('payment_state', 'in', self._unpaid_payment_states()),
        ]
        unpaid_count = Move.search_count(unpaid_domain)

        draft_quotes_domain = self._company_domain() + [
            ('state', '=', 'draft'),
        ]
        try:
            draft_quotes_count = Order.search_count(draft_quotes_domain)
        except AccessError:
            draft_quotes_count = 0

        recent_moves = Move.search(
            invoice_domain,
            limit=5,
            order='invoice_date desc, id desc',
        )
        recent_invoices = []
        for move in recent_moves:
            partner = move.partner_id
            recent_invoices.append({
                'id': move.id,
                'name': move.name or '',
                'partner_name': partner.display_name if partner else '',
                'date_label': format_date(env, move.invoice_date) if move.invoice_date else '',
                'amount_label': self._format_money(abs(move.amount_total_in_currency_signed or 0.0)),
                'state': move.payment_state,
                'state_label': self._payment_state_label(move.payment_state),
            })

        recent_orders = Order.browse()
        try:
            recent_orders = Order.search(
                self._company_domain() + [('state', 'in', ('draft', 'sent'))],
                limit=5,
                order='date_order desc, id desc',
            )
        except AccessError:
            recent_orders = Order.browse()
        recent_quotes = []
        for order in recent_orders:
            partner = order.partner_id
            recent_quotes.append({
                'id': order.id,
                'name': order.name or '',
                'partner_name': partner.display_name if partner else '',
                'date_label': format_date(env, order.date_order) if order.date_order else '',
                'amount_label': self._format_money(order.amount_total),
                'state': order.state,
                'state_label': self._sale_state_label(order.state),
            })

        invoice_action = env.ref('custom_invoicing_dashboard.action_invoice_out_form_create')
        quote_action = env.ref('custom_invoicing_dashboard.action_sale_order_quotation_form_create')
        show_company_settings = env.user.has_group('base.group_system')

        return {
            'total_revenue_label': self._format_money(total_revenue),
            'unpaid_count': unpaid_count,
            'draft_quotes_count': draft_quotes_count,
            'recent_invoices': recent_invoices,
            'recent_quotes': recent_quotes,
            'invoice_action_id': invoice_action.id,
            'quote_action_id': quote_action.id,
            'show_company_settings': show_company_settings,
        }

    @api.model
    def action_open_company_settings(self):
        self._check_dashboard_access()
        if not self.env.user.has_group('base.group_system'):
            raise AccessError(self.env._('Only administrators can open company settings.'))
        company = self.env.company
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Company'),
            'res_model': 'res.company',
            'res_id': company.id,
            'views': [[False, 'form']],
            'target': 'current',
        }
