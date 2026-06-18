FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY common ./common
COPY customer-service ./customer-service
ENV PYTHONPATH=/app
EXPOSE 8004
CMD ["uvicorn", "main:app", "--app-dir", "customer-service", "--host", "0.0.0.0", "--port", "8004"]
