from odoo import api, fields, models, _
from odoo.exceptions import UserError
from ..models.tt_task import get_geoip_response


class TTTaskFinishWizard(models.TransientModel):
    _name = 'tt.task.finish.wizard'
    _description = 'Finish Technician Task Wizard'

    task_id = fields.Many2one(
        'tt.task',
        string='Task',
        required=True,
        readonly=True,
        default=lambda self: self._default_task(),
    )
    finish_option = fields.Selection(
        selection=[
            ('done', 'Fully Completed'),
            ('today', 'Finished for Today'),
        ],
        string='Outcome',
        default='done',
        required=True,
    )

    @api.model
    def _default_task(self):
        active_id = self.env.context.get('active_id')
        if not active_id:
            return False
        task = self.env['tt.task'].browse(active_id)
        return task.id if task.exists() else False

    def action_confirm(self):
        self.ensure_one()
        task = self.task_id
        if not task:
            raise UserError(_('No task found to finish.'))

        option = self.finish_option or 'done'

        # Check if geolocation was provided in context
        end_lat = self.env.context.get('end_latitude')
        end_lng = self.env.context.get('end_longitude')

        if end_lat and end_lng:
            # Use context with geolocation
            task.with_context(end_latitude=end_lat, end_longitude=end_lng).action_finish_with_option(option)
        else:
            # Use without geolocation
            task.action_finish_with_option(option)

        return {'type': 'ir.actions.act_window_close'}

    def update_task_location(self, latitude=False, longitude=False):
        """Update task location like hr_attendance update_last_position"""
        self.ensure_one()
        if self.task_id:
            geo_info = get_geoip_response(latitude=latitude, longitude=longitude)
            self.task_id.write({
                'end_latitude': geo_info.get('latitude'),
                'end_longitude': geo_info.get('longitude'),
                'end_city': geo_info.get('city'),
                'end_country_name': geo_info.get('country_name'),
                'end_ip_address': geo_info.get('ip_address'),
                'end_browser': geo_info.get('browser'),
            })
        return True

    def action_confirm_with_location(self, latitude=False, longitude=False):
        """RPC method called by JavaScript to confirm task with optional geolocation"""
        import logging
        _logger = logging.getLogger(__name__)

        try:
            self.ensure_one()
            _logger.info(f"action_confirm_with_location called with latitude={latitude}, longitude={longitude}")

            if not self.id:
                _logger.error("No wizard ID provided")
                return {'success': False, 'error': 'No wizard ID provided'}

            task = self.task_id
            if not task:
                _logger.error("No task found to finish")
                return {'success': False, 'error': 'No task found to finish.'}

            option = self.finish_option or 'done'
            _logger.info(f"Finishing task {task.id} with option {option}")

            task.with_context(end_latitude=latitude, end_longitude=longitude).action_finish_with_option(option)
            _logger.info("Task finished successfully")
            return {'success': True, 'action': {'type': 'ir.actions.act_window_close'}}

        except Exception as e:
            _logger.error(f"Error in action_confirm_with_location: {str(e)}")
            import traceback
            _logger.error(traceback.format_exc())
            return {'success': False, 'error': str(e)}
