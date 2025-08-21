from odoo import models, fields, api, _

class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    check_motors = fields.Boolean(
        string="Check all motors and gearboxes"
    )

    check_connections = fields.Boolean(
        string="Check looseness connections, hoses, and pipes"
    )

    check_units = fields.Boolean(
        string="Check input, output, and storage units"
    )

    check_filters = fields.Boolean(
        string="Check filters"
    )

    check_screw = fields.Boolean(
        string="Check screw conveyor"
    )

    check_compressor = fields.Boolean(
        string="Check compressor for scale opening/closing"
    )

    check_electrical = fields.Boolean(
        string="Check and clean all electrical components and replace if necessary"
    )

    machine_temperature = fields.Char(
        string="Machine Temperature",
        help="Record the machine temperature"
    )
    work_area_temperature = fields.Char(
        string="Work Area Temperature",
        help="Record the work area temperature"
    )

    item_code = fields.Char(string="Equipment Code", copy=False, readonly=True, index=True)

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        print('res=========>',res)
        print('vals_list=========>',vals_list)
        for record in res:
            if record.category_id and record.category_id.category_code:
                prefix = record.category_id.category_code
                print('prefix=========>',prefix)
                count = self.search_count([('category_id', '=', record.category_id.id)])
                record.item_code = f"{prefix}---{str(count).zfill(4)}"
                print('item_code==========>',record.item_code)
            else:
                record.item_code = ''
        return res


    def write(self, values):
        res = super().write(values)
        print('res=========>', res)
        print('values=========>', values)
        if 'category_id' in values:
            print('category_id=======>',self.category_id.name)
            prefix = self.category_id.category_code
            print('prefix=========>', prefix)
            count = self.search_count([('category_id', '=', self.category_id.id)])
            self.item_code = f"{prefix}---{str(count).zfill(4)}"
        return res
