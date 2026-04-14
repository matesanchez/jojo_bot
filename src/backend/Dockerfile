FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY . .

# Copy prompts directory (relative to project root — handled by railway.toml build context)
# Note: run docker build from project root with: docker build -f src/backend/Dockerfile .
COPY prompts/ /app/prompts/

# Copy pre-built vector database
COPY chroma_db/ /app/chroma_db/

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
