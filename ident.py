import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import cv2
import numpy as np
import matplotlib.pyplot as plt
import re
import os
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# Path to your Tesseract executable (local path, not needed on Railway)
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

def preprocess_image(image):
    gray_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh_img = cv2.threshold(gray_img, 150, 255, cv2.THRESH_BINARY)
    kernel = np.ones((1, 1), np.uint8)
    processed_img = cv2.morphologyEx(thresh_img, cv2.MORPH_CLOSE, kernel)
    height, width = processed_img.shape
    new_height = int(height * 1.5)
    new_width = int(width * 1.5)
    resized_img = cv2.resize(processed_img, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
    return resized_img

def display_image(img):
    plt.imshow(img, cmap='gray')
    plt.axis('off')
    plt.show()

def extract_text(image):
    config = '--psm 6'  # Assume a single uniform block of text
    extracted_text = pytesseract.image_to_string(image, lang='kaz+rus', config=config)
    return extracted_text

def process_pdf_file(file_path):
    extracted_text = ''
    if file_path.lower().endswith('.pdf'):
        pdf_document = fitz.open(file_path)
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img_cv = np.array(img)
            preprocessed_img = preprocess_image(img_cv)
            page_text = extract_text(preprocessed_img)
            extracted_text += page_text
        pdf_document.close()
    elif file_path.lower().endswith(('.jpeg', '.jpg', '.png', '.bmp')):
        img = cv2.imread(file_path)
        preprocessed_img = preprocess_image(img)
        extracted_text = extract_text(preprocessed_img)
    else:
        print("Unsupported file format.")
        return extracted_text
    return extracted_text

def extract_dates_numbers(text):
    date_pattern = re.compile(r'\b\d{1,2}[\./-]\d{1,2}[\./-]\d{2,4}\b')
    number_pattern = re.compile(r'\b\d{9}\b|\b\d{12}\b')
    dates = date_pattern.findall(text)
    numbers = number_pattern.findall(text)
    return dates, numbers

def classify_numbers(numbers):
    inn = None
    id_number = None
    for number in numbers:
        if len(number) == 12:
            inn = number
        elif len(number) == 9:
            id_number = number
    return inn, id_number

def extract_names(text):
    surname_pattern = re.compile(r'\b\w+(ова|ева|ево|ово)\b', re.IGNORECASE)
    patronymic_pattern = re.compile(r'\b\w+(қызы|ұлы|овна|овно|евно|евна)\b', re.IGNORECASE)
    surname_match = surname_pattern.search(text)
    patronymic_match = patronymic_pattern.search(text)
    surname = surname_match.group() if surname_match else None
    patronymic = patronymic_match.group() if patronymic_match else None
    name = None
    if surname:
        name_pattern = re.compile(r'\b[А-ЯЁ][а-яё]+\b', re.IGNORECASE)
        name_candidates = name_pattern.findall(text)
        surname_index = text.find(surname)
        surname_words = text[surname_index:].split()
        if len(surname_words) > 2:
            name = ' '.join(surname_words[1:3])
    return surname, name, patronymic

def detect_document_type(text):
    keywords = ["ЖЕКЕ", "КУӘЛІК", "УДОСТОВЕРЕНИЕ", "ЛИЧНОСТИ"]
    for keyword in keywords:
        if keyword in text.upper():
            return "тип документа: УДОСТОВЕРЕНИЕ ЛИЧНОСТИ"
    return "тип документа: Неизвестно"

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file:
        file_path = os.path.join("/tmp", file.filename)
        file.save(file_path)
        extracted_text = process_pdf_file(file_path)
        dates, numbers = extract_dates_numbers(extracted_text)
        inn, id_number = classify_numbers(numbers)
        surname, name, patronymic = extract_names(extracted_text)
        document_type = detect_document_type(extracted_text)
        if len(dates) >= 2 and inn and id_number:
            issue_date = dates[0] if len(dates) > 0 else None
            expiry_date = dates[1] if len(dates) > 1 else None
            response = {
                "extracted_text": extracted_text,
                "document_type": document_type,
                "issue_date": issue_date,
                "expiry_date": expiry_date,
                "INN": inn,
                "ID_number": id_number,
                "surname": surname,
                "name": name,
                "patronymic": patronymic
            }
        else:
            response = {"error": "Пожалуйста, загрузите изображение в хорошем качестве."}
        os.remove(file_path)
        return jsonify(response), 200
    return jsonify({"error": "Unexpected error"}), 500

@app.route('/')
def index():
    return render_template('ident.html')

if __name__ == '__main__':
    app.run(debug=True)
