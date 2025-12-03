# predict_local.py
import tensorflow as tf
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import cv2
import os

# Load the model (cached for speed)
model_path = 'best_chest_xray_model.h5'
if not os.path.exists(model_path):
    print(f"❌ Model not found at {model_path}. Download it first!")
    exit()

model = tf.keras.models.load_model(model_path)
IMG_SIZE = 224  # Matches EfficientNetB0

def predict_image(image_path):
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return
    
    # Load & preprocess
    img = Image.open(image_path).convert('RGB')
    img_resized = img.resize((IMG_SIZE, IMG_SIZE))
    img_array = np.array(img_resized) / 255.0
    img_array = np.expand_dims(img_array, axis=0)

    # Predict
    pred = model.predict(img_array)[0][0]
    label = "PNEUMONIA" if pred > 0.5 else "NORMAL"
    confidence = pred if pred > 0.5 else 1 - pred

    print(f"Prediction: **{label}** (Confidence: {confidence:.1%})")

    # Simple Grad-CAM (focuses on suspicious areas)
    try:
        # Get last conv layer (adapt if needed: print(model.summary()) to check)
        last_conv_layer = model.get_layer('efficientnetb0').get_layer('top_conv')
        
        grad_model = tf.keras.models.Model(
            [model.inputs], [last_conv_layer.output, model.output]
        )
        
        with tf.GradientTape() as tape:
            conv_outputs, predictions = grad_model(img_array)
            loss = predictions[:, 0]
        
        grads = tape.gradient(loss, conv_outputs)
        pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
        
        conv_outputs = conv_outputs[0]
        heatmap = conv_outputs @ pooled_grads[..., tf.newaxis]
        heatmap = tf.squeeze(heatmap)
        heatmap = np.maximum(heatmap, 0) / tf.math.reduce_max(heatmap)
        
        # Resize & overlay
        heatmap = cv2.resize(heatmap.numpy(), (img.size[0], img.size[1]))
        heatmap_colored = cv2.applyColorMap(np.uint8(255 * heatmap), cv2.COLORMAP_JET)
        superimposed = cv2.addWeighted(np.array(img), 0.6, heatmap_colored, 0.4, 0)
        
        # Plot
        plt.figure(figsize=(15, 5))
        plt.subplot(1, 3, 1); plt.imshow(img); plt.title("Original"); plt.axis('off')
        plt.subplot(1, 3, 2); plt.imshow(heatmap, cmap='jet'); plt.title("Grad-CAM Heatmap"); plt.axis('off')
        plt.subplot(1, 3, 3); plt.imshow(superimposed); plt.title(f"{label} ({confidence:.1%})"); plt.axis('off')
        plt.tight_layout()
        plt.show()
    except Exception as e:
        print(f"Grad-CAM skipped (layer mismatch): {e}")
        plt.figure(figsize=(5, 5))
        plt.imshow(img)
        plt.title(f"Prediction: {label} ({confidence:.1%})")
        plt.axis('off')
        plt.show()

# Test it! Add your X-ray image here
predict_image("test_xray.jpg")  # Replace with your file