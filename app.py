from flask import Flask, render_template, request, redirect, url_for, session
from user import User  # Handles user login/registration
from firebase_config import db
import os
import cv2
import numpy as np
from PIL import Image
import pytesseract
import re

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Session Management
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Process image and extract words
def process_image(file_path):
    img = cv2.imread(file_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(gray, 225, 255, cv2.THRESH_BINARY_INV)[1]
    
    cnts, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    mask = np.zeros(img.shape[:2], np.uint8)

    for cnt in cnts:
        cv2.drawContours(mask, [cnt], -1, 255, -1)

    dst = cv2.bitwise_and(img, img, mask=mask)
    gray = cv2.cvtColor(dst, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 3)
    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

    scanned_file_name = os.path.join(UPLOAD_FOLDER, "processed.png")
    cv2.imwrite(scanned_file_name, dst)
    
    # OCR to extract text
    text = pytesseract.image_to_string(Image.open(scanned_file_name))
    
    # Process the extracted text
    processed_words = process_text(text)
    
    return processed_words


def process_text(text):
    # Convert text to lowercase
    text = text.lower()
    
    # Remove numbers and punctuations (keep only letters and spaces)
    text = re.sub(r'[^a-z\s]', '', text)
    
    # Split text into words
    words = text.split()
    
    # Remove duplicates by converting to set, then back to list
    unique_words = list(set(words))
    
    # Sort words alphabetically (optional)
    unique_words.sort()

    return unique_words

# Update user's word lists in Firestore
def update_word_lists(username, extracted_words):
    user_ref = db.collection('users').document(username)
    user_data = user_ref.get().to_dict()
    
    # Normalize and remove duplicates from existing lists
    known_words = set(word.lower() for word in user_data.get('known_words', []))
    unknown_words = set(word.lower() for word in user_data.get('unknown_words', []))
    
    # Process and normalize incoming words
    for word in extracted_words:
        word = word.lower()  # Ensure new words are lowercase
        if word not in known_words:
            unknown_words.add(word)  # Add only if not already known

    # Update Firestore with de-duplicated lists
    user_ref.update({
        'known_words': list(known_words),
        'unknown_words': list(unknown_words)  # Firestore doesn't support sets, so convert back to list
    })

    print("Word lists updated and duplicates removed.")


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if User.authenticate(username, password):
            session['user'] = username
            return redirect(url_for("dashboard"))
        else:
            return "Invalid credentials, please try again.", 401
    return render_template("index.html")

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if 'user' not in session:
        return redirect(url_for("index"))

    username = session['user']
    user_ref = db.collection('users').document(username)
    user_data = user_ref.get().to_dict()
    
    if request.method == "POST":
        file = request.files["file"]
        if file:
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(file_path)
            extracted_words = process_image(file_path)
            update_word_lists(username, extracted_words)
            
            return redirect(url_for("dashboard"))

    known_count = len(user_data.get('known_words', []))
    unknown_count = len(user_data.get('unknown_words', []))

    return render_template("dashboard.html", known_count=known_count, unknown_count=unknown_count)

@app.route("/logout")
def logout():
    session.pop('user', None)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
