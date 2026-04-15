# Stage 1: Build Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./

# --- FIX: Force create utils.ts in case .dockerignore excluded the lib folder ---
RUN mkdir -p src/lib && \
    echo 'import { clsx, type ClassValue } from "clsx";' > src/lib/utils.ts && \
    echo 'import { twMerge } from "tailwind-merge";' >> src/lib/utils.ts && \
    echo 'export function cn(...inputs: ClassValue[]) {' >> src/lib/utils.ts && \
    echo '  return twMerge(clsx(inputs));' >> src/lib/utils.ts && \
    echo '}' >> src/lib/utils.ts
# --------------------------------------------------------------------------------

ENV VITE_API_URL=""
RUN npm run build

# Stage 2: Build Backend & Worker
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend and worker code
COPY backend/ ./backend/
COPY worker/ ./worker/

# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Set PYTHONPATH so worker can find backend/app
ENV PYTHONPATH=/app/backend:/app

# Create start script
COPY start.sh ./
RUN chmod +x start.sh

# Expose port
EXPOSE 8000

# Run the start script
CMD ["./start.sh"]