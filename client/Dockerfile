# Chess Game Client - Complete Independence
FROM python:3.11-slim

# Install system dependencies for OpenCV and GUI
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libfontconfig1 \
    libice6 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all client files
COPY *.py ./
COPY enums/ ./enums/
COPY sounds/ ./sounds/

# Set environment variable for display (for GUI)
ENV DISPLAY=:0

# Run client
CMD ["python", "networked_game_client.py"]
