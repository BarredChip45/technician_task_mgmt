{
    'name': 'Max Techniciens',
    'summary': 'Manage technician field tasks with timing and material consumption',
    'version': '18.0.1.0.0',
    'category': 'Technician Max',
    'author': 'Kenan Globalis',
    'website': 'https://example.com',
    'license': 'LGPL-3',
    'application': True,
    'installable': True,
    'depends': ['base', 'mail', 'hr', 'fleet', 'stock', 'product', 'uom', 'hr_timesheet'],
    'data': [
        'security/tt_security.xml',
        'security/ir.model.access.csv',
        'data/tt_task_type.xml',
        'data/tt_task_stage.xml',
        'views/tt_task_finish_wizard_views.xml',
        # Load config view before menus/actions that reference it
        'views/res_config_settings_views.xml',
        # Load task-related views
        'views/tt_task_views.xml',
        'views/tt_stage_views.xml',
        'views/tt_type_tag_views.xml',
        # Load menus/actions last
        'views/tt_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'technician_task_mgmt/static/src/js/**/*',
            'technician_task_mgmt/static/src/xml/**/*',
        ],
    },
}
