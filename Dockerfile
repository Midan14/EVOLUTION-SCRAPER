FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium

# Copy source code
COPY src/ ./src/
COPY run.py .
COPY pyproject.toml .

# Create necessary directories
RUN mkdir -p data logs browser_data

# Set environment variables
ENV PYTHONPATH=/app
ENV HEADLESS=true
ENV DATABASE_PATH=data/results.db
ENV LOG_FILE=logs/scraper.log

# Expose API port
EXPOSE 8899

# Run the application
CMD ["python3", "run.py", "--headless"]
