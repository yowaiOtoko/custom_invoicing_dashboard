from odoo import api, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals_list):
        action = self.env.ref(
            'custom_invoicing_dashboard.action_invoicing_dashboard',
            raise_if_not_found=False,
        )
        if action:
            for vals in vals_list:
                if vals.get('share'):
                    continue
                if 'action_id' in vals:
                    continue
                vals['action_id'] = action.id
        return super().create(vals_list)
