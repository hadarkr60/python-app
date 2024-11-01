# Use a minimal base image
FROM python:3.10-slim

# Set a secure working directory
WORKDIR /usr/src/flask_app

# Copy dependencies and install them
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create a non-root user and group, and adjust permissions
RUN groupadd -r flask && \
    useradd --no-log-init -r -g flask flask && \
    chown -R flask:flask /usr/src/flask_app

# Set environment variables
ENV FLASK_APP=weather.py \
    FLASK_RUN_HOST=0.0.0.0 

# Expose only the necessary port
EXPOSE 5000

# Switch to the non-root user
USER flask

# Command to start the Flask application
CMD ["flask", "run"]
