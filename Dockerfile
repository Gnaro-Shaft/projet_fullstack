FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config ./config
COPY services ./services
COPY scripts ./scripts

EXPOSE 8000

CMD ["uvicorn", "services.main:app", "--host", "0.0.0.0", "--port", "8000"]
