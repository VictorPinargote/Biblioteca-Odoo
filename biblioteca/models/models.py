import requests
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from odoo.exceptions import UserError

# MODELO PARA LIBRO

class BibliotecaLibro(models.Model): 
    _name = 'biblioteca.libro' #nombre de 
    _description = 'biblioteca.biblioteca'
    _rec_name = 'titulo'

    firstname = fields.Char(string='Nombre de búsqueda') 
    titulo = fields.Char(string='Título del Libro') 
    author = fields.Many2one('biblioteca.autor', string='Autor Libro')
    ejemplares = fields.Integer(string='Número de ejemplares')
    costo = fields.Float(string="Costo")
    description = fields.Text(string='Resumen del libro')    
    fecha_publicacion = fields.Date(string='Fecha de Publicación')
    genero = fields.Char(string='Género')
    isbn = fields.Char(string='ISBN')
    paginas = fields.Integer(string='Páginas')
    editorial = fields.Many2one('biblioteca.editorial', string='Editorial')
    ubicacion = fields.Char(string='Categoría')

    def action_buscar_openlibrary(self):

        for record in self:
            if not record.firstname:
                raise UserError("Por favor, ingrese un nombre en 'Nombre de búsqueda' antes de buscar en OpenLibrary.")
            
            try:
                url = f"https://openlibrary.org/search.json?q={record.firstname}"
                response = requests.get(url, timeout=8)
                response.raise_for_status()
                data = response.json()
                
                if not data.get('docs'):
                    raise UserError("No se encontró ningún libro con ese nombre en OpenLibrary.")
                
                # Tomamos el primer resultado relevante
                libro = data['docs'][0]
                work_key = libro.get('key')  # Ej: "/works/OL12345W"
                titulo = libro.get('title', 'Sin título')
                autor_nombre = libro.get('author_name',['Desconocido'])[0]
                anio = libro.get('first_publish_year')
                editorial_nombre = libro.get('publisher', ['Desconocido'])[0]
                paginas = 0
                descripcion = ""
                generos = []
                isbn = libro.get('isbn', [None])[0] if libro.get('isbn') else None

                if work_key:
                    work_url = f"https://openlibrary.org{work_key}.json"
                    work_resp = requests.get(work_url, timeout=10)
                    if work_resp.ok:
                        work_data = work_resp.json()

                        # Descripción
                        if isinstance(work_data.get('description'), dict):
                            descripcion = work_data['description'].get('value', '')
                        elif isinstance(work_data.get('description'), str):
                            descripcion = work_data['description']

                        # Géneros
                        if work_data.get('subjects'):
                            generos = work_data['subjects'][:3]

                        # Intentar obtener páginas desde ediciones
                        editions_url = f"https://openlibrary.org{work_key}/editions.json"
                        editions_resp = requests.get(editions_url, timeout=10)
                        if editions_resp.ok:
                            editions_data = editions_resp.json()
                            if editions_data.get('entries'):
                                entry = editions_data['entries'][0]
                                paginas = entry.get('number_of_pages', 0)
                                isbn = entry.get('isbn_10', [None])[0] if entry.get('isbn_10') else isbn
                                editorial_nombre = entry.get('publishers', [None])[0] if entry.get('publishers') else editorial_nombre

                # Buscar o crear autor si no existe
                autor = self.env['biblioteca.autor'].search([('firstname', '=', autor_nombre)], limit=1)
                if not autor:
                    autor = self.env['biblioteca.autor'].create({'firstname': autor_nombre})

                # Buscar o crear editorial
                editorial = self.env['biblioteca.editorial'].search([('name', '=', editorial_nombre)], limit=1)
                if not editorial:
                    editorial = self.env['biblioteca.editorial'].create({'name': editorial_nombre})
                    
                record.write({
                    'titulo': titulo,
                    'author': autor.id,
                    'isbn': isbn or "No disponible",
                    'paginas': paginas or 0,
                    'fecha_publicacion': datetime.strptime(str(anio), '%Y').date() if anio else None,
                    'description': descripcion or "No hay descripción disponible.",
                    'editorial': editorial.id,
                    'genero':", ".join(generos) if generos else "Desconocido",
                })

            except Exception as e:
                raise UserError(f"Error al conectar con OpenLibrary: {str(e)}")
            
# MODELO PARA AUTOR

            
# =========================================================
# 2. AUTORES
# =========================================================
class BibliotecaAutor(models.Model):
    _name = 'biblioteca.autor'
    _description = 'biblioteca.autor' 
   
    firstname = fields.Char()
    lastname = fields.Char()
    nacimiento=fields.Date()
    libros= fields.Many2many('biblioteca.libro','libro_autor_rel', column1= 'author_id', column2= 'libro_id', string='Libros Publicados')

    @api.depends('firstname', 'lastname')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.firstname} {record.lastname}" 

# MODELO NUEVO PARA EDITORIAL
class BibliotecaEditorial(models.Model):
    _name = 'biblioteca.editorial'
    _description = 'Editorial de libros'

    name = fields.Char(string='Nombre Editorial', required=True)
    pais = fields.Char(string='País')
    ciudad = fields.Char(string='Ciudad')


# MODELO NUEVO PARA USUARIOS
class BibliotecaUsuario(models.Model):
    _name = 'biblioteca.usuario'
    _description = 'Usuarios de la biblioteca'

    name = fields.Char(string='Nombre Completo', required=True)
    cedula = fields.Char(string='Cédula')
    telefono = fields.Char(string='Teléfono')
    email = fields.Char(string='Email')
    tipo = fields.Selection([
        ('estudiante', 'Estudiante'),
        ('profesor', 'Profesor'),
        ('externo', 'Externo')
    ], string='Tipo de Usuario')

    @api.constrains('cedula')
    def _check_cedula(self):
        for record in self:
            if record.cedula and not self.validar_cedula_ec(record.cedula):
                raise ValidationError("Cédula ecuatoriana inválida: %s" % record.cedula)

    def validar_cedula_ec(self, cedula):
        if len(cedula) != 10 or not cedula.isdigit():
            return False

        provincia = int(cedula[0:2])
        if provincia < 1 or provincia > 24:
            return False

        coef = [2,1,2,1,2,1,2,1,2]
        total = 0
        for i in range(9):
            val = int(cedula[i]) * coef[i]
            if val >= 10:
                val -= 9
            total += val
        digito_verificador = 10 - (total % 10) if total % 10 != 0 else 0
        return digito_verificador == int(cedula[9])

# MODELO NUEVO PARA PERSONAL
class BibliotecaPersonal(models.Model):
    _name = 'biblioteca.personal'
    _description = 'Personal de la biblioteca'

    name = fields.Char(string='Nombre Completo', required=True)
    cargo = fields.Char(string='Cargo')
    telefono = fields.Char(string='Teléfono')
    email = fields.Char(string='Email')


# MODELO NUEVO PARA PRÉSTAMOS
class BibliotecaPrestamo(models.Model):
    _name = 'biblioteca.prestamo'
    _description = 'Préstamos de libros'

    name = fields.Char(string='Prestamo')
    fecha_prestamo = fields.Datetime( default=datetime.now())
    libro_id = fields.Many2one('biblioteca.libro')
    usuario_id = fields.Many2one('biblioteca.usuario', string='Usuario')
    fecha_devolucion = fields.Datetime()
    multa_bol = fields.Boolean(default=False)
    multa= fields.Float()
    fecha_maxima = fields.Datetime(compute='_compute_fecha_devolucion', store = True) #con compute no se puede hacer consultas; con el store = True me permite almacenar pero la desventaja es que se hace estatico la fecha 
    usuario= fields.Many2one('res.users',string='Usuario presta',
                            default= lambda self: self.env.uid)
                            
    estado = fields.Selection([('b', 'Borrador'),('p', 'Prestado'),('m', 'Multa'),('d', 'Devuelto')], string='Estado', default='b')

    def _cron_multas(self):
        prestamos = self.env['biblioteca.prestamo'].search([('estado', '=' ,'p'),  #Tupla tiene 3 items sub0 lo que quiero cambiar sub1 el comparativo, sub2 con el que se compara
                                                           ('fecha_maxima', '<' , datetime.now())]) #El search devuelve una lista de objetos en este caso de prestamos
        for prestamo in prestamos:    #Se usa el for para recorrer todo la lista que se creo de los prestamos
            prestamo.write({'estado':'m',
                            'multa_bol':True,
                            'multa': 1.0})
            
        prestamos = self.env['biblioteca.prestamo'].search([('estado', '=', 'm')])
        for prestamo in prestamos:
            days = (datetime.now() - prestamo.fecha_maxima).days
            #days.days - es otra forma de hacerlo
            prestamo.write({'multa':days})
            
            
    @api.depends('fecha_maxima','fecha_devolucion')
    def _compute_fecha_devolucion(self):
        for record in self:
            record.fecha_maxima = record.fecha_prestamo + timedelta(days=2)

    def write(self, vals):
        seq = self.env.ref('biblioteca.sequence_codigo_prestamos').next_by_code('biblioteca.prestamo')
        vals['name'] =seq
        return super(BibliotecaPrestamo, self).write(vals)
        
    def generar_prestamo(self):
        print("Generando préstamo")
        self.write({'estado': 'p'})
    

    class BibliotecaMulta(models.Model):
        _name= 'biblioteca.multa'
        _description='biblioteca.multa'
        _rec_name= 'name_multa'

        name_multa=fields.Char(string='Codigo de la Multa')
        multa= fields.Char(string='Descripcion de la Multa')
        costo_multa= fields.Char(string='Costo de la multa')
        fecha_multa= fields.Date(string= 'Fecha de la Multa')
        prestamo= fields.Many2one('biblioteca.prestamo')