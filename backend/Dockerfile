FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libgomp1 && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt backend/requirements-ocr.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements-ocr.txt
COPY backend ./backend
COPY docs/business-rules.md ./docs/business-rules.md
ENV KTV_DATA_DIR=/app/data
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
