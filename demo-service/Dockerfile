FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY common ./common
COPY demo-service ./demo-service
ENV PYTHONPATH=/app
EXPOSE 8007
CMD ["uvicorn", "main:app", "--app-dir", "demo-service", "--host", "0.0.0.0", "--port", "8007"]
