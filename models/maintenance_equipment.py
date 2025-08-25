from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    machine_temperature = fields.Char(string="Machine Temperature")
    work_area_temperature = fields.Char(string="Work Area Temperature")

    maintenance_instructions_ids = fields.One2many(
        'maintenance.instructions', 'equipment_id',
        string="Maintenance Instructions"
    )
    item_code = fields.Char(string="Equipment Code", copy=False, readonly=True, index=True)

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for record in res:
            if record.category_id and record.category_id.category_code:
                prefix = record.category_id.category_code
                count = self.search_count([('category_id', '=', record.category_id.id)])
                record.item_code = f"{prefix}---{str(count).zfill(4)}"
            else:
                record.item_code = ''
        return res

    def write(self, values):
        res = super().write(values)
        if 'category_id' in values:
            prefix = self.category_id.category_code
            count = self.search_count([('category_id', '=', self.category_id.id)])
            self.item_code = f"{prefix}---{str(count).zfill(4)}"
        else:
            self.item_code = ''
        return res


class MaintenanceInstruction(models.Model):
    _name = 'maintenance.instructions'
    _description = 'Maintenance Instructions'

    name = fields.Char(string="Instruction", required=True)
    done = fields.Boolean(string="Done")
    not_done = fields.Boolean(string="Not Done")
    equipment_id = fields.Many2one('maintenance.equipment', string="Equipment", ondelete='cascade')
    request_id = fields.Many2one('maintenance.request', string="Maintenance Request", ondelete='cascade')

    @api.constrains('done', 'not_done')
    def _check_instruction_status(self):
        for record in self:
            if record.done and record.not_done:
                raise UserError(_("An instruction cannot be both Done and Not Done!"))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.equipment_id:
                requests = self.env['maintenance.request.custom'].search(
                    [('equipment_id', '=', record.equipment_id.id)])
                for req in requests:
                    self.env['maintenance.instructions.custom'].create({
                        'name': record.name,
                        'done': record.done,
                        'not_done': record.not_done,
                        'request_id': req.id,
                    })
        return records

    def write(self, vals):
        res = super().write(vals)
        for record in self:
            if record.equipment_id:
                requests = self.env['maintenance.request.custom'].search(
                    [('equipment_id', '=', record.equipment_id.id)])
                for req in requests:
                    instr = self.env['maintenance.instructions.custom'].search([
                        ('name', '=', record.name),
                        ('request_id', '=', req.id)
                    ], limit=1)
                    if instr:
                        instr.write({
                            'done': record.done,
                            'not_done': record.not_done
                        })
        return res
