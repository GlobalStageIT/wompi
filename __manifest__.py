{
    'name': 'Wompi Payment Acquirer',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 380,
    'author': "Jose Moreno, javibits",
    'summary': 'Payment Acquirer: Wompi Bancolombia Implementation',
    'description': """Wompi payment acquirer""",
    'version': '1.0',
    'category': 'Invoicing',
    'license': 'AGPL-3',
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_wompi_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'payment_wompi/static/src/js/payment_form.js',
        ],
    },
    'images': ['static/description/icon.png'],
    'application': True,
    'installable': True,
    'uninstall_hook': 'uninstall_hook',
    'currency': 'USD',
    'price': 120.00,
}
