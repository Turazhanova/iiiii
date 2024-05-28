FROM python:3.8-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Install Tesseract
RUN apt-get update && apt-get install -y tesseract-ocr

COPY . .

CMD ["python", "ident.py"]
