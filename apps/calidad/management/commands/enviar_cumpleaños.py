import os
from io import BytesIO
from email.mime.image import MIMEImage
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.db.models import Q
from PIL import Image, ImageDraw, ImageFont

# ¡Asegúrate de que la app se llame así en tu proyecto!
from recursoshumanos.models import Trabajador 

class Command(BaseCommand):
    help = 'Envía correos de cumpleaños con imagen personalizada basados en el modelo Trabajador'

    def handle(self, *args, **kwargs):
        self.stdout.write("Buscando cumpleañeros del día...")
        hoy = timezone.now().date()
        meses = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

        # Filtramos: Que cumplan hoy, que tengan email, y MUY IMPORTANTE, que estén activos
        cumpleaneros = Trabajador.objects.filter(
            fecha_nacimiento__month=hoy.month,
            fecha_nacimiento__day=hoy.day,
            email__isnull=False,
            activo=True
        ).filter(
            Q(fecha_cese__isnull=True) | Q(fecha_cese__gt=hoy)
        ).exclude(email__exact='')

        if not cumpleaneros.exists():
            self.stdout.write("No hay cumpleaños el día de hoy.")
            return

        # --- RUTAS DE MATERIALES ---
        base_dir = settings.BASE_DIR
        ruta_imagen = os.path.join(base_dir, 'static', 'img', 'plantilla_cumple.jpg')
        ruta_fuente_nombre = os.path.join(base_dir, 'static', 'fonts', 'cursiva.ttf') 
        ruta_fuente_texto = os.path.join(base_dir, 'static', 'fonts', 'arial.ttf') 

        recursos_requeridos = [ruta_imagen, ruta_fuente_nombre, ruta_fuente_texto]
        recursos_faltantes = [ruta for ruta in recursos_requeridos if not os.path.exists(ruta)]
        if recursos_faltantes:
            for recurso in recursos_faltantes:
                self.stdout.write(self.style.ERROR(f"Recurso no encontrado: {recurso}"))
            return

        for trabajador in cumpleaneros:
            try:
                # 1. ABRIR LA IMAGEN
                img = Image.open(ruta_imagen)
                draw = ImageDraw.Draw(img)

                # 2. CARGAR FUENTES (Ajusta los tamaños)
                font_nombre = ImageFont.truetype(ruta_fuente_nombre, 80)
                font_proyecto = ImageFont.truetype(ruta_fuente_texto, 24)
                font_fecha = ImageFont.truetype(ruta_fuente_texto, 25)

                # 3. TEXTO: Nombre del trabajador
                # Armamos el nombre de forma explícita para no omitir el apellido paterno.
                # Mostramos: primer nombre + apellido paterno + apellido materno.
                primer_nombre = (trabajador.nombres or '').split()[0] if trabajador.nombres else ''
                nombre_trabajador = " ".join(
                    parte for parte in [
                        primer_nombre,
                        trabajador.apellido_paterno,
                        trabajador.apellido_materno,
                    ]
                    if parte
                ).title()
                
                # 4. TEXTO: Proyecto del trabajador
                # Como es ManyToMany, tomamos el primero. Si no tiene, usamos su Área o Ceneris
                primer_proyecto = trabajador.proyectos.first()
                if primer_proyecto:
                    nombre_proyecto = f"PROYECTO {primer_proyecto.nombre}".upper()
                elif trabajador.area:
                    nombre_proyecto = f"ÁREA DE {trabajador.area.nombre}".upper()
                else:
                    nombre_proyecto = "FAMILIA CENERIS"

                # 5. DIBUJAR LOS TEXTOS EN LA IMAGEN
                # NOTA: Los números (500, 500) son las coordenadas X, Y. 
                # Tendrás que ajustarlos según el tamaño real de tu imagen de fondo.
                draw.text((510, 430), nombre_trabajador, font=font_nombre, fill="#000000", anchor="mm")
                draw.text((520, 520), nombre_proyecto, font=font_proyecto, fill="#000000", anchor="mm")

                # Dibujar el día y mes en la esquina (en el ícono del calendario)
                draw.text((940, 70), str(hoy.day), font=font_fecha, fill="#000000", anchor="mm")
                draw.text((940, 90), meses[hoy.month], font=font_fecha, fill="#000000", anchor="mm")

                buffer = BytesIO()
                img.save(buffer, format="JPEG", quality=90)
                image_data = buffer.getvalue()

                # 6. OBTENER CORREOS DE COMPAÑEROS (@ceneris.com)
                # Se notifica por BCC a todos los trabajadores activos con dominio @ceneris.com,
                # excluyendo al cumpleañero para evitar que reciba una copia adicional.
                compañeros = Trabajador.objects.filter(
                    activo=True,
                    email__icontains='@ceneris.com'
                ).filter(
                    Q(fecha_cese__isnull=True) | Q(fecha_cese__gt=hoy)
                ).exclude(id=trabajador.id)

                # values_list(flat=True) devuelve solo la columna email como lista de strings.
                lista_bcc = list(compañeros.values_list('email', flat=True))

                # 7. PREPARAR Y ENVIAR EL CORREO

                asunto = f"!Hoy es el cumpleaños de {nombre_trabajador}! 🎉"

                html_content = render_to_string('calidad/emails/feliz_cumpleaños.html', {'nombre': trabajador.nombres})
                
                msg = EmailMultiAlternatives(
                    subject=asunto, 
                    body="¡Feliz cumpleaños!", 
                    from_email=settings.DEFAULT_FROM_EMAIL, 
                    to=[trabajador.email],
                    bcc=lista_bcc
                )

                msg.attach_alternative(html_content, "text/html")

                img_attachment = MIMEImage(image_data)
                img_attachment.add_header('Content-ID', '<cumple_img>')
                msg.attach(img_attachment)

                msg.send()

                self.stdout.write(self.style.SUCCESS(
                    f"  -> Correo enviado a: {nombre_trabajador} y notificado a {len(lista_bcc)} compañeros."
                ))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  -> Error con {trabajador.nombres}: {e}"))