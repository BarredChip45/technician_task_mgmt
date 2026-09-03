from odoo import api, fields, models, _
from odoo.exceptions import UserError
from ..models.tt_task import get_geoip_response


class TTTaskStartWizard(models.TransientModel):
    _name = 'tt.task.start.wizard'
    _description = 'Start Technician Task Wizard'

    task_id = fields.Many2one(
        'tt.task',
        string='Task',
        required=True,
        readonly=True,
        default=lambda self: self._default_task(),
    )

    @api.model
    def _default_task(self):
        active_id = self.env.context.get('active_id')
        if not active_id:
            return False
        task = self.env['tt.task'].browse(active_id)
        return task.id if task.exists() else False

    def action_confirm_with_location(self):
        """Confirm start with geolocation - will be intercepted by JavaScript"""
        return self.action_confirm()

    def action_confirm(self):
        self.ensure_one()
        task = self.task_id
        if not task:
            raise UserError(_('No task found to start.'))

        # Check if geolocation was provided in context
        start_lat = self.env.context.get('start_latitude')
        start_lng = self.env.context.get('start_longitude')

        if start_lat and start_lng:
            # Use context with geolocation
            task.with_context(start_latitude=start_lat, start_longitude=start_lng).action_start()
        else:
            # Fallback without geolocation
            task.action_start()

        return {'type': 'ir.actions.act_window_close'}

    def start_with_location_rpc(self, latitude=False, longitude=False):
        """RPC method called by JavaScript to start task with optional geolocation"""
        self.ensure_one()
        task = self.task_id

        if not task:
            return {'success': False, 'error': 'No task found'}

        try:
            # Call the task's start method with location
            result = task.start_with_location_rpc(latitude=latitude, longitude=longitude)
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}