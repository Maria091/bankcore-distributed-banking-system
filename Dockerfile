FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir . psycopg[binary]
EXPOSE 8000
# Local-only educational setup, not a production image.
CMD ["uvicorn", "bankcore.api:app", "--host", "0.0.0.0", "--port", "8000"]
