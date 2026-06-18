FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY common ./common
COPY product-service ./product-service
ENV PYTHONPATH=/app
EXPOSE 8002
CMD ["uvicorn", "main:app", "--app-dir", "product-service", "--host", "0.0.0.0", "--port", "8002"]
