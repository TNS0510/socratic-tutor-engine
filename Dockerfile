# Use the official lightweight Python 3.12 image as our foundation
FROM python:3.12-slim

# Set the working environment folder inside the container
WORKDIR /app

# Copy our dependencies map list first to optimize Docker caching layers
COPY requirements.txt .

# Install all required fullstack dependencies globally inside the container
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire rest of our application directory into the container
COPY . .

# Expose port 8000 so the cloud router can communicate with FastAPI
EXPOSE 8000

# Launch Uvicorn bound to 0.0.0.0 so it accepts incoming internet requests
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]