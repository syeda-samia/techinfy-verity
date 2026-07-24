import torch
import torch.nn.functional as F
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForImageClassification
import numpy as np

# CLIP permanently disabled for deployment
CLIP_AVAILABLE = False
clip = None

class ImageClassifier:
    def __init__(self, model_weight=0.7, forensic_weight=0.3, auto_fix=True):
        self.models = {}
        self.processors = {}
        self.device = "cpu"
        self.model_weight = model_weight
        self.forensic_weight = forensic_weight
        
        print("Loading models...")
        self.load_models()
        print("Models loaded successfully")
    
    def load_models(self):
        try:
            # SDXL Detector (main model)
            model_name = "Organika/sdxl-detector"
            self.processors["sdxl"] = AutoImageProcessor.from_pretrained(model_name)
            self.models["sdxl"] = AutoModelForImageClassification.from_pretrained(model_name)
            self.models["sdxl"].to(self.device)
            self.models["sdxl"].eval()
            print("✓ SDXL detector loaded")
            
            # CLIP disabled
            self.models["clip"] = None
            self.processors["clip"] = None
            print("⚠ CLIP disabled for deployment")
            
        except Exception as e:
            print(f"Error loading models: {e}")
            raise
    
    def preprocess_image(self, image):
        if isinstance(image, str):
            image = Image.open(image).convert("RGB")
        elif isinstance(image, Image.Image):
            image = image.convert("RGB")
        return image
    
    def predict_sdxl(self, image):
        """Get SDXL detector prediction"""
        try:
            inputs = self.processors["sdxl"](images=image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.models["sdxl"](**inputs)
                logits = outputs.logits
                probs = torch.nn.functional.softmax(logits, dim=-1)
                prob = probs[0][1].item()  # probability of being AI-generated
            
            return prob
        except Exception as e:
            print(f"SDXL prediction error: {e}")
            return 0.5
    
    def run_detection(self, image_path, verbose=False):
        """Run full detection pipeline"""
        try:
            image = self.preprocess_image(image_path)
            
            # Get SDXL prediction
            sdxl_score = self.predict_sdxl(image)
            
            # Simple confidence based on score
            confidence = abs(sdxl_score - 0.5) * 2  # 0-1 range
            confidence = min(1.0, confidence)
            
            if sdxl_score > 0.5:
                label = "AI Generated"
                raw_score = sdxl_score
            else:
                label = "Real/Original"
                raw_score = 1 - sdxl_score
            
            return {
                "label": label,
                "confidence": confidence,
                "raw_score": raw_score,
                "sdxl_score": sdxl_score,
                "model_used": "sdxl-detector",
                "is_ai": sdxl_score > 0.5
            }
            
        except Exception as e:
            print(f"Detection error: {e}")
            return {
                "label": "Error",
                "confidence": 0.0,
                "raw_score": 0.0,
                "error": str(e)
            }
