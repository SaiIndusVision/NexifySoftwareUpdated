# Use an official Python runtime as a parent image
FROM python:3.10

# Set the working directory in the container
WORKDIR /app

# Copy only requirements.txt first to leverage Docker caching
COPY requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt 

# Copy the entire project after installing dependencies
COPY . /app/

# Collect static files
RUN python3 manage.py collectstatic --noinput

# Expose the port the app runs on
EXPOSE 8005

# Run the Django development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8005"]
