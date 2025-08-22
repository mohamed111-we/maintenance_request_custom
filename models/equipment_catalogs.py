from odoo import models, fields


class EquipmentCatalogue(models.Model):
    _name = 'equipment.catalogue'
    _description = 'Equipment Catalogue'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string="Equipment Catalogue",
        required=True
    )

    attachment_ids = fields.One2many(
        'ir.attachment',
        'res_id',
        string="Attachments",
        domain=lambda self: [
            ('res_model', '=', self._name),
            ('res_id', '=', self.id)
        ],
        auto_join=True
    )
    equipment_name = fields.Many2one('maintenance.equipment',string = "Equipment")
