from odoo import models, fields, api
from odoo.osv import expression


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    department_id = fields.Many2one(
        'hr.department',
        string="Department",
        default=lambda self: self.env.user.employee_id.department_id if self.env.user.employee_id else False
    )

    available_technician_ids = fields.Many2many(
        'hr.employee',
        compute='_compute_available_technicians',
        store=False,
        string='Available Technicians',
        domain="[('company_ids', 'in', company_id)]"
    )
    responsible_employee_id = fields.Many2one('hr.employee',
                                              string='Responsible Employee'
                                              , compute='_compute_responsible_employee_id',
                                              store=True,
                                              readonly=False,
                                              tracking=True,
                                              domain="[('id', 'in', available_technician_ids)]"
                                              )

    maintenance_type = fields.Selection(selection_add=[
        ('other_tasks', 'Other tasks')
    ])

    line_ids = fields.One2many(
        "maintenance.request.line",
        "request_id",
        string="Request Lines"
    )

    machine_temperature = fields.Char(
        string="Machine Temperature",
        help="Record the machine temperature"
    )
    work_area_temperature = fields.Char(
        string="Work Area Temperature",
        help="Record the work area temperature"
    )

    # maintenance_instructions_request_ids = fields.One2many(
    #     'maintenance.instructions',
    #     'request_id',
    #     string="Maintenance Instructions"
    # )

    done_instruction_ids = fields.One2many(
        'maintenance.instructions',
        'request_id',
        string="Done Instructions",
        compute="_compute_done_instructions",
        store=False
    )

    @api.depends('equipment_id.maintenance_instructions_ids.done')
    def _compute_done_instructions(self):
        for rec in self:
            if rec.equipment_id:
                rec.done_instruction_ids = rec.equipment_id.maintenance_instructions_ids.filtered(lambda ins: ins.done)
            else:
                rec.done_instruction_ids = False

    @api.model_create_multi
    def create(self, vals_list):
        """
        Automatically fill maintenance_instructions_ids when creating a new maintenance.request.
        """
        records = super().create(vals_list)
        for record in records:
            if record.equipment_id:
                for instruction in record.equipment_id.maintenance_instructions_ids:
                    self.env['maintenance.instructions'].create({
                        'name': instruction.name,
                        'request_id': record.id,
                    })
        return records

    def write(self, values):
        """
        Automatically update maintenance_instructions_ids when equipment_id is changed.
        """
        res = super().write(values)
        if 'equipment_id' in values:
            for record in self:
                # Clear existing instructions
                record.maintenance_instructions_request_ids.unlink()
                # Copy instructions from the new equipment_id
                if record.equipment_id:
                    for instruction in record.equipment_id.maintenance_instructions_ids:
                        self.env['maintenance.instructions'].create({
                            'name': instruction.name,
                            'request_id': record.id,
                        })
        return res


    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):

        domain = expression.normalize_domain(domain)

        user = self.env.user
        # Group that should have full access
        manager_group = self.env.ref('maintenance_custom.group_maintenance_request_creator', raise_if_not_found=False)
        # If user is NOT in the manager group, restrict by department
        if manager_group and manager_group in user.groups_id:
            department = user.employee_id.department_id
            print(user.employee_id.name)
            if department:
                extra_domain = [('department_id', '=', department.id)]
                domain = expression.AND([domain, extra_domain])
            else:
                # No department assigned, block access to all records
                domain = expression.AND([domain, [('id', '=', False)]])

        return super(MaintenanceRequest, self)._search(domain, offset=offset, limit=limit, order=order)

    @api.depends('maintenance_team_id')
    def _compute_available_technicians(self):
        """Compute the available technicians based on the selected team."""
        for record in self:
            if record.maintenance_team_id:
                record.available_technician_ids = record.maintenance_team_id.member_ids.ids
            else:
                record.available_technician_ids = False

    @api.onchange('maintenance_team_id')
    def _onchange_maintenance_team_id(self):
        for rec in self:
            rec.responsible_employee_id = False

    @api.depends('company_id', 'equipment_id')
    def _compute_responsible_employee_id(self):
        for request in self:
            if request.equipment_id:
                request.responsible_employee_id = request.equipment_id.technician_user_id.employee_id or request.equipment_id.category_id.technician_user_id.employee_id
            if request.responsible_employee_id and request.company_id.id not in request.responsible_employee_id.user_id.company_ids.ids:
                request.responsible_employee_id = False




    def action_create_activity(self):
        for request in self:
            if request.department_id and request.department_id.manager_id.user_id:
                activity_type = self.env.ref('mail.mail_activity_data_todo')
                summary = "New Maintenance Activity"
                note = "Please review the maintenance request."
                self.env['mail.activity'].create({
                    'activity_type_id': activity_type.id,
                    'summary': summary,
                    'note': note,
                    'user_id': request.department_id.manager_id.user_id.id,
                    'res_id': request.id,
                    'res_model': request._name,
                    'date_deadline': fields.Date.today(),
                })

class MaintenanceTeam(models.Model):
    _inherit = 'maintenance.team'

    member_ids = fields.Many2many(
        'hr.employee',
        'maintenance_team_employees_rel',
        string="Team Members",
        domain="[('company_ids', 'in', company_id)]")

class MaintenanceRequestLine(models.Model):
    _name = "maintenance.request.line"
    _description = "Maintenance Request Line"

    request_id = fields.Many2one("maintenance.request", string="Maintenance Request")
    technician = fields.Char(string="Technician")
    work_hours = fields.Float(string="Working Hours")
    mc_notes = fields.Text(string="M/C Notes")



