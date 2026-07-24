# models.py - UPDATED: CLIP + Organika/sdxl-detector (proper AI-vs-real model)
import torch
import torchvision.transforms as transforms
from PIL import Image
import numpy as np
import warnings
warnings.filterwarnings('ignore')

from transformers import pipeline

try:
    import clip
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False
    print("CLIP not available")


class ImageModels:
    def __init__(self, device="cpu"):
        self.device = device
        self.models = {}
        self.processors = {}
        self.load_models()

    def load_models(self):
        """Load all pretrained models"""
        print("Loading models...")

        # 1. CLIP
        if CLIP_AVAILABLE:
            try:
                self.models['clip'], self.processors['clip'] = clip.load("ViT-B/32", device=self.device)
                print("✓ CLIP loaded")
            except Exception as e:
                print(f"✗ CLIP loading failed: {e}")
                self.models['clip'] = None
        else:
            print("✗ CLIP not available")
            self.models['clip'] = None

        # 2. SDXL Detector (proper AI-vs-real trained model)
        try:
            self.models['sdxl_detector'] = pipeline(
                "image-classification",
                model="Organika/sdxl-detector"
            )
            print("✓ SDXL Detector loaded")
        except Exception as e:
            print(f"✗ SDXL Detector loading failed: {e}")
            self.models['sdxl_detector'] = None

        print("Model loading complete!")

    def preprocess_image(self, image_path):
        """Load and preprocess image for CLIP only.
        SDXL detector (transformers pipeline) takes the raw image path/PIL image directly."""
        try:
            image = Image.open(image_path).convert('RGB')
            orig_width, orig_height = image.size
            print(f"  Original: {orig_width}x{orig_height}")

            if self.models['clip'] is not None:
                clip_transform = transforms.Compose([
                    transforms.Resize(224),
                    transforms.CenterCrop(224),
                    transforms.ToTensor(),
                    transforms.Normalize((0.48145466, 0.4578275, 0.40821073),
                                         (0.26862954, 0.26130258, 0.27577711))
                ])
                clip_input = clip_transform(image).unsqueeze(0).to(self.device)
            else:
                clip_input = None

            return {
                'clip': clip_input,
                'pil_image': image
            }
        except Exception as e:
            print(f"Error preprocessing image: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_clip_score(self, image_tensor):
        if self.models['clip'] is None or image_tensor is None:
            return {'ai_probability': 0.5, 'error': 'CLIP not available'}

        try:
            text_prompts = [
                "A real photograph taken with a camera",
                "A realistic camera photo",
                "An AI generated image",
                "A fake image created by AI",
                "A digital artwork",
                "A photograph of a real scene"
            ]

            text_tokens = clip.tokenize(text_prompts).to(self.device)

            with torch.no_grad():
                logits_per_image, _ = self.models['clip'](image_tensor, text_tokens)
                probs = logits_per_image.softmax(dim=-1).cpu().numpy()

            real_score = probs[0][0] + probs[0][1] + probs[0][5]
            ai_score = probs[0][2] + probs[0][3] + probs[0][4]

            real_score = real_score * 1.1
            total = real_score + ai_score

            if total > 0:
                ai_prob = ai_score / total
            else:
                ai_prob = 0.5

            ai_prob = 0.3 + (ai_prob * 0.4)

            return {
                'ai_probability': float(ai_prob),
                'confidence': float(max(probs[0])),
            }
        except Exception as e:
            print(f"CLIP error: {e}")
            return {'ai_probability': 0.5, 'error': str(e)}

    def get_sdxl_detector_score(self, pil_image):
        """Get AI probability from Organika/sdxl-detector.
        Returns labels 'human' (real) and 'artificial' (AI-generated)."""
        if self.models['sdxl_detector'] is None or pil_image is None:
            return {'ai_probability': 0.5, 'error': 'SDXL Detector not available'}

        try:
            results = self.models['sdxl_detector'](pil_image)
            # results looks like: [{'label': 'human', 'score': 0.99}, {'label': 'artificial', 'score': 0.01}]
            scores = {r['label'].lower(): float(r['score']) for r in results}

            ai_prob = scores.get('artificial', 0.5)

            return {
                'ai_probability': float(ai_prob),
                'human_score': float(scores.get('human', 1 - ai_prob)),
                'artificial_score': float(ai_prob),
            }
        except Exception as e:
            print(f"SDXL Detector error: {e}")
            return {'ai_probability': 0.5, 'error': str(e)}

    def get_all_scores(self, image_path):
        """Get scores from all models.
        Both CLIP and SDXL Detector count toward the final average,
        with SDXL Detector as the primary, reliable signal."""
        inputs = self.preprocess_image(image_path)
        if inputs is None:
            return {
                'error': 'Failed to preprocess image',
                'average_ai_probability': 0.5,
                'scores': {}
            }

        scores = {}
        valid_scores = []
        failed_models = []

        # CLIP
        if self.models['clip'] is not None:
            scores['clip'] = self.get_clip_score(inputs['clip'])
            if 'ai_probability' in scores['clip'] and 'error' not in scores['clip']:
                valid_scores.append(scores['clip']['ai_probability'])
            else:
                failed_models.append('clip')

        # SDXL Detector (primary AI-detection signal)
        if self.models['sdxl_detector'] is not None:
            scores['sdxl_detector'] = self.get_sdxl_detector_score(inputs['pil_image'])
            if 'ai_probability' in scores['sdxl_detector'] and 'error' not in scores['sdxl_detector']:
                # Weight sdxl_detector more heavily by adding it twice
                # (simple way to bias the average toward the more reliable model)
                valid_scores.append(scores['sdxl_detector']['ai_probability'])
                valid_scores.append(scores['sdxl_detector']['ai_probability'])
            else:
                failed_models.append('sdxl_detector')

        if failed_models:
            print(f"  ⚠️ Failed models: {', '.join(failed_models)}")

        if valid_scores:
            avg_ai_prob = np.mean(valid_scores)
        else:
            avg_ai_prob = 0.5

        print(f"  Scores calculated: {len(valid_scores)} score(s) averaged (CLIP + SDXL Detector x2)")

        return {
            'scores': scores,
            'average_ai_probability': float(avg_ai_prob),
            'models_used': len(valid_scores)
        }


if __name__ == "__main__":
    print("Initializing Image Models...")
    try:
        model = ImageModels()
        print("\nModels initialized successfully!")
    except Exception as e:
        print(f"Error initializing models: {e}")