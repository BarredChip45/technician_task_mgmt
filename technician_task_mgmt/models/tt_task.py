from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

def get_google_maps_url(latitude, longitude):
    return "https://maps.google.com?q=%s,%s" % (latitude, longitude)

def get_geoip_response(latitude=False, longitude=False):
    """Get geolocation information prioritizing passed coordinates over IP-based location"""
    result = {
        'city': 'Unknown',
        'country_name': 'Unknown',
        'latitude': latitude or False,
        'longitude': longitude or False,
        'ip_address': 'Unknown',
        'browser': 'Unknown',
    }

    # If coordinates are provided, use them directly
    if latitude and longitude:
        result['latitude'] = latitude
        result['longitude'] = longitude
        # Still try to get other info from request if available
        try:
            from odoo.http import request
            if request and hasattr(request, 'geoip'):
                result['city'] = getattr(request.geoip.city, 'name', 'Unknown') or 'Unknown'
                result['country_name'] = (getattr(request.geoip.country, 'name', None) or
                                        getattr(request.geoip.continent, 'name', None) or 'Unknown')
                result['ip_address'] = getattr(request.geoip, 'ip', 'Unknown')
                if hasattr(request, 'httprequest') and hasattr(request.httprequest, 'user_agent'):
                    result['browser'] = getattr(request.httprequest.user_agent, 'browser', 'Unknown')
        except (ImportError, RuntimeError, AttributeError):
            pass
        return result

    # Fallback to IP-based geolocation if no coordinates provided
    try:
        from odoo.http import request
        if not request or not hasattr(request, 'geoip'):
            return result

        result.update({
            'city': getattr(request.geoip.city, 'name', 'Unknown') or 'Unknown',
            'country_name': (getattr(request.geoip.country, 'name', None) or
                           getattr(request.geoip.continent, 'name', None) or 'Unknown'),
            'latitude': getattr(request.geoip.location, 'latitude', False) or False,
            'longitude': getattr(request.geoip.location, 'longitude', False) or False,
            'ip_address': getattr(request.geoip, 'ip', 'Unknown'),
        })

        if hasattr(request, 'httprequest') and hasattr(request.httprequest, 'user_agent'):
            result['browser'] = getattr(request.httprequest.user_agent, 'browser', 'Unknown')

    except (ImportError, RuntimeError, AttributeError):
        # Request not available or no geoip data - return defaults
        pass

    return result


class TTTaskStage(models.Model):
    _name = 'tt.task.stage'
    _description = 'Technician Task Stage'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    fold = fields.Boolean(string=_('Folded in Kanban'))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], default='draft', required=True)


class TTTaskType(models.Model):
    _name = 'tt.task.type'
    _description = 'Technician Task Type'

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)


class TTTaskTag(models.Model):
    _name = 'tt.task.tag'
    _description = 'Technician Task Tag'

    name = fields.Char(required=True, translate=True)
    color = fields.Integer(string=_('Color'))
    active = fields.Boolean(default=True)


class TTBuildingTag(models.Model):
    _name = 'tt.building.tag'
    _description = 'Technician Building Tag'

    name = fields.Char(required=True, translate=True)
    color = fields.Integer(string=_('Color'))
    active = fields.Boolean(default=True)


class TTSubTask(models.Model):
    _name = 'tt.subtask'
    _description = 'Technician Sub-task'
    _order = 'sequence, id'

    task_id = fields.Many2one('tt.task', required=True, ondelete='cascade')
    name = fields.Char(required=True)
    is_done = fields.Boolean(default=False)
    sequence = fields.Integer(default=10)


class TTMaterialLine(models.Model):
    _name = 'tt.material.line'
    _description = 'Technician Task Material Line'

    task_id = fields.Many2one('tt.task', required=True, ondelete='cascade')
    product_id = fields.Many2one(
        'product.product', required=True,
        domain="[('type','in',('consu','product'))]"
    )
    product_uom_id = fields.Many2one('uom.uom', required=True)
    quantity = fields.Float(required=True, default=1.0)
    description = fields.Char()

    @api.constrains('quantity')
    def _check_quantity_positive(self):
        for rec in self:
            if rec.quantity <= 0:
                raise ValidationError(_('Quantity must be greater than zero.'))

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for rec in self:
            if rec.product_id:
                rec.product_uom_id = rec.product_id.uom_id


class TTTimerLine(models.Model):
    _name = 'tt.timer.line'
    _description = 'Technician Task Timer Line'
    _order = 'start_datetime desc, id desc'

    task_id = fields.Many2one('tt.task', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', required=True)
    start_datetime = fields.Datetime(required=True)
    end_datetime = fields.Datetime()
    timesheet_line_id = fields.Many2one(
        'account.analytic.line', string=_('Timesheet Entry'), readonly=True, copy=False
    )
    duration_hours = fields.Float(
        string=_('Duration (hours)'), compute='_compute_duration', store=True
    )
    pause_duration_seconds = fields.Integer(
        string=_('Paused Seconds'), default=0, copy=False
    )

    @api.depends('start_datetime', 'end_datetime', 'pause_duration_seconds')
    def _compute_duration(self):
        for rec in self:
            duration = 0.0
            if rec.start_datetime and rec.end_datetime:
                # On modern Odoo versions, these are datetime objects already
                delta = rec.end_datetime - rec.start_datetime
                paused = rec.pause_duration_seconds or 0
                total_seconds = max(delta.total_seconds() - paused, 0.0)
                duration = total_seconds / 3600.0
            rec.duration_hours = duration
    def _create_timesheet_entry(self):
        """Create an hr_timesheet entry from this timer line when possible."""
        AnalyticLine = self.env['account.analytic.line'].with_context(default_task_id=False)
        for line in self:
            if not line.end_datetime:
                continue
            start = line.start_datetime
            if not start:
                continue
            duration = line.duration_hours
            if not duration:
                delta = line.end_datetime - start
                duration = delta.total_seconds() / 3600.0 if delta else 0.0
            if duration <= 0:
                continue
            task = line.task_id
            project = task._get_timesheet_project()
            if not project:
                raise UserError(_('Please configure a timesheet project in Technician Task settings before stopping the timer.'))
            analytic_account = getattr(project, 'analytic_account_id', False)
            if not analytic_account:
                analytic_account = self._ensure_project_analytic_account(project)
            if not analytic_account:
                raise UserError(_('Project %s has no analytic account for timesheet entries.') % project.display_name)
            employee = line.employee_id
            if not employee:
                raise UserError(_('Timer line is missing an employee.'))
            employee_name = employee.name or employee.display_name or ''
            description = '%s - %s' % (task.name, employee_name) if employee_name else task.name
            entry_vals = {
                'name': description,
                'employee_id': employee.id,
                'user_id': employee.user_id.id if employee.user_id else False,
                'project_id': project.id,
                'account_id': analytic_account.id,
                'unit_amount': duration,
                'date': fields.Date.context_today(line, timestamp=line.end_datetime),
                'company_id': employee.company_id.id or analytic_account.company_id.id or line.env.company.id,
                'amount': 0.0,
                'task_id': False,
            }
            if line.timesheet_line_id:
                line.timesheet_line_id.write(entry_vals)
            else:
                timesheet = AnalyticLine.create(entry_vals)
                line.timesheet_line_id = timesheet.id
        return True

    def _get_default_analytic_plan(self, company):
        Plan = self.env['account.analytic.plan'].sudo()
        company_plan = getattr(company, 'analytic_plan_id', False) if company else False
        if company_plan:
            return company_plan
        plan = False
        if company:
            if 'company_id' in Plan._fields:
                plan = Plan.search([('company_id', '=', company.id)], limit=1)
            elif 'company_ids' in Plan._fields:
                plan = Plan.search([('company_ids', 'in', company.id)], limit=1)
            if plan:
                return plan
        domain = []
        if 'company_id' in Plan._fields:
            domain = [('company_id', '=', False)]
        plan = Plan.search(domain, limit=1) if domain else Plan.search([], limit=1)
        return plan

    def _ensure_project_analytic_account(self, project):
        project = project.sudo() if hasattr(project, 'sudo') else project
        analytic_account = getattr(project, 'analytic_account_id', False)
        if analytic_account:
            return analytic_account
        create_method = getattr(project, '_get_or_create_analytic_account', None)
        if callable(create_method):
            create_method()
            analytic_account = getattr(project, 'analytic_account_id', False)
            if analytic_account:
                return analytic_account
        company = getattr(project, 'company_id', False) or self.env.company
        plan = getattr(project, 'plan_id', False)
        if plan and hasattr(plan, 'id'):
            plan = plan
        elif plan:
            plan = self.env['account.analytic.plan'].browse(plan)
        else:
            plan = self._get_default_analytic_plan(company)
        if not plan:
            company_name = company.display_name if company and hasattr(company, 'display_name') else (company.name if company else self.env.company.display_name)
            raise UserError(_('Please configure an analytic plan for company %s before logging timesheets.') % company_name)
        vals = {
            'name': project.display_name or getattr(project, 'name', False) or _('Technician Timesheet %s') % project.id,
            'company_id': company.id if company else False,
            'plan_id': plan.id if hasattr(plan, 'id') else plan,
        }
        partner = getattr(project, 'partner_id', False)
        if partner:
            vals['partner_id'] = partner.id
        AnalyticAccount = self.env['account.analytic.account'].sudo()
        analytic_account = AnalyticAccount.create(vals)
        if hasattr(project, 'write'):
            update_vals = {}
            if 'analytic_account_id' in project._fields:
                update_vals['analytic_account_id'] = analytic_account.id
            elif 'analytic_account_ids' in project._fields:
                update_vals['analytic_account_ids'] = [(4, analytic_account.id)]
            if update_vals:
                project.sudo().write(update_vals)
        return analytic_account

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines:
            if line.end_datetime:
                line._create_timesheet_entry()
        return lines

    def write(self, vals):
        end_datetime_updated = 'end_datetime' in vals
        res = super().write(vals)
        if end_datetime_updated:
            for line in self:
                if line.end_datetime:
                    line._create_timesheet_entry()
        return res



class TTTask(models.Model):
    _name = 'tt.task'
    _description = 'Technician Task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'scheduled_date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(required=True, tracking=True)
    ticket_number = fields.Char(string=_('Ticket Number'), tracking=True)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True,
                                  default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1).id)
    task_type_id = fields.Many2one('tt.task.type', string=_('Task Type'), tracking=True)
    tag_ids = fields.Many2many('tt.task.tag', string=_('Tags'))
    color = fields.Integer(string=_('Color'))
    partner_id = fields.Many2one('res.partner', string=_('Customer'))
    company_id = fields.Many2one('res.company', string=_('Company'), default=lambda self: self.env.company, required=True, index=True)
    building_tag_ids = fields.Many2many(
        'tt.building.tag', 'tt_task_building_tag_rel', 'task_id', 'tag_id',
        string=_('Location Tags')
    )
    location_text = fields.Text(string=_('Location Details'))
    is_closed = fields.Boolean(string=_('Closed'), compute='_compute_is_closed', store=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string=_('Vehicle'))
    scheduled_date = fields.Datetime(string=_('Scheduled Date'), tracking=True)
    description = fields.Html()

    subtask_ids = fields.One2many('tt.subtask', 'task_id', string=_('Sub-tasks'))
    photo_ids = fields.Many2many(
        'ir.attachment', 'tt_task_ir_attachment_rel', 'task_id', 'attachment_id',
        string=_('Photos'),
        domain="[('mimetype', 'ilike', 'image/')]"
    )
    material_line_ids = fields.One2many('tt.material.line', 'task_id', string=_('Materials'))

    stage_id = fields.Many2one(
        'tt.task.stage', string=_('Stage'), index=True, tracking=True,
        default=lambda self: self._default_stage_id(),
        group_expand='_read_group_stage_id'
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], default='draft', tracking=True)

    kanban_state = fields.Selection([
        ('normal', 'In Progress'),
        ('blocked', 'Blocked'),
        ('done', 'Ready')
    ], default='normal', tracking=True)

    start_datetime = fields.Datetime(string=_('Start Time'))
    end_datetime = fields.Datetime(string=_('End Time'))
    timer_line_ids = fields.One2many('tt.timer.line', 'task_id', string=_('Time Logs'))
    duration_hours = fields.Float(
        string=_('Total Duration (hours)'), compute='_compute_total_duration', store=True
    )
    pause_start_datetime = fields.Datetime(string=_('Pause Start'), copy=False)
    accumulated_pause_seconds = fields.Integer(string=_('Paused Seconds'), default=0, copy=False)

    picking_ids = fields.Many2many(
        'stock.picking', 'tt_task_picking_rel', 'task_id', 'picking_id',
        string=_('Pickings'), copy=False
    )
    picking_count = fields.Integer(
        string=_('Pickings'), compute='_compute_picking_count', readonly=True
    )
    # UI helpers for Odoo 18 views (toggle Start/Stop button)
    can_start = fields.Boolean(compute='_compute_button_visibility', readonly=True)
    can_stop = fields.Boolean(compute='_compute_button_visibility', readonly=True)
    can_pause = fields.Boolean(compute='_compute_button_visibility', readonly=True)
    can_resume = fields.Boolean(compute='_compute_button_visibility', readonly=True)
    is_paused = fields.Boolean(compute='_compute_button_visibility', readonly=True, store=False)
    current_timer_display = fields.Char(
        string=_('Timer'), compute='_compute_current_timer_display', readonly=True
    )

    # Champs de localisation (similaires à hr_attendance)
    start_latitude = fields.Float(string="Start Latitude", digits=(10, 7), readonly=True, aggregator=None)
    start_longitude = fields.Float(string="Start Longitude", digits=(10, 7), readonly=True, aggregator=None)
    start_country_name = fields.Char(string="Start Country", help="Based on IP Address", readonly=True)
    start_city = fields.Char(string="Start City", readonly=True)
    start_ip_address = fields.Char(string="Start IP Address", readonly=True)
    start_browser = fields.Char(string="Start Browser", readonly=True)

    end_latitude = fields.Float(string="End Latitude", digits=(10, 7), readonly=True, aggregator=None)
    end_longitude = fields.Float(string="End Longitude", digits=(10, 7), readonly=True, aggregator=None)
    end_country_name = fields.Char(string="End Country", help="Based on IP Address", readonly=True)
    end_city = fields.Char(string="End City", readonly=True)
    end_ip_address = fields.Char(string="End IP Address", readonly=True)
    end_browser = fields.Char(string="End Browser", readonly=True)

    # Champ dummy pour le widget start button
    start_button_widget = fields.Char(compute='_compute_start_button_widget', store=False)

    @api.depends('can_start')
    def _compute_start_button_widget(self):
        for rec in self:
            rec.start_button_widget = 'start_button' if rec.can_start else ''

    @api.depends('timer_line_ids.duration_hours')
    def _compute_total_duration(self):
        for rec in self:
            rec.duration_hours = sum(rec.timer_line_ids.mapped('duration_hours'))

    @api.depends('state')
    def _compute_is_closed(self):
        for rec in self:
            rec.is_closed = rec.state in ('done', 'cancel')

    @api.depends('picking_ids')
    def _compute_picking_count(self):
        for rec in self:
            rec.picking_count = len(rec.picking_ids)

    @api.depends('state', 'timer_line_ids.end_datetime', 'timer_line_ids.start_datetime', 'pause_start_datetime')
    def _compute_button_visibility(self):
        for rec in self:
            has_open_timer = any(not l.end_datetime for l in rec.timer_line_ids)
            is_paused = bool(rec.pause_start_datetime)
            rec.is_paused = is_paused
            rec.can_start = (rec.state in ('draft', 'in_progress')) and not has_open_timer
            rec.can_pause = (rec.state == 'in_progress') and has_open_timer and not is_paused
            rec.can_stop = (rec.state == 'in_progress') and has_open_timer and not is_paused
            rec.can_resume = (rec.state == 'in_progress') and has_open_timer and is_paused

    @api.depends('state', 'start_datetime', 'end_datetime',
                 'timer_line_ids.start_datetime', 'timer_line_ids.end_datetime', 'duration_hours',
                 'pause_start_datetime', 'accumulated_pause_seconds')
    def _compute_current_timer_display(self):
        def _format_hms(seconds: int) -> str:
            h = seconds // 3600
            m = (seconds % 3600) // 60
            s = seconds % 60
            return f"{h:02d}:{m:02d}:{s:02d}"

        now = fields.Datetime.now()
        for rec in self:
            value = ''
            if rec.state == 'in_progress':
                open_line = next((l for l in rec.timer_line_ids if not l.end_datetime), None)
                if open_line and open_line.start_datetime:
                    delta = now - open_line.start_datetime
                    total_secs = int(delta.total_seconds()) if delta else 0
                    pause_secs = rec.accumulated_pause_seconds or 0
                    if rec.pause_start_datetime:
                        pause_delta = now - rec.pause_start_datetime
                        pause_secs += int(pause_delta.total_seconds()) if pause_delta else 0
                    secs = max(total_secs - pause_secs, 0)
                    value = _format_hms(secs)
                else:
                    total_secs = int((rec.duration_hours or 0.0) * 3600)
                    if total_secs > 0:
                        value = _format_hms(total_secs)
            elif rec.state == 'done':
                # Show final duration if available
                total_secs = int((rec.duration_hours or 0.0) * 3600)
                if total_secs > 0:
                    value = _format_hms(total_secs)
            rec.current_timer_display = value

    # --- Finish helpers ---
    def _get_stage_for_finish(self, xmlid, name, state):
        stage = self.env.ref(xmlid, raise_if_not_found=False)
        Stage = self.env['tt.task.stage']
        if stage and stage.state == state:
            return stage
        if name:
            found = Stage.search([('name', '=', name)], limit=1)
            if found:
                return found
        return Stage.search([('state', '=', state)], order='sequence, id', limit=1)

    # --- Stage helpers ---
    def _default_stage_id(self):
        stage = self.env['tt.task.stage'].search([], order='sequence, id', limit=1)
        return stage.id if stage else False

    @api.model
    def _read_group_stage_id(self, stages, domain, order=None):
        return self.env['tt.task.stage'].search([], order='sequence, id')

    def _sync_state_from_stage(self):
        for rec in self:
            if rec.stage_id and rec.state != rec.stage_id.state:
                rec.with_context(_skip_stage_sync=True).write({'state': rec.stage_id.state})

    def _sync_stage_from_state(self, preferred_stage=False):
        Stage = self.env['tt.task.stage']
        for rec in self:
            stage = False
            if preferred_stage and preferred_stage.exists() and preferred_stage.state == rec.state:
                stage = preferred_stage
            if not stage:
                stage = Stage.search([('state', '=', rec.state)], order='sequence, id', limit=1)
            if stage and rec.stage_id != stage:
                rec.with_context(_skip_stage_sync=True).write({'stage_id': stage.id})
        return self

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get('_skip_stage_sync'):
            return res
        if 'stage_id' in vals:
            self._sync_state_from_stage()
        if 'state' in vals:
            self._sync_stage_from_state()
        return res

    def action_stop(self):
        """Stop the running timer and finish the task (set to Done)."""
        # Reuse finish logic to ensure consistency (timer close + stock + state done)
        return self.action_finish()

    def action_toggle_timer(self):
        """Single button to Start or Stop depending on current state/timer."""
        for task in self:
            has_open_timer = any(not l.end_datetime for l in task.timer_line_ids)
            if task.state in ('draft', 'in_progress') and not has_open_timer:
                task.action_start()
            elif task.state == 'in_progress' and has_open_timer:
                task.action_stop()
            else:
                # No-op or inconsistent state
                raise UserError(_('Action not allowed in the current state.'))
        return True

    def action_pause_timer(self):
        """Pause the active timer without closing the task."""
        for task in self:
            if task.state != 'in_progress':
                raise UserError(_('Only in-progress tasks can be paused.'))
            if task.pause_start_datetime:
                raise UserError(_('The timer is already paused.'))
            open_line = task.timer_line_ids.filtered(lambda l: not l.end_datetime)
            if not open_line:
                raise UserError(_('No running timer found to pause.'))
            now = fields.Datetime.now()
            task.write({'pause_start_datetime': now})
        return True


    def action_resume_timer(self):
        """Resume a previously paused timer using the same timer line."""
        for task in self:
            if task.state != 'in_progress':
                raise UserError(_('Only in-progress tasks can be resumed.'))
            if not task.pause_start_datetime:
                raise UserError(_('No paused timer found.'))
            open_line = task.timer_line_ids.filtered(lambda l: not l.end_datetime)
            if not open_line:
                raise UserError(_('No running timer found to resume.'))
            now = fields.Datetime.now()
            pause_delta = now - task.pause_start_datetime
            paused_seconds = int(pause_delta.total_seconds()) if pause_delta else 0
            paused_seconds = max(paused_seconds, 0)
            task.write({
                'pause_start_datetime': False,
                'accumulated_pause_seconds': task.accumulated_pause_seconds + paused_seconds,
            })
        return True

    def action_open_finish_wizard(self):
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_('Only in-progress tasks can be finished.'))
        if self.pause_start_datetime:
            raise UserError(_('Resume the timer before finishing.'))
        open_line = self.timer_line_ids.filtered(lambda l: not l.end_datetime)
        if not open_line:
            raise UserError(_('No running timer found on this task.'))
        view = self.env.ref('technician_task_mgmt.view_tt_task_finish_wizard')
        context = dict(self.env.context, active_id=self.id, active_model=self._name, default_task_id=self.id)
        return {
            'name': _('Finish Task'),
            'type': 'ir.actions.act_window',
            'res_model': 'tt.task.finish.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view.id if view else False,
            'context': context,
        }

    def action_finish_with_option(self, option):
        valid_options = {'done', 'today'}
        if option not in valid_options:
            raise UserError(_('Unknown finish option.'))
        stage_map = {
            'done': self._get_stage_for_finish('technician_task_mgmt.tt_stage_done', 'Done', 'done'),
            'today': self._get_stage_for_finish('technician_task_mgmt.tt_stage_finished_today', 'Finished for Today', 'in_progress'),
        }
        target_stage = stage_map.get(option)
        final_state = 'done' if option == 'done' else 'in_progress'
        mark_end = option == 'done'
        self._finalize_finish(target_stage=target_stage, final_state=final_state, mark_end_datetime=mark_end)
        return True

    def _finalize_finish(self, target_stage=False, final_state='done', mark_end_datetime=True):
        for task in self:
            if task.state != 'in_progress':
                raise UserError(_('Only in-progress tasks can be finished.'))
            if task.pause_start_datetime:
                raise UserError(_('Resume the timer before finishing.'))
            if not task.photo_ids:
                raise UserError(_('Please add at least one photo before completing the task.'))
            open_line = task.timer_line_ids.filtered(lambda l: not l.end_datetime)
            if not open_line:
                raise UserError(_('No running timer found on this task.'))
            open_line = open_line[:1]
            now = fields.Datetime.now()
            total_pause = task.accumulated_pause_seconds or 0
            if task.pause_start_datetime:
                pause_delta = now - task.pause_start_datetime
                total_pause += int(pause_delta.total_seconds()) if pause_delta else 0
            total_pause = max(total_pause, 0)
            open_line.write({
                'end_datetime': now,
                'pause_duration_seconds': total_pause,
            })
            if task.material_line_ids:
                task._create_material_picking()

            # Capture end location information when finishing completely
            write_vals = {
                'pause_start_datetime': False,
                'accumulated_pause_seconds': 0,
            }

            # End location is already handled by JavaScript via update_end_location
            # No need to process geolocation here as it would overwrite the correct coordinates

            if final_state:
                write_vals['state'] = final_state
                if final_state == 'done':
                    write_vals['kanban_state'] = 'done'
                else:
                    write_vals['kanban_state'] = 'blocked'
            if mark_end_datetime:
                write_vals['end_datetime'] = now
            elif final_state != 'done':
                write_vals.setdefault('end_datetime', False)
            if target_stage and target_stage.exists():
                write_vals['stage_id'] = target_stage.id
            task.with_context(_skip_stage_sync=True).write(write_vals)
            preferred_stage = False
            if target_stage and target_stage.exists() and target_stage.state == task.state:
                preferred_stage = target_stage
            task._sync_stage_from_state(preferred_stage=preferred_stage)
        return True


    # Buttons
    def action_start_with_location(self):
        """Start task with geolocation - will be intercepted by JavaScript"""
        return self.action_start()

    def action_start_with_geolocation(self):
        """Start task with geolocation support - will be intercepted by JavaScript"""
        # This method will be intercepted by the FormController patch
        # If called directly (JS disabled), fallback to normal start
        return self.action_start()

    def start_with_location_rpc(self, latitude=False, longitude=False):
        """RPC method called by JavaScript to start task with optional geolocation"""
        self.ensure_one()

        if not self.id:
            return {'success': False, 'error': 'No task ID provided'}

        try:
            # Store geolocation if provided
            if latitude and longitude:
                geo_info = get_geoip_response(latitude=latitude, longitude=longitude)
                self.write({
                    'start_latitude': geo_info.get('latitude'),
                    'start_longitude': geo_info.get('longitude'),
                    'start_city': geo_info.get('city'),
                    'start_country_name': geo_info.get('country_name'),
                    'start_ip_address': geo_info.get('ip_address'),
                    'start_browser': geo_info.get('browser'),
                })

            # Start the task
            self.action_start()

            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def action_finish_with_location(self):
        """Finish task with geolocation - will be intercepted by JavaScript"""
        return self.action_finish()

    def action_start(self):
        """Start the task timer.
        - Ensure no open timer exists
        - Set state to in_progress, set start_datetime
        - Create timer line for current/assigned employee
        - Capture start location information
        """
        for task in self:
            if task.state not in ('draft', 'in_progress'):
                raise UserError(_('Cannot start a task that is not in Draft or In Progress.'))
            open_line = task.timer_line_ids.filtered(lambda l: not l.end_datetime)
            if open_line:
                raise UserError(_('The task is already running. Please stop it before starting again.'))
            employee = task.employee_id or self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
            if not employee:
                raise UserError(_('No employee linked to current user.'))
            now = fields.Datetime.now()

            # Capture start location information
            start_lat = task.env.context.get('start_latitude')
            start_lng = task.env.context.get('start_longitude')
            geo_info = get_geoip_response(latitude=start_lat, longitude=start_lng)

            write_vals = {
                'state': 'in_progress',
                'start_datetime': now,
                'pause_start_datetime': False,
                'accumulated_pause_seconds': 0,
            }

            # Add start location fields if available
            if geo_info:
                write_vals.update({
                    'start_latitude': geo_info.get('latitude'),
                    'start_longitude': geo_info.get('longitude'),
                    'start_city': geo_info.get('city'),
                    'start_country_name': geo_info.get('country_name'),
                    'start_ip_address': geo_info.get('ip_address'),
                    'start_browser': geo_info.get('browser'),
                })

            task.write(write_vals)
            # move to first stage with in_progress
            task._sync_stage_from_state()
            if not task.id:
                raise UserError(_('Invalid task record - no ID found'))

            self.env['tt.timer.line'].create({
                'task_id': task.id,
                'employee_id': employee.id,
                'start_datetime': now,
            })

        return False

    def _get_tt_settings(self):
        ICP = self.env['ir.config_parameter'].sudo()
        get_m2o = lambda key: int(ICP.get_param(key)) if ICP.get_param(key) else False
        warehouse_id = get_m2o('technician_task_mgmt.tt_warehouse_id')
        src_location_id = get_m2o('technician_task_mgmt.tt_src_location_id')
        dest_location_id = get_m2o('technician_task_mgmt.tt_dest_location_id')
        return warehouse_id, src_location_id, dest_location_id

    def _get_timesheet_project(self):
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()
        project_param = ICP.get_param('technician_task_mgmt.tt_timesheet_project_id')
        if not project_param:
            return self.env['project.project']
        try:
            project_id = int(project_param)
        except (TypeError, ValueError):
            return self.env['project.project']
        project = self.env['project.project'].browse(project_id)
        return project if project.exists() else self.env['project.project']

    def _ensure_dest_location(self, warehouse_id, dest_location_id):
        """Create a default internal destination location under the warehouse if missing."""
        StockLocation = self.env['stock.location'].sudo()
        existing_dest = False
        if dest_location_id:
            existing_dest = StockLocation.browse(dest_location_id)
            if existing_dest.exists() and existing_dest.usage == 'inventory':
                if not existing_dest.scrap_location:
                    existing_dest.write({'scrap_location': True})
                return existing_dest.id
        wh = self.env['stock.warehouse'].browse(warehouse_id) if warehouse_id else False
        parent_loc = False
        if existing_dest and existing_dest.exists():
            parent_loc = existing_dest
        elif wh and getattr(wh, 'scrap_location_id', False):
            parent_loc = wh.scrap_location_id
        elif wh and getattr(wh, 'lot_stock_id', False):
            parent_loc = wh.lot_stock_id
        else:
            parent_loc = StockLocation.search([('usage', '=', 'internal')], limit=1)
        dest = StockLocation.create({
            'name': _('Technician Consumption'),
            'usage': 'inventory',
            'scrap_location': True,
            'location_id': parent_loc.id if parent_loc else False,
            'company_id': wh.company_id.id if wh else self.env.company.id,
        })
        self.env['ir.config_parameter'].sudo().set_param('technician_task_mgmt.tt_dest_location_id', dest.id)
        return dest.id

    def _create_material_picking(self):
        """Consume task materials by scrapping them to the technician consumption location.
        This removes quantities from the source location while keeping a record of the operation.
        """
        StockScrap = self.env['stock.scrap'].sudo()
        for task in self:
            if not task.material_line_ids:
                continue
            warehouse_id, src_location_id, dest_location_id = task._get_tt_settings()
            warehouse = self.env['stock.warehouse'].browse(warehouse_id) if warehouse_id else self.env['stock.warehouse'].search([], limit=1)
            src_location = self.env['stock.location'].browse(src_location_id) if src_location_id else (warehouse.lot_stock_id if warehouse and getattr(warehouse, 'lot_stock_id', False) else self.env['stock.location'].search([('usage', '=', 'internal')], limit=1))
            dest_location_id = task._ensure_dest_location(warehouse.id if warehouse else False, dest_location_id)
            dest_location = self.env['stock.location'].browse(dest_location_id)

            Quant = self.env['stock.quant'].sudo()
            for line in task.material_line_ids:
                scrap_vals = {
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_uom_id.id,
                    'scrap_qty': line.quantity,
                    'origin': _('Task %s') % (task.name,),
                    'location_id': src_location.id if src_location else False,
                    'scrap_location_id': dest_location.id if dest_location else False,
                    'company_id': task.company_id.id if task.company_id else self.env.company.id,
                }
                scrap = StockScrap.create(scrap_vals)
                if hasattr(scrap, 'button_validate'):
                    scrap.button_validate()
                else:
                    scrap.action_validate()
                if src_location:
                    Quant._update_available_quantity(line.product_id, src_location, -line.quantity)
        return True

    def action_finish(self):
        """Finish the task completely using the default option."""
        return self.action_finish_with_option('done')

    def action_cancel(self):
        for task in self:
            task.write({
                'state': 'cancel',
                'pause_start_datetime': False,
                'accumulated_pause_seconds': 0,
            })
            task._sync_stage_from_state()
        return True

    def action_open_pickings(self):
        self.ensure_one()
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        action['domain'] = [('id', 'in', self.picking_ids.ids)]
        action['context'] = dict(self.env.context, default_picking_type_id=False)
        return action

    def action_start_location_maps(self):
        self.ensure_one()
        if not self.start_latitude or not self.start_longitude:
            raise UserError(_('No start location coordinates available.'))
        return {
            'type': 'ir.actions.act_url',
            'url': get_google_maps_url(self.start_latitude, self.start_longitude),
            'target': 'new'
        }

    def action_end_location_maps(self):
        self.ensure_one()
        if not self.end_latitude or not self.end_longitude:
            raise UserError(_('No end location coordinates available.'))
        return {
            'type': 'ir.actions.act_url',
            'url': get_google_maps_url(self.end_latitude, self.end_longitude),
            'target': 'new'
        }

    def update_end_location(self, latitude=False, longitude=False):
        """Update task end location like hr_attendance update_last_position"""
        for task in self:
            geo_info = get_geoip_response(latitude=latitude, longitude=longitude)
            task.write({
                'end_latitude': geo_info.get('latitude'),
                'end_longitude': geo_info.get('longitude'),
                'end_city': geo_info.get('city'),
                'end_country_name': geo_info.get('country_name'),
                'end_ip_address': geo_info.get('ip_address'),
                'end_browser': geo_info.get('browser'),
            })
        return True

    def finish_task_from_wizard(self, finish_option='done'):
        """Finish task like hr_attendance attendance_manual"""
        self.ensure_one()
        if self.state != 'in_progress':
            return {'warning': 'Only in-progress tasks can be finished.'}

        try:
            self.action_finish_with_option(finish_option)
            return {'type': 'ir.actions.act_window_close'}
        except Exception as e:
            return {'warning': str(e)}
