FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY common ./common
COPY auth-service ./auth-service
ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["uvicorn", "main:app", "--app-dir", "auth-service", "--host", "0.0.0.0", "--port", "8000"]
