# -*- coding: utf-8 -*-
{
    'name': 'Custom Maintenance Requests',
    'version': '18.0.1.0',
    'sequence': 0,
    'summary': 'Manage custom maintenance requests',
    'description': """
    Custom Maintenance Request Module
    =================================
    This module allows users to create and manage maintenance requests
    with custom equipment types and status tracking.""",
    'category': 'Maintenance',
    'author': 'Eng.Mathany Saad',
    'depends': ['base', 'maintenance','hr'],
    'data': [
        'security/maintenance_security.xml',
        'security/ir.model.access.csv',
        'views/maintenance_request_custom_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
