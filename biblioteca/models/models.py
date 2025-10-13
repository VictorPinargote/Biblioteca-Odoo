# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re
from datetime import date, timedelta

# -------------------------
# EDITORIAL
# -------------------------
class Editorial(models.Model):
    _name = "biblioteca.editorial"
    _description = "Editorial"

    name = fields.Char("Nombre", required=True)
    website = fields.Char("Sitio web")
    email = fields.Char("Email")
    phone = fields.Char("Teléfono")
    street = fields.Char("Calle")
    city = fields.Char("Ciudad")
    country_id = fields.Many2one("res.country", "País")
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("name_uniq", "unique(name)", "La editorial ya existe (nombre repetido).")
    ]


# -------------------------
# AUTOR
# -------------------------
class Autor(models.Model):
    _name = "biblioteca.autor"
    _description = "Autor"
    _rec_name = "full_name"

    firstname = fields.Char("Nombres", required=True)
    lastname = fields.Char("Apellidos", required=True)
    full_name = fields.Char("Autor", compute="_compute_full_name", store=True, index=True)
    country_id = fields.Many2one("res.country", "País")
    birth_date = fields.Date("Fecha de nacimiento")
    death_date = fields.Date("Fecha de fallecimiento")
    biography = fields.Text("Biografía")
    active = fields.Boolean(default=True)

    @api.depends("firstname", "lastname")
    def _compute_full_name(self):
        for r in self:
            r.full_name = ("%s %s" % (r.firstname or "", r.lastname or "")).strip()


# -------------------------
# LIBRO
# -------------------------
class Libro(models.Model):
    _name = "biblioteca.libro"
    _description = "Libro"
    _order = "name"

    # Datos básicos
    name = fields.Char("Título", required=True, index=True)
    isbn = fields.Char("ISBN", help="ISBN-10 o ISBN-13. Ej: 978-3-16-148410-0", index=True)
    publication_date = fields.Date("Fecha de publicación")
    pages = fields.Integer("Páginas")
    category = fields.Selection([
        ("novela", "Novela"),
        ("cuento", "Cuento"),
        ("poesia", "Poesía"),
        ("ensayo", "Ensayo"),
        ("tecnico", "Técnico"),
        ("otros", "Otros"),
    ], string="Categoría", default="otros", required=True)

    # Relaciones
    editorial_id = fields.Many2one("biblioteca.editorial", "Editorial", ondelete="set null")
    autor_ids = fields.Many2many("biblioteca.autor", string="Autores")

    # Inventario / préstamo
    ejemplares = fields.Integer("Ejemplares", default=1)
    disponibles = fields.Integer("Disponibles", compute="_compute_disponibles", store=True)
    prestamo_ids = fields.One2many("biblioteca.prestamo", "libro_id", string="Préstamos")
    prestamos_activos = fields.Integer("Préstamos activos", compute="_compute_disponibles", store=True)

    # Estado
    state = fields.Selection([
        ("disponible", "Disponible"),
        ("agotado", "Agotado"),
        ("no_prestable", "No prestable"),
    ], default="disponible", string="Estado")

    description = fields.Text("Descripción")

    _sql_constraints = [
        ("isbn_unique", "unique(isbn)", "El ISBN ya existe."),
        ("ejemplares_nonneg", "CHECK(ejemplares >= 0)", "Los ejemplares no pueden ser negativos.")
    ]

    @api.depends("ejemplares", "prestamo_ids.state")
    def _compute_disponibles(self):
        for r in self:
            activos = len(r.prestamo_ids.filtered(lambda p: p.state == "prestado"))
            r.prestamos_activos = activos
            r.disponibles = max(0, (r.ejemplares or 0) - activos)

    @api.constrains("isbn")
    def _check_isbn(self):
        isbn_regex = r"^(97(8|9))?\d{9}(\d|X)$"  # ISBN-10/13 (sin guiones)
        for r in self:
            if r.isbn and not re.sub(r"[- ]", "", r.isbn):
                raise ValidationError(_("ISBN inválido."))
            if r.isbn:
                raw = re.sub(r"[- ]", "", r.isbn)
                if not re.match(isbn_regex, raw):
                    raise ValidationError(_("Formato de ISBN inválido (use 10 u 13 dígitos).")) 

    def action_view_prestamos(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Préstamos de %s") % self.name,
            "res_model": "biblioteca.prestamo",
            "view_mode": "list,form",
            "domain": [("libro_id", "=", self.id)],
            "context": {"default_libro_id": self.id},
        }


# -------------------------
# USUARIO (socio de la biblioteca)
# -------------------------
class Usuario(models.Model):
    _name = "biblioteca.usuario"
    _description = "Usuario"
    _rec_name = "name"

    name = fields.Char("Nombre completo", required=True)
    dni = fields.Char("DNI / ID", required=True, index=True)
    email = fields.Char("Email")
    phone = fields.Char("Teléfono")
    address = fields.Char("Dirección")
    fecha_alta = fields.Date("Fecha de alta", default=fields.Date.context_today)
    sancionado = fields.Boolean("Sancionado", default=False)
    prestamo_ids = fields.One2many("biblioteca.prestamo", "usuario_id", string="Préstamos")
    multa_ids = fields.One2many("biblioteca.multa", "usuario_id", string="Multas")

    _sql_constraints = [
        ("dni_uniq", "unique(dni)", "Este DNI ya está registrado.")
    ]


# -------------------------
# PERSONAL (staff)
# -------------------------
class Personal(models.Model):
    _name = "biblioteca.personal"
    _description = "Personal"
    _rec_name = "name"

    name = fields.Char("Nombre", required=True)
    role = fields.Selection([
        ("bibliotecario", "Bibliotecario"),
        ("auxiliar", "Auxiliar"),
        ("admin", "Administración"),
    ], string="Rol", required=True, default="bibliotecario")
    employee_code = fields.Char("Código empleado")
    phone = fields.Char("Teléfono")
    email = fields.Char("Email")
    active = fields.Boolean(default=True)


# -------------------------
# PRESTAMO
# -------------------------
class Prestamo(models.Model):
    _name = "biblioteca.prestamo"
    _description = "Préstamo"
    _order = "fecha_prestamo desc"

    libro_id = fields.Many2one("biblioteca.libro", "Libro", required=True, ondelete="restrict")
    usuario_id = fields.Many2one("biblioteca.usuario", "Usuario", required=True, ondelete="restrict")
    personal_id = fields.Many2one("biblioteca.personal", "Atendido por", ondelete="set null")

    fecha_prestamo = fields.Date("Fecha de préstamo", default=fields.Date.context_today, required=True)
    dias = fields.Integer("Días de préstamo", default=7)
    fecha_devolucion_prevista = fields.Date("Fecha prevista", compute="_compute_fprev", store=True)
    fecha_devolucion_real = fields.Date("Fecha de devolución")
    state = fields.Selection([
        ("prestado", "Prestado"),
        ("devuelto", "Devuelto"),
        ("vencido", "Vencido"),
    ], default="prestado", string="Estado", tracking=True)

    dias_retraso = fields.Integer("Días de retraso", compute="_compute_retraso", store=True)
    multa_id = fields.One2many("biblioteca.multa", "prestamo_id", string="Multas generadas")

    _sql_constraints = [
        ("un_prestamo_por_usuario_libro_abierto",
         "CHECK(1=1)",
         "Constraint placeholder (validaciones extra en @constrains).")
    ]

    @api.depends("fecha_prestamo", "dias")
    def _compute_fprev(self):
        for r in self:
            base = r.fecha_prestamo or date.today()
            r.fecha_devolucion_prevista = base + timedelta(days=r.dias or 0)

    @api.depends("fecha_devolucion_prevista", "fecha_devolucion_real", "state")
    def _compute_retraso(self):
        today = date.today()
        for r in self:
            ref = r.fecha_devolucion_real or today
            if r.fecha_devolucion_prevista and r.state in ("prestado", "vencido", "devuelto"):
                delay = (ref - r.fecha_devolucion_prevista).days
                r.dias_retraso = max(0, delay)
            else:
                r.dias_retraso = 0

    @api.constrains("libro_id", "state")
    def _check_disponibilidad(self):
        for r in self:
            if r.state == "prestado" and r.libro_id.disponibles <= 0:
                raise ValidationError(_("No hay ejemplares disponibles de '%s'.") % r.libro_id.name)

    def action_devolver(self):
        for r in self:
            if r.state != "prestado":
                continue
            r.fecha_devolucion_real = fields.Date.context_today(self)
            r.state = "devuelto"
            # Si hubo retraso, crear multa 
            if r.dias_retraso > 0 and not r.multa_id:
                self.env["biblioteca.multa"].create({
                    "prestamo_id": r.id,
                    "usuario_id": r.usuario_id.id,
                    "tarifa_por_dia": 0.5,  
                })

    @api.onchange("fecha_prestamo", "dias")
    def _onchange_fechas(self):
        self._compute_fprev()


# -------------------------
# MULTA
# -------------------------
class Multa(models.Model):
    _name = "biblioteca.multa"
    _description = "Multa"

    prestamo_id = fields.Many2one("biblioteca.prestamo", "Préstamo", required=True, ondelete="cascade")
    usuario_id = fields.Many2one("biblioteca.usuario", "Usuario", required=True, ondelete="cascade")
    tarifa_por_dia = fields.Float("Tarifa por día", default=0.5)
    dias_retraso = fields.Integer("Días de retraso", related="prestamo_id.dias_retraso", store=True)
    monto = fields.Float("Monto", compute="_compute_monto", store=True)
    pagada = fields.Boolean("Pagada", default=False)
    fecha = fields.Date("Fecha", default=fields.Date.context_today)

    @api.depends("tarifa_por_dia", "dias_retraso")
    def _compute_monto(self):
        for r in self:
            r.monto = (r.tarifa_por_dia or 0.0) * (r.dias_retraso or 0)

    def action_marcar_pagada(self):
        self.write({"pagada": True})
