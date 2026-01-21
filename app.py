from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import whisper
import tensorflow as tf
import numpy as np
import tempfile

app = Flask(__name__, static_folder='frontend', static_url_path='')
CORS(app)

@app.route('/')
def index():
    return app.send_static_file('index.html')

# Global variables for models
model = None
whisper_model = None
MODEL_PATH = os.path.join("models", "bilstm_fraud_model.h5")

def configure_ffmpeg():
    """Hashes out the location of ffmpeg if not in PATH."""
    # Common Winget install path pattern for this user
    # Found at: C:\Users\pradi\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin
    possible_paths = [
        os.path.join(os.environ['LOCALAPPDATA'], r"Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin"),
        os.path.join(os.environ['LOCALAPPDATA'], r"Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-7.0.1-full_build\bin"), # Fallback for versions
    ]
    
    # Add to PATH
    for p in possible_paths:
        if os.path.exists(p):
            print(f"Found FFmpeg at: {p}")
            os.environ["PATH"] += os.pathsep + p
            break

configure_ffmpeg()

def load_models():
    global model, whisper_model
    try:
        if os.path.exists(MODEL_PATH):
            model = tf.keras.models.load_model(MODEL_PATH)
            print("Fraud detection model loaded.")
        else:
            print(f"Warning: Model file {MODEL_PATH} not found. Using mock mode.")
            model = "MOCK"
        
        print("Loading Whisper model (base)...")
        whisper_model = whisper.load_model("base")
        print("Whisper model loaded.")
    except Exception as e:
        print(f"Error loading models: {e}")

# Load models on startup
load_models()
import time

@app.route('/api/analyze', methods=['POST'])
def analyze_audio():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
        
    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
            audio_file.save(temp_audio.name)
            temp_path = temp_audio.name

        # Transcribe
        start_time = time.time()
        result = whisper_model.transcribe(temp_path)
        transcription_time = time.time() - start_time
        print(f"Transcription took: {transcription_time:.2f}s")
        
        text = result["text"]
        
        # Keyword detection
        # Keyword detection
        # Keyword detection
        keywords = {
            # 1️⃣ Pure context — NEVER raise risk alone
            "context": [
                "bank", "account", "transaction", "balance", "statement",
                "branch", "customer care", "helpline", "service",
                "savings", "current", "credit", "debit"
            ],

            # 2️⃣ Credibility / impersonation cues (LOW risk alone)
            "impersonation": [
                "this is", "calling from", "speaking from",
                "bank manager", "relationship manager",
                "customer support", "official", "verified",
                "head office", "authorized"
            ],

            # 3️⃣ Sensitive data or action requests (HIGH risk)
            "sensitive": [
                "otp", "one time password", "cvv", "cvc",
                "pin", "atm pin", "mpin", "password",
                "net banking", "upi pin",
                "transfer", "send money", "refund",
                "install", "download", "anydesk", "teamviewer",
                "remote access", "screen share"
            ],

            # 4️⃣ Coercion / urgency / threat (VERY HIGH risk)
            "coercion": [
                "urgent", "immediately", "within minutes",
                "right now", "expires today", "last chance",
                "blocked in", "will be blocked",
                "suspend", "deactivate",
                "arrest", "jail", "legal action",
                "warrant", "police complaint",
                "fraud department"
            ]
        }
        
        lower_text = text.lower()
        detected_keywords = []
        for level, words in keywords.items():
            for word in words:
                if word in lower_text:
                    detected_keywords.append({"word": word, "level": level})

        # Calculate Score & Risk Level
        score_val = 0
        
        if model == "MOCK":
             # Base score logic for MOCK
             if any(k['level'] == 'sensitive' for k in detected_keywords) and any(k['level'] == 'coercion' for k in detected_keywords):
                score_val = 95 # Sensitive + Coercion = Very Critical
             elif any(k['level'] == 'coercion' for k in detected_keywords):
                score_val = 85
             elif any(k['level'] == 'sensitive' for k in detected_keywords):
                score_val = 75
             elif any(k['level'] == 'impersonation' for k in detected_keywords):
                score_val = 30 # Impersonation alone is suspicious but not critical
             elif any(k['level'] == 'context' for k in detected_keywords):
                score_val = 10 # Just context
             else:
                score_val = 5
        else:
            try:
                # Attempt to predict
                input_data = np.array([text])
                
                import logging
                logging.getLogger("tensorflow").setLevel(logging.ERROR)
                
                pred_start = time.time()
                prediction = model.predict(input_data)
                print(f"Prediction took: {time.time() - pred_start:.2f}s")
                
                # Model returns 0.0 to 1.0, convert to 0-100
                score_val = int(prediction[0][0] * 100)
                
            except Exception as e:
                print(f"Prediction Error (Handled): {e}")
                # Fallback logic based on keywords if model fails
                if any(k['level'] == 'sensitive' for k in detected_keywords) and any(k['level'] == 'coercion' for k in detected_keywords):
                    score_val = 95
                elif any(k['level'] == 'coercion' for k in detected_keywords):
                    score_val = 85
                elif any(k['level'] == 'sensitive' for k in detected_keywords):
                    score_val = 75
                else:
                    score_val = 15

        # Determine Risk Level
        risk_level = "Safe"
        if score_val >= 80:
            risk_level = "Critical"
        elif score_val >= 60:
            risk_level = "High Risk"
        elif score_val >= 40:
            risk_level = "Medium Risk"
        if score_val >= 20:
            risk_level = "Low Risk"


        # Cleanup
        os.remove(temp_path)

        return jsonify({
            'text': text,
            'fraud_score': score_val, # Now 0-100
            'risk_level': risk_level,
            'detected_keywords': detected_keywords,
            'is_fraud': score_val > 50
        })

    except Exception as e:
        import traceback
        traceback.print_exc() # Print to console
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
