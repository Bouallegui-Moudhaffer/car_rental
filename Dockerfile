FROM python:3.10-slim

WORKDIR /app

# Install system deps for MySQLdb, WeasyPrint dependencies + openssl
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    pkg-config \
    default-libmysqlclient-dev \
    libffi-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    fonts-freefont-ttf \
    curl \
    openssl \
  && rm -rf /var/lib/apt/lists/*

# Copy & install Python deps
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source and entrypoint
COPY app        ./
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 5000

# Use entrypoint to ensure SECRET_KEY is set, then launch
ENTRYPOINT ["entrypoint.sh"]
CMD ["python", "main.py"]
