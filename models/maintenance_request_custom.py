from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _

from odoo.exceptions import UserError


class MaintenanceRequestCustom(models.Model):
    _name = 'maintenance.request.custom'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Custom Maintenance Request'

    @api.returns('self')
    def _default_stage(self):
        return self.env['maintenance.stage'].search([], limit=1)

    line_ids = fields.One2many('maintenance.technician.line', 'request_id')

    machine_temperature = fields.Char(
        string="Machine Temperature",
        help="Record the machine temperature"
    )
    work_area_temperature = fields.Char(
        string="Work Area Temperature",
        help="Record the work area temperature"
    )

    name = fields.Char(string='Request', required=True)

    equipment_id = fields.Many2one('maintenance.equipment',
                                   string="Equipment")

    category_id = fields.Many2one('maintenance.equipment.category',
                                  string='Category',
                                  related='equipment_id.category_id',
                                  readonly=True)

    request_date = fields.Date(string="Request Date",
                               default=fields.Date.today,
                               readonly=True)

    close_date = fields.Date('Close Date',
                             help="Date the maintenance was finished.")

    maintenance_type = fields.Selection([
        ('corrective', 'Corrective'),
        ('preventive', 'Preventive'),
        ('other_tasks', 'Other tasks'),
    ], string="Maintenance Type", default='corrective')

    maintenance_team_id = fields.Many2one('maintenance.team',
                                          string="Team",
                                          required=True)

    scheduled_date = fields.Datetime(string="Scheduled Date")

    duration = fields.Float(string="Duration")

    priority = fields.Selection([('0', 'Very Low'),
                                 ('1', 'Low'),
                                 ('2', 'Normal'),
                                 ('3', 'High')], string='Priority')

    email_cc = fields.Char(string="Email CC")

    description = fields.Html(string="Notes")

    instruction_type = fields.Selection([
        ('pdf', 'PDF'),
        ('google_slide', 'Google Slide'),
        ('text', 'Text')],
        string="Instruction", default="text")

    instruction_pdf = fields.Binary('PDF')

    archive = fields.Boolean(string='Archived', default=False)

    instruction_google_slide = fields.Char('Google Slide',
                                           help="Paste the url of your Google Slide. Make sure the access to the document is public.")

    instruction_text = fields.Html('Text')

    color = fields.Integer('Color Index')

    schedule_date = fields.Datetime('Scheduled Date',
                                    help="Date the maintenance team plans the maintenance.")

    company_id = fields.Many2one('res.company',
                                 string='Company',
                                 required=True,
                                 default=lambda self: self.env.company)

    department_id = fields.Many2one('hr.department',
                                    string="Department",
                                    default=lambda self: self.env.user.employee_id.department_id)

    user_id = fields.Many2one('res.users',
                              string='Responsible User'
                              , compute='_compute_user_from_employee',
                              store=True,
                              readonly=False,
                              tracking=True)

    stage_id = fields.Many2one('maintenance.stage',
                               string='Stage',
                               ondelete='restrict',
                               tracking=True,
                               group_expand='_read_group_stage_ids',
                               default=_default_stage,
                               copy=False)

    kanban_state = fields.Selection(
        [('normal', 'In Progress'),
         ('blocked', 'Blocked'),
         ('done', 'Ready for next stage')],
        string='Kanban State', required=True, default='normal', tracking=True)

    maintenance_request_id = fields.Many2one(
        'maintenance.request',
        string="Linked Original Request"
    )

    recurring_maintenance = fields.Boolean(string="Recurrent",
                                           compute='_compute_recurring_maintenance',
                                           store=True,
                                           readonly=False)

    repeat_interval = fields.Integer(string="Repeat Every", default=1)

    repeat_unit = fields.Selection([
        ('day', 'Days'),
        ('week', 'Weeks'),
        ('month', 'Months'),
        ('year', 'Years')
    ], string="Unit", default='month')

    repeat_type = fields.Selection([
        ('forever', 'Forever'),
        ('until', 'Until Date')
    ], string="Repeat Type", default='forever')

    repeat_until = fields.Date(string="Repeat Until")

    owner_user_id = fields.Many2one('res.users',
                                    string='Created by User',
                                    default=lambda s: s.env.uid)

    employee_id = fields.Many2one(
        'hr.employee',
        string='Responsible Employee',
        compute='_compute_employee_id',
        store=True,
        readonly=False,
        domain=lambda self: self._get_employee_domain()
    )

    maintenance_instructions_request_ids_custom = fields.One2many(
        'maintenance.instructions.custom',
        'request_id',
        string="Maintenance Instructions"
    )

    # @api.model_create_multi
    # def create(self, vals_list):
    #     """
    #     Automatically fill maintenance_instructions_request_ids_custom when creating a new maintenance.request.custom.
    #     """
    #     records = super().create(vals_list)
    #     for record in records:
    #         if record.equipment_id:
    #             for instruction in record.equipment_id.maintenance_instructions_ids:
    #                 self.env['maintenance.instructions.custom'].create({
    #                     'name': instruction.name,
    #                     'done': instruction.done,
    #                     'not_done': instruction.not_done,
    #                     'request_id': record.id,
    #                 })
    #
    #     return records

    # def write(self, values):
    #     """
    #     Automatically update maintenance_instructions_request_ids_custom when equipment_id is changed.
    #     """
    #     res = super().write(values)
    #     if 'equipment_id' in values:
    #         for record in self:
    #             record.maintenance_instructions_request_ids_custom.unlink()
    #             if record.equipment_id:
    #                 for instruction in record.equipment_id.maintenance_instructions_ids:  # استخدم الحقل الصحيح
    #                     self.env['maintenance.instructions.custom'].create({
    #                         'name': instruction.name,
    #                         'done': instruction.done,
    #                         'not_done': instruction.not_done,
    #                         'request_id': record.id,
    #                     })
    #     return res

    @api.onchange('equipment_id')
    def _onchange_equipment_id(self):
        for record in self:
            if record.equipment_id:
                record.machine_temperature = record.equipment_id.machine_temperature
                record.work_area_temperature = record.equipment_id.work_area_temperature
            else:
                record.machine_temperature = ''
                record.work_area_temperature = ''

    def action_assign_activity(self):
        for request in self:
            department = request.department_id
            if department and department.manager_id and department.manager_id.user_id:
                activity_type = self.env.ref('mail.mail_activity_data_todo')
                summary = "Follow up on maintenance requests"
                note = f"Please follow up on your maintenance request:{request.name}"

                self.env['mail.activity'].create({
                    'activity_type_id': activity_type.id,
                    'summary': summary,
                    'note': note,
                    'user_id': department.manager_id.user_id.id,
                    'res_id': request.id,
                    'res_model_id': self.env['ir.model']._get('maintenance.request').id,
                    'date_deadline': fields.Date.today(),
                })

    @api.model
    def _get_employee_domain(self):
        domain = []
        if self.maintenance_team_id:
            domain = [('id', 'in', self.maintenance_team_id.member_ids.ids)]
        return domain

    @api.depends('maintenance_team_id', 'equipment_id')
    def _compute_employee_id(self):
        for record in self:

            if record.equipment_id and record.equipment_id.technician_user_id:
                record.employee_id = record.equipment_id.technician_user_id.employee_id

            elif record.equipment_id and record.equipment_id.category_id.technician_user_id:
                record.employee_id = record.equipment_id.category_id.technician_user_id.employee_id

            # Fallback to first team member if available
            elif record.maintenance_team_id and record.maintenance_team_id.member_ids:
                record.employee_id = record.maintenance_team_id.member_ids[0]

            else:
                record.employee_id = False

    @api.depends('employee_id')
    def _compute_user_from_employee(self):
        for rec in self:
            rec.user_id = rec.employee_id.user_id.id if rec.employee_id else False

    @api.depends('maintenance_type')
    def _compute_recurring_maintenance(self):
        for request in self:
            if request.maintenance_type != 'preventive':
                request.recurring_maintenance = False

    def archive_equipment_request(self):
        self.write(
            {
                'archive': True,
                'recurring_maintenance': False
            })

    def reset_equipment_request(self):
        first_stage_obj = self.env['maintenance.stage'].search([], order="sequence asc", limit=1)
        self.write({'archive': False, 'stage_id': first_stage_obj.id})

    @api.model
    def create(self, vals):
        if 'stage_id' not in vals:
            first_stage = self.env['maintenance.stage'].search([], order='sequence asc', limit=1)

            if first_stage:
                vals['stage_id'] = first_stage.id

        # Pass close date if stage is done
        if vals.get('stage_id'):
            stage = self.env['maintenance.stage'].browse(vals['stage_id'])

        record = super(MaintenanceRequestCustom, self).create(vals)

        for rec in record:
            if rec.equipment_id:
                for instruction in record.equipment_id.maintenance_instructions_ids:
                    self.env['maintenance.instructions.custom'].create({
                        'name': instruction.name,
                        'done': instruction.done,
                        'not_done': instruction.not_done,
                        'request_id': rec.id,
                    })

        if record.department_id:
            record._create_department_activity(record)

        # Prepare values for linked request
        maintenance_request_vals = {
            'name': record.name,
            'equipment_id': record.equipment_id.id,
            'description': record.description,
            'request_date': record.request_date,
            'priority': record.priority,
            'user_id': record.employee_id.id,
            'responsible_employee_id': record.employee_id.id if record.employee_id else False,
            'schedule_date': record.scheduled_date,
            'duration': record.duration,
            'department_id': record.department_id.id,
            'maintenance_type': record.maintenance_type,
            'maintenance_team_id': record.maintenance_team_id.id,
            'instruction_type': record.instruction_type,
            'instruction_pdf': record.instruction_pdf,
            'repeat_interval': record.repeat_interval,
            'instruction_google_slide': record.instruction_google_slide,
            'instruction_text': record.instruction_text,
            'recurring_maintenance': record.recurring_maintenance,
            'email_cc': record.email_cc,
            'machine_temperature': record.machine_temperature,
            'line_ids': [(0, 0, {
                'technician': line.technician.id,
                'work_hours': line.work_hours,
                'mc_notes': line.mc_notes
            }) for line in record.line_ids],
        }

        linked_request = self.env['maintenance.request'].sudo().create(maintenance_request_vals)
        record.maintenance_request_id = linked_request.id

        # Attach instruction PDF if available
        if record.instruction_type == 'pdf' and record.instruction_pdf:
            self.env['ir.attachment'].create({
                'name': f"{record.name}_instruction.pdf",
                'type': 'binary',
                'datas': record.instruction_pdf,
                'res_model': 'maintenance.request',
                'res_id': linked_request.id,
                'mimetype': 'application/pdf'
            })

        # All Links
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        custom_url = f"{base_url}/web#id={record.id}&model=maintenance.request.custom&view_type=form"
        request_url = f"{base_url}/web#id={linked_request.id}&model=maintenance.request&view_type=form"

        # Activity in maintenance.request
        activity_note_maintenance_request = f"""
                <p>
                    <strong>{_("A New Maintenance Request Has Been Created. Please Review And Follow Up.")}</strong>
                </p>
                <ul>
                    <li><strong>{_("Request Name")}:</strong> {record.name}</li>
                    <li><strong>{_("Equipment")}:</strong> {record.equipment_id.name or 'N/A'}</li>
                    <li><strong>{_("Priority")}:</strong> {dict(record._fields['priority'].selection).get(record.priority) or ' '}</li>
                    <li><strong>{_("Scheduled Date")}:</strong> {record.scheduled_date or ' '}</li>
                </ul>
                <p>
                <p>
                🔗 <a href="{request_url}" target="_blank" style="color:#0b5394;text-decoration:underline;">{_("Open Original Request")}</a>
            </p>
                </p>
            """
        # Activity in maintenance.request.custom
        activity_note_maintenance_request_custom = f"""
                        <p>
                            <strong>{_("A New Maintenance Request Has Been Created. Please Review And Follow Up.")}</strong>
                        </p>
                        <ul>
                            <li><strong>{_("Request Name")}:</strong> {record.name}</li>
                            <li><strong>{_("Equipment")}:</strong> {record.equipment_id.name or 'N/A'}</li>
                            <li><strong>{_("Priority")}:</strong> {dict(record._fields['priority'].selection).get(record.priority) or ' '}</li>
                            <li><strong>{_("Scheduled Date")}:</strong> {record.scheduled_date or ' '}</li>
                        </ul>
                        <p>
                        <p>
                        🔗 <a href="{custom_url}" target="_blank" style="color:#0b5394;text-decoration:underline;">{_("Open Custom Request")}</a><br/>
                    </p>
                        </p>
                    """

        self.env['mail.activity'].create({
            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            'summary': _("New Maintenance Request: %s") % record.name,
            'note': activity_note_maintenance_request,
            'user_id': record.employee_id.user_id.id if record.employee_id else self.env.uid,
            'res_id': linked_request.id,
            'res_model_id': self.env['ir.model']._get_id('maintenance.request'),
            'date_deadline': fields.Date.today(),
        })

        self.env['mail.activity'].create({
            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            'summary': _("New Custom Maintenance Request: %s") % record.name,
            'note': activity_note_maintenance_request_custom,
            'user_id': record.employee_id.user_id.id if record.employee_id else self.env.uid,
            'res_id': record.id,
            'res_model_id': self.env['ir.model']._get_id('maintenance.request.custom'),
            'date_deadline': fields.Date.today(),
        })
        return record

    def write(self, vals):
        if vals and 'kanban_state' not in vals and 'stage_id' in vals:
            vals['kanban_state'] = 'normal'

        if 'stage_id' in vals:

            stage = self.env['maintenance.stage'].browse(vals['stage_id'])

            last_stage = self.env['maintenance.stage'].search([], order='sequence desc', limit=1)

            if stage.id == last_stage.id:
                vals['close_date'] = fields.Date.today()

                activity = self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=self.user_id.id or self.env.uid,
                    date_deadline=fields.Date.today(),
                    note="""
                    <p>{done} {finish}</p>
                    <p>{archive}</p>
                    """.format(
                        done=_("It was completed"),
                        finish=_("Finish the maintenance request."),
                        archive=_("Please archive the application or continue with any remaining tasks."),
                    )
                    ,

                    summary=_("🔧 Order status: Expired"),
                )
                activity.action_done()

            else:
                vals['close_date'] = False

            if self.department_id:
                self._create_department_activity(self)

            for request in self:
                if stage.done and request.maintenance_type == 'preventive' and request.recurring_maintenance:
                    schedule_date = request.schedule_date or fields.Datetime.now()
                    schedule_date += relativedelta(**{f"{request.repeat_unit}s": request.repeat_interval})
                    if request.repeat_type == 'forever' or schedule_date.date() <= request.repeat_until:
                        default_stage = self.env['maintenance.stage'].search([], order='sequence asc', limit=1)
                        request.copy({
                            'schedule_date': schedule_date,
                            'stage_id': default_stage.id if default_stage else False
                        })

        res = super(MaintenanceRequestCustom, self).write(vals)
        if 'equipment_id' in vals:
            for record in self:
                record.maintenance_instructions_request_ids_custom.unlink()
                if record.equipment_id:
                    for instruction in record.equipment_id.maintenance_instructions_ids:
                        self.env['maintenance.instructions.custom'].create({
                            'name': instruction.name,
                            'done': instruction.done,
                            'not_done': instruction.not_done,
                            'request_id': record.id,
                        })
        for record in self:
            if record.maintenance_request_id:
                update_vals = {}
                if 'name' in vals:
                    update_vals['name'] = record.name
                if 'equipment_id' in vals:
                    update_vals['equipment_id'] = record.equipment_id.id
                if 'description' in vals:
                    update_vals['description'] = record.description
                if 'priority' in vals:
                    update_vals['priority'] = record.priority
                if 'schedule_date' in vals:
                    update_vals['schedule_date'] = record.scheduled_date
                if 'duration' in vals:
                    update_vals['duration'] = record.duration
                if 'department_id' in vals:
                    update_vals['department_id'] = record.department_id.id
                if 'maintenance_team_id' in vals:
                    update_vals['maintenance_team_id'] = record.maintenance_team_id.id
                if 'maintenance_type' in vals:
                    update_vals['maintenance_type'] = record.maintenance_type
                if 'machine_temperature' in vals:
                    update_vals['machine_temperature'] = record.machine_temperature
                if 'work_area_temperature' in vals:
                    update_vals['work_area_temperature'] = record.work_area_temperature

                if update_vals:
                    record.maintenance_request_id.sudo().write(update_vals)

        if vals.get('owner_user_id') or vals.get('employee_id'):
            self._add_followers()

        if 'stage_id' in vals:
            last_stage = self.env['maintenance.stage'].search([], order="sequence desc", limit=1)

            self.filtered(lambda m: vals['stage_id'] == last_stage.id).write({'close_date': fields.Date.today()})
            self.filtered(lambda m: vals['stage_id'] != last_stage.id).write({'close_date': False})

            self.activity_feedback(['maintenance.mail_act_maintenance_request'])
            self.activity_update()

        if vals.get('employee_id') or vals.get('schedule_date'):
            self.activity_update()

        if self._need_new_activity(vals):
            self.activity_unlink(['maintenance.mail_act_maintenance_request'])
            self.activity_update()

        return res

    def _create_department_activity(self, request):
        department = request.department_id
        if not department.manager_id or not department.manager_id.user_id:
            return

        activity_type = self.env.ref('mail.mail_activity_data_todo')
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        request_url = f"{base_url}/web#id={request.id}&model=maintenance.request.custom&view_type=form"

        summary = _("New Maintenance Request for %s") % department.name
        note = (
                   "<p>%s</p>"
                   "<p><strong>%s:</strong> %s</p>"
                   "<p><strong>%s:</strong> %s</p>"
                   "<p><strong>%s:</strong> %s</p>"
                   "<p><a href='%s' target='_blank'>%s</a></p>"
               ) % (
                   _("New maintenance request created for your department"),
                   _("Request"), request.name,
                   _("Equipment"), request.equipment_id.name or _('N/A'),
                   _("Priority"), dict(request._fields['priority'].selection).get(request.priority) or '',
                   request_url,
                   _("View Request")
               )

        self.env['mail.activity'].create({
            'activity_type_id': activity_type.id,
            'summary': summary,
            'note': note,
            'user_id': department.manager_id.user_id.id,
            'res_id': department.id,
            'res_model_id': self.env['ir.model']._get('hr.department').id,
            'date_deadline': fields.Date.today(),
        })

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        stage_ids = stages.sudo()._search([], order=stages._order)
        return stages.browse(stage_ids)

    def activity_update(self):
        """ Update maintenance activities with proper links and details """
        for request in self:
            if request.schedule_date:
                base_url = request.get_base_url()
                request_url = f"{base_url}/web#id={request.id}&model=maintenance.request.custom&view_type=form"

                activity_vals = {
                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    'summary': f'Maintenance Request: {request.name}',
                    'note': f'Maintenance request created for equipment: {request.equipment_id.name or "N/A"}. '
                            f'<a href="{request_url}">Open Request</a>',
                    'user_id': request.employee_id.user_id.id if request.employee_id else request.owner_user_id.id or self.env.uid,
                    'date_deadline': request.schedule_date.date(),
                    'res_id': request.id,
                    'res_model_id': self.env['ir.model']._get_id('maintenance.request.custom'),
                }

                existing_activity = self.env['mail.activity'].search([
                    ('res_id', '=', request.id),
                    ('res_model_id', '=', self.env['ir.model']._get_id('maintenance.request.custom')),
                    ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
                ], limit=1)

                if existing_activity:
                    existing_activity.write(activity_vals)
                else:
                    self.env['mail.activity'].create(activity_vals)

    def send_notification_to_team(self):
        for request in self:
            if request.maintenance_team_id and request.schedule_date:
                today = fields.Date.today()
                if request.schedule_date.date() == today:
                    message = f"""
                        <p>New maintenance request scheduled for today:</p>
                        <p><strong>Request:</strong> {request.name}</p>
                        <p><strong>Equipment:</strong> {request.equipment_id.name or 'N/A'}</p>
                        <p><strong>Scheduled Date:</strong> {request.schedule_date}</p>
                        <p><strong>Priority:</strong> {dict(request._fields['priority'].selection).get(request.priority)}</p>
                    """
                    request.message_post(
                        body=message,
                        subject=f"Maintenance Scheduled: {request.name}",
                        partner_ids=request.maintenance_team_id.member_ids.mapped('partner_id').ids
                    )

    def _add_followers(self):
        for request in self:
            partner_ids = set()
            if request.owner_user_id:
                partner_ids.add(request.owner_user_id.partner_id.id)
            if request.employee_id and request.employee_id.user_id:
                partner_ids.add(request.employee_id.user_id.partner_id.id)
            if request.department_id and request.department_id.manager_id and request.department_id.manager_id.user_id:
                partner_ids.add(request.department_id.manager_id.user_id.partner_id.id)
            if request.maintenance_team_id and request.maintenance_team_id.member_ids:
                for member in request.maintenance_team_id.member_ids:
                    if member.user_id:
                        partner_ids.add(member.user_id.partner_id.id)
            if partner_ids:
                request.message_subscribe(partner_ids=list(partner_ids))

    def _need_new_activity(self, vals):
        return vals.get('equipment_id')

    @api.depends('company_id', 'equipment_id')
    def _compute_maintenance_team_id(self):
        for request in self:
            if request.equipment_id and request.equipment_id.maintenance_team_id:
                request.maintenance_team_id = request.equipment_id.maintenance_team_id.id
            elif request.equipment_id and request.equipment_id.category_id and request.equipment_id.category_id.maintenance_team_id:
                request.maintenance_team_id = request.equipment_id.category_id.maintenance_team_id.id
            else:
                request.maintenance_team_id = False

            if request.maintenance_team_id and request.maintenance_team_id.company_id and request.maintenance_team_id.company_id.id != request.company_id.id:
                request.maintenance_team_id = False


class MaintenanceTechnicianLine(models.Model):
    _name = "maintenance.technician.line"
    _description = "Maintenance Technician Line"

    request_id = fields.Many2one("maintenance.request.custom", string="Maintenance Request")
    technician = fields.Char(string="Technician")
    work_hours = fields.Float(string="Working Hours")
    mc_notes = fields.Text(string="M/C Notes")


class MaintenanceInstructionCustom(models.Model):
    _name = 'maintenance.instructions.custom'
    _description = 'Maintenance Instructions (Custom Request)'

    name = fields.Char(string="Instruction", required=True)
    done = fields.Boolean(string="Done")
    not_done = fields.Boolean(string="Not Done")
    request_id = fields.Many2one(
        'maintenance.request.custom',
        string="Maintenance Request",
        ondelete='cascade'
    )

    @api.constrains('done', 'not_done')
    def _check_instruction_status(self):
        for record in self:
            if record.done and record.not_done:
                raise UserError(_("An instruction cannot be both Done and Not Done!"))
