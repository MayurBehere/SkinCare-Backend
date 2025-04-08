# ml_model/classifier.py

import numpy as np
from tensorflow import keras
from tensorflow.keras.preprocessing import image
import os

# Load model globally once
model_path = os.path.join(os.path.dirname(__file__), "do7.keras")
model = keras.models.load_model(model_path)

# Class labels
class_labels = ["Acne", "Keratosis", "Milia"]

# Preprocess image
def preprocess(img_path):
    img = image.load_img(img_path, target_size=(224, 224))
    img_array = image.img_to_array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    return img_array

# Predict
def classify_image(img_path):
    img = preprocess(img_path)
    preds = model.predict(img)
    idx = np.argmax(preds)
    return {
        "acne_type": class_labels[idx],
        "confidence": float(preds[0][idx])
    }
