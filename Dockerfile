FROM node:22-slim AS frontend-build

WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY frontend/index.html ./frontend/index.html
COPY --from=frontend-build /frontend/dist ./frontend/dist
COPY scripts ./scripts
COPY docs ./docs
COPY .env.example .

ENV PYTHONPATH=/app
ENV TRADING_MODE=DRY_RUN

CMD ["uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
