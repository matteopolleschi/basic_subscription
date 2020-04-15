# -*- coding: utf-8 -*-
{
    'name': "Basic Subscription",

    'summary': """Manage Subscriptions""",

    'description': """
        Basic module to manage subscriptions.
        Features:
            - Create and modify subscriptions
    """,

    'author': "Mounir Lahsini",
    'website': "https://github.com/matteopolleschi/basic_subscription",

    'category': 'Sales',
    'version': '1.0',
    'sequence': 1,

    'depends': ['base','mail','uom','account'],

    'data': [
        'security/basic_subscription_security.xml',
        'security/ir.model.access.csv',
        'views/basic_subscription_views.xml',
        'data/basic_subscription_stage_data.xml',
    ],

    'demo': [
        'data/basic_subscription_demo.xml',
    ],
    
    'application': True,
}