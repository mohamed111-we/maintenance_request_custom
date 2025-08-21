from odoo import models, fields

class EquipmentCatalogue(models.Model):
    _name = 'equipment.catalogue'
    _description = 'Equipment Catalogue'

    name = fields.Char(string="Equipment Catalogue", required=True)
    file_type = fields.Selection([
        ('pdf', 'PDF File'),
        ('image', 'Image File'),
    ], string="File Type")

    image = fields.Binary(string="Attachment")
    attachment = fields.Binary(string="Attachment")
    attachment_filename = fields.Char(string="File Name")






