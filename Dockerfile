FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy project files to the container
COPY . /app

# Install required Python dependencies
RUN pip install -r requirements.txt

# Expose the Flask port
EXPOSE 5000

# Command to run the Flask application
CMD ["python", "app.py"]
 
