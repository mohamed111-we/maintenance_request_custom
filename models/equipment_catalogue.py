from odoo import models, fields

class EquipmentCatalogue(models.Model):
    _name = 'equipment.catalogue'
    _description = 'Equipment Catalogue'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = (fields.Char(
        string="Equipment Catalogue",
        required=True
    ))

    file_type = fields.Selection([
        ('file', 'PDF File'),
        ('image', 'Image File'),
    ], string="File Type")

    image = fields.Binary(
        string="Attachment"
    )

    attachment = fields.Binary(
        string="Attachment"
    )

    attachment_filename = fields.Char(
        string="File Name"
    )

    # if record.instruction_type == 'pdf' and record.instruction_pdf:
    #     self.env['ir.attachment'].create({
    #         'name': f"{record.name}_instruction.pdf",
    #         'type': 'binary',
    #         'datas': record.instruction_pdf,
    #         'res_model': 'maintenance.request',
    #         'res_id': linked_request.id,
    #         'mimetype': 'application/pdf'
    #     })






