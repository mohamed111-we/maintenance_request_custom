from odoo import models, fields, api

class MaintenanceEquipmentCategory(models.Model):
    _inherit = 'maintenance.equipment.category'


    short_name = fields.Char(string="Short Name", copy=False, index=True)
    category_code = fields.Char(string="Category Code", copy=False, index=True)