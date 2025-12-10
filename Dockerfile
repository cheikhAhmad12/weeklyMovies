# ==== Étape 1 : Base Python ====
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y build-essential curl git && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "flow.py"]
