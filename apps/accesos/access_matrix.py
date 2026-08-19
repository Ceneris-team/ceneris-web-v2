# CAV-185: matriz de grupos y plataformas permitidas.
#
# Clave: prefijo de URL (tal como aparece en `request.path`).
# Valor:
#   - lista de nombres de grupo -> solo esos grupos pueden entrar.
#   - None -> cualquier usuario autenticado puede entrar (sin filtro
#     de grupo), solo se exige sesion valida.
#
# Cualquier URL que no empiece con ninguno de estos prefijos queda
# fuera del alcance de este middleware (no se toca su comportamiento
# actual).
ACCESS_MATRIX = {
    '/admin/': ['Administrador'],
    '/recursoshumanos/': ['Recursos Humanos', 'Supervisores'],
    '/calidad/': ['Calidad'],
    '/metricas_ceneris/': None,
    '/api/': None,
}
