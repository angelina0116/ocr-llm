from flask import Flask, render_template, request, redirect, url_for, session
from user import User  # Assuming user.py handles Firestore user registration/login
import os
import cv2
import numpy as np
from PIL import Image
import pytesseract

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # For session management
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def process_image(file_path):
    img = cv2.imread(file_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(gray, 225, 255, cv2.THRESH_BINARY_INV)[1]
    
    cnts, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    H, W = img.shape[:2]

    for cnt in cnts:
        x, y, w, h = cv2.boundingRect(cnt)
        if cv2.contourArea(cnt) > 100 and (0.7 < w/h < 1.3) and (W/4 < x + w//2 < W*3/4) and (H/4 < y + h//2 < H*3/4):
            break
    
    mask = np.zeros(img.shape[:2], np.uint8)
    cv2.drawContours(mask, [cnt], -1, 255, -1)
    dst = cv2.bitwise_and(img, img, mask=mask)

    gray = cv2.cvtColor(dst, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 3)
    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

    scanned_file_name = os.path.join(UPLOAD_FOLDER, "processed.png")
    cv2.imwrite(scanned_file_name, dst)

    text = pytesseract.image_to_string(Image.open(scanned_file_name))
    return text


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

    if request.method == "POST":
        file = request.files["file"]
        if file:
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(file_path)

            extracted_text = process_image(file_path)
            return render_template("dashboard.html", text=extracted_text)
    return render_template("dashboard.html")


@app.route("/logout")
def logout():
    session.pop('user', None)
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
