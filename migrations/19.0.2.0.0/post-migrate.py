def migrate(cr, installed_version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    action = env.ref(
        'custom_invoicing_dashboard.action_invoicing_dashboard',
        raise_if_not_found=False,
    )
    if not action:
        return
    users = env['res.users'].search([
        ('share', '=', False),
        ('action_id', '=', False),
    ])
    if users:
        users.write({'action_id': action.id})
