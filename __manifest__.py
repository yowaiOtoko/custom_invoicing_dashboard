{
    'name': 'Custom Invoicing Dashboard',
    'version': '19.0.2.0.0',
    'category': 'Accounting',
    'summary': 'Minimal invoicing and quotations dashboard',
    'license': 'LGPL-3',
    'depends': ['account', 'sale', 'web'],
    'data': [
        'security/ir.model.access.csv',
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
    'application': False,
}
