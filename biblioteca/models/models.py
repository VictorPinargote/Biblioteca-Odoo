# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError 
from datetime import datetime, timedelta



# =========================================================
# 1. LIBROS
# =========================================================
class BibliotecaLibro(models.Model):
    _name = 'biblioteca.libro'
    _description = 'Libro de la Biblioteca' 
    
    firstname = fields.Char(string="Título del Libro", required=True)
    autor = fields.Many2one('biblioteca.autor', string='Autor del Libro')
    value = fields.Integer(string='Número de Ejemplares', default=1)
    value2 = fields.Float(compute="_value_pc", store=True, string='Costo de Referencia')
    description = fields.Text(string='Resumen del Libro')

    prestamo_ids = fields.One2many(
        'biblioteca.prestamo', 
        'libro_id', 
        string='Historial de Préstamos'
    )
    
    available = fields.Boolean(
        string='Disponible', 
        compute='_compute_available', 
        store=True,
    )
    

            

# =========================================================
# 2. AUTORES
# =========================================================
class BibliotecaAutor(models.Model):
    _name = 'biblioteca.autor'
    _description = 'Autor de la Biblioteca'
    
    firstname = fields.Char(string='Nombre', required=True)
    lastname = fields.Char(string='Apellido', required=True)
    
    libro_ids = fields.One2many('biblioteca.libro', 'autor', string='Libros Escritos')
    
    @api.depends('firstname','lastname')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.firstname or ''} {record.lastname or ''}"

# =========================================================
# 3. USUARIOS (LECTORES)
# =========================================================
class BibliotecaUsuario(models.Model):
    _name = 'biblioteca.usuario'
    _description = 'Usuario/Lector de la Biblioteca'
    _inherit = ['res.partner']
    
    prestamo_ids = fields.One2many(
        'biblioteca.prestamo', 
        'usuario_id', 
        string='Préstamos Realizados'
    )
    
    multa_ids = fields.One2many(
        'biblioteca.multa',
        'usuario_id',
        string='Multas'
    )
    
    prestamo_count = fields.Integer(
        string='Número de Préstamos',
        compute='_compute_prestamo_count',
        store=True 
    )
    
    multa_pendiente_count = fields.Integer(
        string='Multas Pendientes',
        compute='_compute_multa_pendiente_count',
        store=True
    )
    
    @api.depends('prestamo_ids')
    def _compute_prestamo_count(self):
        for record in self:
            record.prestamo_count = len(record.prestamo_ids)

    @api.depends('multa_ids.state')
    def _compute_multa_pendiente_count(self):
        for record in self:
            record.multa_pendiente_count = len(record.multa_ids.filtered(lambda m: m.state == 'pendiente'))


# =========================================================
# 4. PRÉSTAMOS
# =========================================================
class BibliotecaPrestamo(models.Model):
    _name = 'biblioteca.prestamo'
    _description = 'Registro de Préstamo de Libro'
    _rec_name = 'name'
    
    name = fields.Char(required=True, string='Prestamo')
    fecha_prestamo = fields.Datetime(default=datetime.now())
    libro_id = fields.Many2one('biblioteca.libro')
    usuario_id = fields.Many2one('biblioteca.usuario',string="Usuario")
    fecha_devolucion = fields.Datetime()
    multa_bol = fields.Boolean(default=False)
    multa = fields.Float()
    fecha_maxima = fields.Datetime(compute='_compute_fecha_devolucion')
    usuario = fields.Many2one('res.users', string='Usuario presta',
                              default = lambda self: self.evm.uid)
    
    estado = fields.Selection([('b','Borrador'),
                               ('p','Prestamo'),
                               ('m','Multa'),
                               ('d','Devuelto')],
                              string='Estado', default='b')
    @api.depends('fecha_devolucion','fecha_prestamo')
    def _compute_fecha_devolucion(self):
        for record in self:
            record.fecha_devolucion = record.fecha_prestamo + timedelta(days=2)
    
    def write(self, vals):
        seq = self.env.ref('biblioteca.sequence_codigo_prestamos').next_by_code('biblioteca.prestamo') 
        vals['name'] = seq
        return super(BibliotecaPrestamo, self).write(vals)
        
    def generar_prestamo(self):
        print("Generando prestamo")
        self.write({'estado':'p'})

# =========================================================
# 5. MULTAS
# =========================================================
class BibliotecaMulta(models.Model):
    _name = 'biblioteca.multa'
    _description = 'Multa por Retraso de Libro'
    _rec_name = 'name'

    name = fields.Char(string='Referencia de Multa', default=lambda self: self.env['ir.sequence'].next_by_code('biblioteca.multa'), readonly=True)
    
    usuario_id = fields.Many2one('biblioteca.usuario', string='Lector Multado', required=True)
    prestamo_id = fields.Many2one('biblioteca.prestamo', string='Préstamo Origen', required=True, ondelete='restrict')
    monto = fields.Float(string='Monto de la Multa', required=True, digits='Product Price')
    dias_retraso = fields.Integer(string='Días de Retraso', required=True)
    fecha_vencimiento = fields.Date(string='Fecha de Vencimiento', required=True)
    
    state = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('pagada', 'Pagada'),
        ('cancelada', 'Cancelada')
    ], string='Estado', default='pendiente', required=True, readonly=True)
    
    def action_pagar(self):
        self.ensure_one()
        self.state = 'pagada'