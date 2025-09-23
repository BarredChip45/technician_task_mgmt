from odoo import http
from odoo.http import request


class TechnicianTaskController(http.Controller):

    @http.route('/technician_task/start_with_location', type="json", auth="user")
    def start_task_with_location(self, task_id, latitude=False, longitude=False):
        """Start a task with geolocation data"""
        try:
            task = request.env['tt.task'].browse(task_id)
            if task.exists():
                # Pass location data via context
                task.with_context(start_latitude=latitude, start_longitude=longitude).action_start()
                return {'success': True}
            return {'success': False, 'error': 'Task not found'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/technician_task/finish_with_location', type="json", auth="user")
    def finish_task_with_location(self, task_id, option='done', latitude=False, longitude=False):
        """Finish a task with geolocation data"""
        try:
            task = request.env['tt.task'].browse(task_id)
            if task.exists():
                # Pass location data via context
                task.with_context(end_latitude=latitude, end_longitude=longitude).action_finish_with_option(option)
                return {'success': True}
            return {'success': False, 'error': 'Task not found'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/technician_task/wizard_finish_with_location', type="json", auth="user")
    def wizard_finish_with_location(self, wizard_id, latitude=False, longitude=False):
        """Confirm wizard finish with geolocation data"""
        try:
            wizard = request.env['tt.task.finish.wizard'].browse(wizard_id)
            if wizard.exists():
                task = wizard.task_id
                option = wizard.finish_option
                # Pass location data via context
                result = task.with_context(end_latitude=latitude, end_longitude=longitude).action_finish_with_option(option)
                return {'success': True, 'result': result}
            return {'success': False, 'error': 'Wizard not found'}
        except Exception as e:
            return {'success': False, 'error': str(e)}