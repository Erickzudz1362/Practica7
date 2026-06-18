FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY common ./common
COPY notification-service ./notification-service
ENV PYTHONPATH=/app
EXPOSE 8006
CMD ["uvicorn", "main:app", "--app-dir", "notification-service", "--host", "0.0.0.0", "--port", "8006"]
