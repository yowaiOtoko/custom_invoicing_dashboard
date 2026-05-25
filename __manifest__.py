{
    'name': 'Custom Invoicing Dashboard',
    'version': '19.0.2.0.3',
    'category': 'Accounting',
    'author': 'yowaiOtoko',
    'website': 'https://invo-facturation.fr',
    'summary': 'Minimal invoicing and quotations dashboard',
    'description': 'Backend dashboard for invoicing and quotations with KPI cards, quick actions, and recent documents.',
    'license': 'LGPL-3',
    'depends': ['base', 'account', 'sale', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/dashboard_window_actions.xml',
        'views/res_company_views.xml',
        'views/invoicing_dashboard_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_invoicing_dashboard/static/src/invoicing_dashboard.xml',
            'custom_invoicing_dashboard/static/src/invoicing_dashboard.js',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'auto_install': False,
    'application': False,
    'sequence': 1,
}
