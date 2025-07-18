# Use an official Python runtime as a parent image
FROM python:3.13.5-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY main.py models.py requirements.txt /app/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Run main.py when the container launches
CMD ["python", "main.py"]