import os
import numpy as np
import requests
from io import BytesIO
from PIL import Image
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader

# === Paths ===
BASE_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(BASE_DIR, "do7.keras")
INDEX_PATH = os.path.join(BASE_DIR, "index_data")
PDF_FOLDER = os.path.join(BASE_DIR, "source_pdfs")
INDEX_NAME = "index"
INDEX_FILE = os.path.join(INDEX_PATH, f"{INDEX_NAME}.faiss")

# === Model + Labels ===
model = load_model(MODEL_PATH)
class_labels = ["Acne", "Keratosis", "Milia"]

# === Embedding + FAISS ===
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def load_documents_from_pdfs(pdf_folder):
    all_docs = []
    for filename in os.listdir(pdf_folder):
        if filename.endswith(".pdf"):
            loader = PyPDFLoader(os.path.join(pdf_folder, filename))
            pages = loader.load_and_split()
            all_docs.extend(pages)
    return all_docs

if os.path.exists(INDEX_FILE):
    print("✅ FAISS index found. Loading...")
    vector_store = FAISS.load_local(INDEX_PATH, embeddings=embedding_model, allow_dangerous_deserialization=True)
else:
    print("⚠️ FAISS index not found. Creating from PDFs...")
    docs = load_documents_from_pdfs(PDF_FOLDER)
    vector_store = FAISS.from_documents(docs, embedding_model)
    os.makedirs(INDEX_PATH, exist_ok=True)
    vector_store.save_local(INDEX_PATH)
    print("✅ New FAISS index created and saved.")

# === Image Preprocessing ===
def preprocess_image_url(image_url):
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content)).convert('RGB')
        img = img.resize((224, 224))
        img_array = img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0) / 255.0
        return img_array
    except Exception as e:
        raise RuntimeError(f"Error loading image from URL: {e}")

# === Acne Classification ===
def classify_image_url(image_url):
    img_array = preprocess_image_url(image_url)
    preds = model.predict(img_array)
    idx = np.argmax(preds)
    return {
        "acne_type": class_labels[idx],
        "confidence": float(preds[0][idx])
    }

# === Mistral Integration ===
def get_recommendation(acne_type):
    query = f"What is {acne_type}? List the ingredients, products and selfcare tips for {acne_type}."

    results = vector_store.similarity_search(query, k=4)
    context = "\n\n".join([doc.page_content for doc in results])

    prompt = f"""You are a helpful assistant. Based on the following context, answer the question.

Context:
{context}

Question: {query}

Answer:"""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "mistral", "prompt": prompt, "stream": False}
        )
        response.raise_for_status()
        return response.json().get("response", "No answer generated.")
    except Exception as e:
        raise RuntimeError(f"Recommendation fetch failed: {e}")

# === Final Function ===
def classify_and_recommend(image_url):
    result = classify_image_url(image_url)
    recommendation = get_recommendation(result["acne_type"])
    return {
        "classification": result,
        "recommendation": recommendation,
        "image_url": image_url
    }
