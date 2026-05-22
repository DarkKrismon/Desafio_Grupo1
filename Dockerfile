FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# ATENCIÓN AQUÍ: Cambiamos al requirements de la API
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]