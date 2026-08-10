from PIL import Image, ImageDraw, ImageFont

# Pon aquí la ruta real de tu compu
img = Image.open('static/img/plantilla_cumple.jpg') 
draw = ImageDraw.Draw(img)

# Pon aquí la ruta real de tus fuentes
font_nombre = ImageFont.truetype('static/fonts/cursiva.ttf', 80)
font_proyecto = ImageFont.truetype('static/fonts/arial.ttf', 30)
font_fecha = ImageFont.truetype('static/fonts/arial.ttf', 25)

# Aquí juegas con los números (X, Y)
draw.text((510, 430), "Fabio Saavedra Garcia", font=font_nombre, fill="#000000", anchor="mm")
draw.text((520, 520), "ÁREA DE TECNOLOGIA DE LA INFORMACIÓN", font=font_proyecto, fill="#000000", anchor="mm")

# Fecha en la esquina del calendario (ajusta X, Y según tu imagen)
meses = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
dia = 5  # Cambia el día aquí
mes = 'Marzo'  # O usa: mes = meses[3]

draw.text((940, 70), str(dia), font=font_fecha, fill="#000000", anchor="mm")
draw.text((940, 90), mes, font=font_fecha, fill="#000000", anchor="mm")

# Esto abrirá la imagen en tu pantalla al instante para que veas cómo quedó
img.show()