{
    'name': 'Custom Invoicing Dashboard',
    'version': '19.0.5.0.0',
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
        'views/export_comptable_actions.xml',
        'views/res_company_views.xml',
        'views/invoicing_dashboard_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_invoicing_dashboard/static/src/invoicing_dashboard.xml',
            'custom_invoicing_dashboard/static/src/invoicing_dashboard.js',
            'custom_invoicing_dashboard/static/src/export_comptable.xml',
            'custom_invoicing_dashboard/static/src/export_comptable.js',
        ],
    },
    'external_dependencies': {
        'python': ['xlsxwriter'],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'auto_install': False,
    'application': False,
    'sequence': 1,
}
