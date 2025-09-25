from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    tt_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Default Warehouse for Technician Tasks',
        config_parameter='technician_task_mgmt.tt_warehouse_id'
    )
    tt_src_location_id = fields.Many2one(
        'stock.location',
        string='Source Location for Technician Materials',
        config_parameter='technician_task_mgmt.tt_src_location_id'
    )
    tt_dest_location_id = fields.Many2one(
        'stock.location',
        string='Destination Location for Technician Consumption',
        config_parameter='technician_task_mgmt.tt_dest_location_id'
    )
    tt_timesheet_project_id = fields.Many2one(
        'project.project',
        string='Timesheet Project for Technician Tasks',
        config_parameter='technician_task_mgmt.tt_timesheet_project_id',
        help='Project used when logging time from technician task timers.'
    )
