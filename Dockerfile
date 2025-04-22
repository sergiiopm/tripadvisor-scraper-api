# Usa Python 3.12 slim
FROM python:3.12-slim

WORKDIR /app

# Instala dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el código de la app
COPY app/ ./app

# Exponer puerto 3000
EXPOSE 3000

# Comando por defecto
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3000"]
