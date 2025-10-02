#-*- coding: utf-8 -*-

from odoo import models, fields, api


class biblioteca_libro(models.Model):
    _name = 'biblioteca.libro'
    _description = 'biblioteca.biblioteca'

    name = fields.Char()
    value = fields.Integer()
    value2 = fields.Float(compute="_value_pc", store=True) #---- Se guarda en la base de datos 
    description = fields.Text()

    @api.depends('value')
    def _value_pc(self):
        for record in self:
            record.value2 = float(record.value) / 100

