# Dockerfile

# 1. Usar una imagen base de Python oficial
FROM python:3.11-slim-bookworm

# 2. Configurar el entorno
ENV PYTHONUNBUFFERED 1
WORKDIR /app

# 3. Instalar dependencias del sistema operativo
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    # Dependencias para mysqlclient
    build-essential \
    pkg-config \
    default-libmysqlclient-dev \
    \
    # Dependencias completas para WeasyPrint
    libpango-1.0-0 \
    libcairo2 \
    libffi-dev \
    fontconfig \
    libcairo2-dev \
    libpango1.0-dev \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-xlib-2.0-dev \
    \
    # --- ¡PAQUETE DE FUENTES CORREGIDO Y MÁS ESTÁNDAR! ---
    # Instala fuentes como Liberation Sans, Serif, Mono (sustitutos de Arial, Times, Courier)
    fonts-liberation \
    \
    && \
    \
    # --- ¡COMANDO CLAVE AÑADIDO AQUÍ! ---
    # Fuerza la reconstrucción del caché de fuentes del sistema.
    # Esto ayuda a Pango/WeasyPrint a encontrar las fuentes rápidamente.
    fc-cache -fv && \
    \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV CACHE_BUSTER=1

# 4. Copiar e instalar requerimientos de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiar el resto del código
COPY . .

# 5b. Normalizar finales de linea del entrypoint y hacerlo ejecutable.
# El sed es defensivo: si el archivo llegara con CRLF (clonado en Windows), el
# shebang quedaria como "#!/usr/bin/env bash\r" y el contenedor no arrancaria.
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# 6. Exponer el puerto
EXPOSE 8000

# 7. Comando de inicio.
# El entrypoint corre migrate y collectstatic antes de levantar gunicorn.
CMD ["/app/entrypoint.sh"]