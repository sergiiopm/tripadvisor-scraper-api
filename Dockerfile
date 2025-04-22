FROM python:3.12-slim

WORKDIR /app

# Copiamos y instalamos dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && python -m playwright install --with-deps chromium

# Copiamos el código de la aplicación
COPY app/ ./app

EXPOSE 3000

# Arrancamos Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3000"]
