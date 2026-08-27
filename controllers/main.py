from odoo import http
from odoo.exceptions import AccessDenied, AccessError, UserError
from odoo.http import request


class InvoicingDashboardController(http.Controller):

    _EXPORT_FORMATS = (
        'fec', 'sage', 'csv', 'xlsx', 'pdf', 'fecpdf', 'pennylane',
    )

    def _check_dashboard_access(self):
        user = request.env.user
        if user._is_public():
            raise AccessDenied()
        if not (
            user.has_group('account.group_account_invoice')
            or user.has_group('account.group_account_readonly')
        ):
            raise AccessDenied()

    @http.route('/custom/dashboard', type='http', auth='user')
    def invoicing_dashboard(self, **kwargs):
        try:
            self._check_dashboard_access()
        except AccessDenied:
            return request.make_response('Forbidden', status=403)
        action = request.env.ref('custom_invoicing_dashboard.action_invoicing_dashboard')
        cids = ','.join(str(cid) for cid in request.env.companies.ids)
        return request.redirect('/web#action=%s&cids=%s' % (action.id, cids))

    @http.route('/custom/export/comptable/<string:fmt>', type='http', auth='user')
    def export_comptable(self, fmt, date_from=None, date_to=None, **kwargs):
        try:
            self._check_dashboard_access()
        except AccessDenied:
            return request.make_response('Forbidden', status=403)
        if fmt not in self._EXPORT_FORMATS:
            return request.make_response('Unknown export format', status=400)
        try:
            data, filename, mimetype = request.env[
                'custom_invoicing_dashboard.accounting_export'
            ]._prepare_file(fmt, date_from, date_to)
        except AccessError:
            return request.make_response('Forbidden', status=403)
        except UserError as exc:
            return request.make_response(str(exc), status=400)
        headers = [
            ('Content-Type', mimetype),
            ('Content-Disposition', 'attachment; filename="%s"' % filename),
        ]
        return request.make_response(data, headers=headers)
