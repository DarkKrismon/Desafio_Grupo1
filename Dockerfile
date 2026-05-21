# Usamos una imagen oficial de Python ligera
FROM python:3.11-slim

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias para compilar algunas librerías
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalarlos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código de la API y la carpeta models
COPY . .

# Exponer el puerto que usará FastAPI
EXPOSE 8000

# Comando para arrancar el servidor
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]