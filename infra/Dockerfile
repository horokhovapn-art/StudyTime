FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ backend/
COPY frontend/ frontend/
ENV FRONTEND_DIR=/app/frontend DB_PATH=/data/studytime.db TZ=Europe/Kyiv
CMD ["sh","-c","uvicorn app:app --app-dir backend --host 0.0.0.0 --port ${PORT:-8000}"]
