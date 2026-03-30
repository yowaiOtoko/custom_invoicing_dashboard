from odoo import http
from odoo.exceptions import AccessDenied
from odoo.http import request


class InvoicingDashboardController(http.Controller):

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
