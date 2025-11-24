


from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import pandas as pd
import joblib
from tensorflow.keras.models import load_model
import numpy as np
from PIL import Image
import io
import os
import warnings


# -------------------- Config --------------------


warnings.filterwarnings("ignore", category=UserWarning)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# -------------------- Paths --------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NUMERIC_MODEL_PATH = os.path.join(BASE_DIR, "rf_numeric_demo.joblib")
CNN_MODEL_PATH = os.path.join(BASE_DIR, "image_model.h5")  # Keep your image model path

# -------------------- FastAPI Init --------------------
app = FastAPI(title="Malnutrition Demo API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For demo, allow all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------- Load Models --------------------
if not os.path.exists(NUMERIC_MODEL_PATH):
    raise FileNotFoundError(f"Numeric demo model not found at: {NUMERIC_MODEL_PATH}")
if not os.path.exists(CNN_MODEL_PATH):
    raise FileNotFoundError(f"CNN model not found at: {CNN_MODEL_PATH}")

loaded_pipeline = joblib.load(NUMERIC_MODEL_PATH)
image_model = load_model(CNN_MODEL_PATH)
print("✅ Models loaded successfully!")

# -------------------- Label Map --------------------
label_map = {0: "Healthy", 1: "Stunted", 2: "Wasted", 3: "Underweight"}

# -------------------- Helper Functions --------------------
def predict_image(img_bytes):
    """Predict Malnourished or Normal from image"""
    try:
        img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        img = img.resize((224, 224))
        x = np.array(img) / 255.0
        x = np.expand_dims(x, axis=0)
        preds = image_model.predict(x, verbose=0)[0][0]
        return "Malnourished" if preds < 0.5 else "Normal"
    except Exception as e:
        print(f"❌ Prediction error: {e}")
        return "Unknown"

# -------------------- API Endpoint --------------------
@app.post("/PredictFull")
async def predict_full(
    file: UploadFile = File(...),
    Sex: str = Form(None),
    Age: str = Form(None),
    Height: str = Form(None),
    Weight: str = Form(None)
):
    try:
        # Image prediction
        img_bytes = await file.read()
        image_result = predict_image(img_bytes)

        # If image is normal, no need for numeric prediction
        if image_result == "Normal":
            return {
                "status": "success",
                "Image Prediction": image_result,
                "Numeric Prediction": None,
                "Advice": "Child appears healthy. Maintain balanced diet and regular check-ups."
            }

        # Numeric data check
        if None in [Sex, Age, Height, Weight]:
            return {
                "status": "incomplete",
                "Image Prediction": image_result,
                "Numeric Prediction": None,
                "Advice": "Malnourished detected. Please provide Age, Sex, Height, and Weight."
            }

        # Convert numeric inputs
        try:
            Age = int(Age)
            Height = float(Height)
            Weight = float(Weight)
        except ValueError:
            return {"status": "error", "error": "Invalid input types for Age/Height/Weight."}

        # Encode sex
        sex_code = 1 if Sex.lower() == "male" else 0

        # Prepare dataframe for numeric model
        input_df = pd.DataFrame([{
            "Sex": sex_code,
            "Age": Age,
            "Height": Height,
            "Weight": Weight
        }])

        # Predict numeric malnutrition
        numeric_pred = loaded_pipeline.predict(input_df)[0]
        label = label_map.get(numeric_pred, "Unknown")

        advice_map = {
            "Healthy": "✅ Continue good health practices and regular checkups.",
            "Stunted": "⚠️ Child shows stunting. Consult pediatrician and follow nutrition plan.",
            "Wasted": "⚠️ Child shows wasting. Consult pediatrician and follow nutrition plan.",
            "Underweight": "⚠️ Child is underweight. Consult pediatrician and follow nutrition plan.",
            "Unknown": "⚠️ Unable to determine numeric malnutrition."
        }

        return {
            "status": "success",
            "Image Prediction": image_result,
            "Numeric Prediction": label,
            "Advice": advice_map[label]
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}

# -------------------- Root Endpoint --------------------
@app.get("/")
def read_root():
    return {"message": "✅ Malnutrition Demo API is running!"}

# -------------------- Run Server --------------------
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
