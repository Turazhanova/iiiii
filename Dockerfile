# Use the official Python image from the Docker Hub
FROM python:3.8-slim

# Install the required system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    tesseract-ocr \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set the TESSDATA_PREFIX environment variable
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata/

# Download the Tesseract language data files
RUN wget -P /usr/share/tesseract-ocr/4.00/tessdata/ https://github.com/tesseract-ocr/tessdata_best/raw/main/kaz.traineddata
RUN wget -P /usr/share/tesseract-ocr/4.00/tessdata/ https://github.com/tesseract-ocr/tessdata_best/raw/main/rus.traineddata

# Set the working directory
WORKDIR /app

# Copy the requirements file into the image
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the image
COPY . .

# Command to run the application with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5008", "ident:app"]
