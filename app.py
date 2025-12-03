# app.py
import os
import uuid
import random
import numpy as np
import cv2
import tensorflow as tf
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from config import Config

# Suppress TensorFlow OneDNN warning
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

app = Flask(__name__)
app.config.from_object(Config)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

mysql = MySQL(app)

# ------------------- AI MODEL (PNEUMONIA ONLY) -------------------
PNEUMONIA_MODEL_PATH = 'models/best_chest_xray_model.h5'

if not os.path.exists(PNEUMONIA_MODEL_PATH):
    raise FileNotFoundError(f"CRITICAL: Pneumonia model not found at {PNEUMONIA_MODEL_PATH}")

pneumonia_model = tf.keras.models.load_model(PNEUMONIA_MODEL_PATH)
print(f"Pneumonia model loaded: {PNEUMONIA_MODEL_PATH}")

PNEUMONIA_CLASSES = {0: "Normal", 1: "Pneumonia"}

# ------------------- QUOTES -------------------
QUOTES = [
    '"AI will be as common in healthcare as the stethoscope." – Robert Pearl',
    '"The greatest opportunity of AI is restoring the human touch." – Eric Topol',
    '"AI enhances physicians\' focus on personalized care." – Steven Lin',
    '"AI is the key to unlocking personalized medicine." – Healthcare 2018'
]

# ------------------- DECORATOR -------------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

# ------------------- ENHANCED GRAD-CAM (Pneumonia Only) -------------------
def get_gradcam(img_array):
    """
    Generate Grad-CAM heatmap for pneumonia detection
    Returns heatmap and intensity score
    """
    try:
        # Find last convolutional layer
        conv_layer = None
        for layer in reversed(pneumonia_model.layers):
            if 'conv' in layer.name.lower():
                conv_layer = layer
                break
        if not conv_layer:
            return None, 0

        grad_model = tf.keras.Model([pneumonia_model.inputs], [conv_layer.output, pneumonia_model.output])

        with tf.GradientTape() as tape:
            conv_out, preds = grad_model(img_array)
            class_score = preds[:, 0]  # Binary: Pneumonia probability

        grads = tape.gradient(class_score, conv_out)
        if grads is None:
            return None, 0

        pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
        conv_out = conv_out[0]
        heatmap = conv_out @ pooled_grads[..., tf.newaxis]
        heatmap = tf.squeeze(heatmap)
        heatmap = tf.maximum(heatmap, 0) / tf.math.reduce_max(heatmap)
        
        # Calculate intensity score (percentage of highly activated regions)
        intensity_score = float(tf.reduce_mean(heatmap).numpy())
        
        return heatmap.numpy(), intensity_score
    except Exception as e:
        print(f"Grad-CAM Error: {e}")
        return None, 0

def create_enhanced_overlay(original_img, heatmap, label, confidence, intensity_score):
    """
    Create an enhanced overlay with heatmap, bounding boxes, and annotations
    """
    # Convert PIL to numpy if needed
    if isinstance(original_img, Image.Image):
        original_img = np.array(original_img)
    
    img_height, img_width = original_img.shape[:2]
    
    # Resize heatmap to match original image
    heatmap_resized = cv2.resize(heatmap, (img_width, img_height))
    
    # Normalize heatmap
    heatmap_normalized = np.uint8(255 * heatmap_resized)
    
    # Apply custom colormap (red for high attention areas)
    heatmap_colored = cv2.applyColorMap(heatmap_normalized, cv2.COLORMAP_JET)
    
    # Create weighted overlay
    alpha = 0.5 if label == "Pneumonia" else 0.3
    overlay = cv2.addWeighted(original_img, 0.7, heatmap_colored, alpha, 0)
    
    # Find regions of high attention (potential affected areas)
    threshold = 0.6  # 60% of max activation
    high_attention_mask = heatmap_resized > threshold
    
    # Find contours of high attention regions
    contours, _ = cv2.findContours(
        high_attention_mask.astype(np.uint8), 
        cv2.RETR_EXTERNAL, 
        cv2.CHAIN_APPROX_SIMPLE
    )
    
    # Draw bounding boxes around high attention areas (only if pneumonia detected)
    if label == "Pneumonia" and len(contours) > 0:
        # Filter contours by area (remove very small regions)
        min_area = (img_width * img_height) * 0.01  # At least 1% of image
        significant_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]
        
        for i, contour in enumerate(significant_contours[:3]):  # Max 3 boxes
            x, y, w, h = cv2.boundingRect(contour)
            # Draw rectangle
            cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 255, 255), 3)
            # Add label
            label_text = f"ROI {i+1}"
            cv2.putText(overlay, label_text, (x, y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    
    # Convert to PIL for text annotation
    overlay_pil = Image.fromarray(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(overlay_pil)
    
    # Try to load a nice font, fallback to default
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Add header with diagnosis info
    header_height = 80
    header = Image.new('RGB', (img_width, header_height), color=(30, 41, 59))
    header_draw = ImageDraw.Draw(header)
    
    # Diagnosis text
    color = (239, 68, 68) if label == "Pneumonia" else (16, 185, 129)  # Red or Green
    try:
        header_draw.text((20, 15), f"Diagnosis: {label}", fill=color, font=font_large)
        header_draw.text((20, 50), f"Confidence: {confidence:.1f}% | Intensity: {intensity_score*100:.1f}%", 
                        fill=(255, 255, 255), font=font_small)
    except:
        header_draw.text((20, 15), f"Diagnosis: {label}", fill=color)
        header_draw.text((20, 45), f"Confidence: {confidence:.1f}%", fill=(255, 255, 255))
    
    # Add color scale legend
    legend_width = 200
    legend_height = 30
    legend_x = img_width - legend_width - 20
    legend_y = 25
    
    # Create gradient for legend
    for i in range(legend_width):
        intensity = int(255 * (i / legend_width))
        color_val = cv2.applyColorMap(np.array([[intensity]], dtype=np.uint8), cv2.COLORMAP_JET)[0][0]
        header_draw.rectangle(
            [legend_x + i, legend_y, legend_x + i + 1, legend_y + legend_height],
            fill=(int(color_val[2]), int(color_val[1]), int(color_val[0]))
        )
    
    try:
        header_draw.text((legend_x, legend_y - 20), "Attention Intensity", fill=(255, 255, 255), font=font_small)
        header_draw.text((legend_x, legend_y + legend_height + 5), "Low", fill=(255, 255, 255), font=font_small)
        header_draw.text((legend_x + legend_width - 30, legend_y + legend_height + 5), "High", 
                        fill=(255, 255, 255), font=font_small)
    except:
        pass
    
    # Combine header and overlay
    final_image = Image.new('RGB', (img_width, img_height + header_height))
    final_image.paste(header, (0, 0))
    final_image.paste(overlay_pil, (0, header_height))
    
    return final_image

# ------------------- ROUTES -------------------
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        pwd = generate_password_hash(request.form['password'])

        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM users WHERE username=%s OR email=%s", (username, email))
        if cur.fetchone():
            flash('Username or email already taken.', 'danger')
        else:
            cur.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", (username, email, pwd))
            mysql.connection.commit()
            flash('Registered! Please log in.', 'success')
            return redirect(url_for('login'))
        cur.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        pwd = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, username, password FROM users WHERE username=%s", (username,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[2], pwd):
            session['user_id'] = user[0]
            session['username'] = user[1]
            flash(f'Welcome back, {user[1]}!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    quote = random.choice(QUOTES)
    return render_template('dashboard.html', username=session['username'], quote=quote)

@app.route('/predict', methods=['POST'])
@login_required
def predict():
    file = request.files.get('image')
    if not file:
        return jsonify(error="No image uploaded"), 400

    # Save uploaded image
    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Preprocess
    img = Image.open(filepath).convert('RGB')
    orig_size = img.size
    img_resized = img.resize((224, 224))
    img_array = np.array(img_resized) / 255.0
    img_array = np.expand_dims(img_array, axis=0).astype(np.float32)

    # Predict
    pred = pneumonia_model.predict(img_array, verbose=0)[0]
    prob = float(pred[0])
    label = PNEUMONIA_CLASSES[1] if prob > 0.5 else PNEUMONIA_CLASSES[0]
    confidence = prob if prob > 0.5 else 1 - prob

    # Enhanced Grad-CAM Heatmap
    overlay_url = None
    heatmap, intensity_score = get_gradcam(img_array)
    
    if heatmap is not None:
        # Create enhanced overlay with annotations
        enhanced_overlay = create_enhanced_overlay(
            img, 
            heatmap, 
            label, 
            confidence * 100,
            intensity_score
        )
        
        # Save enhanced overlay
        overlay_filename = f"overlay_{filename}"
        overlay_path = os.path.join(app.config['UPLOAD_FOLDER'], overlay_filename)
        enhanced_overlay.save(overlay_path)
        overlay_url = f"/uploads/{overlay_filename}"

    # Cleanup original file
    os.remove(filepath)

    return jsonify(
        label=label,
        confidence=round(confidence * 100, 1),
        overlay_url=overlay_url,
        intensity_score=round(intensity_score * 100, 1)
    )

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)