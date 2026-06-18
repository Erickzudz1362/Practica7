FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY common ./common
COPY sales-service ./sales-service
ENV PYTHONPATH=/app
EXPOSE 8005
CMD ["uvicorn", "main:app", "--app-dir", "sales-service", "--host", "0.0.0.0", "--port", "8005"]
