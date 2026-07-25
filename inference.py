# inference.py - FIXED with proper JSON serialization + singleton model caching
import json
import os
import sys
import warnings
import cv2
import numpy as np
from PIL import Image
import io
import tempfile
warnings.filterwarnings('ignore')

from decision_engine import DecisionEngine

class ImageClassifier:
    def __init__(self, model_weight=0.7, forensic_weight=0.3, auto_fix=True):
        self.engine = DecisionEngine(model_weight, forensic_weight)
        self.auto_fix = auto_fix
        self.temp_files = []
        print(f"Image Classifier initialized! (Auto-fix: {auto_fix})")
    
    def __del__(self):
        """Clean up temporary files"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
    
    def detect_compression(self, image_path):
        """Detect if image is over-compressed"""
        try:
            file_size = os.path.getsize(image_path) / 1024  # KB
            
            img = cv2.imread(image_path)
            if img is None:
                return {'is_compressed': False, 'ratio': 0}
            
            h, w = img.shape[:2]
            expected_size = (h * w * 3) / 1024
            compression_ratio = expected_size / file_size if file_size > 0 else 0
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            block_size = 8
            artifacts = 0
            blocks = 0
            
            for i in range(0, h - block_size + 1, block_size):
                for j in range(0, w - block_size + 1, block_size):
                    block = gray[i:i+block_size, j:j+block_size].astype(np.float32)
                    dct_block = cv2.dct(block)
                    zeros = np.sum(np.abs(dct_block) < 0.5)
                    if zeros > 10:
                        artifacts += 1
                    blocks += 1
            
            artifact_ratio = artifacts / blocks if blocks > 0 else 0
            is_compressed = (compression_ratio > 5 or artifact_ratio > 0.3 or file_size < 100)
            
            return {
                'is_compressed': bool(is_compressed),
                'compression_ratio': float(compression_ratio),
                'artifact_ratio': float(artifact_ratio),
                'file_size_kb': float(file_size),
                'severity': 'high' if compression_ratio > 15 else 'medium' if compression_ratio > 8 else 'low'
            }
        except Exception as e:
            print(f"Compression detection error: {e}")
            return {'is_compressed': False, 'error': str(e)}
    
    def fix_compression(self, image_path):
        """Fix over-compressed images"""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return None
            
            print("  🔧 Fixing compression artifacts...")
            
            img = cv2.fastNlMeansDenoisingColored(img, None, 8, 8, 7, 21)
            kernel = np.array([[0, -0.5, 0], [-0.5, 3, -0.5], [0, -0.5, 0]])
            img = cv2.filter2D(img, -1, kernel)
            noise = np.random.normal(0, 1.5, img.shape).astype(np.uint8)
            img = cv2.add(img, noise)
            
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            l = cv2.equalizeHist(l)
            lab = cv2.merge([l, a, b])
            img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            temp_path = temp_file.name
            temp_file.close()
            
            cv2.imwrite(temp_path, img)
            self.temp_files.append(temp_path)
            
            print(f"  ✅ Compression fixed: {os.path.basename(temp_path)}")
            
            return temp_path
            
        except Exception as e:
            print(f"  ❌ Fix failed: {e}")
            return None
    
    def run_detection(self, file_path, verbose=True):
        """Main detection with auto compression handling"""
        if not os.path.exists(file_path):
            return {
                'error': 'File not found',
                'ai_probability': 0.0,
                'verdict': 'Error'
            }
        
        try:
            if verbose:
                print(f"\n{'='*60}")
                print(f"📸 Analyzing: {os.path.basename(file_path)}")
                print(f"{'='*60}")
            
            compression_info = self.detect_compression(file_path)
            
            if verbose:
                print(f"📊 File size: {compression_info.get('file_size_kb', 0):.1f} KB")
                print(f"📊 Compression ratio: {compression_info.get('compression_ratio', 0):.1f}x")
                if compression_info.get('is_compressed'):
                    print(f"⚠️  Over-compressed detected! Severity: {compression_info.get('severity', 'unknown')}")
            
            image_to_process = file_path
            if self.auto_fix and compression_info.get('is_compressed'):
                fixed_path = self.fix_compression(file_path)
                if fixed_path and os.path.exists(fixed_path):
                    image_to_process = fixed_path
                    if verbose:
                        print("✅ Using fixed version for analysis")
                else:
                    if verbose:
                        print("⚠️  Could not fix compression, using original")
            
            result = self.engine.process_image(image_to_process, original_path=file_path)
            
            # Convert numpy types to Python types for JSON serialization
            result['ai_probability'] = float(result.get('ai_probability', 0))
            result['confidence_score'] = float(result.get('confidence_score', 0))
            result['compression_info'] = {
                'is_compressed': bool(compression_info.get('is_compressed', False)),
                'compression_ratio': float(compression_info.get('compression_ratio', 0)),
                'artifact_ratio': float(compression_info.get('artifact_ratio', 0)),
                'file_size_kb': float(compression_info.get('file_size_kb', 0)),
                'severity': str(compression_info.get('severity', 'low'))
            }
            
            if verbose:
                print(f"\n{'='*60}")
                print(f"🎯 Result: {result['verdict']}")
                print(f"🤖 AI Probability: {result['ai_probability']:.2f}")
                print(f"📊 Confidence: {result['confidence_score']:.2f}")
                print(f"{'='*60}")
            
            return result
            
        except Exception as e:
            import traceback
            print(f"Error during detection: {e}")
            traceback.print_exc()
            return {
                'error': str(e),
                'ai_probability': 0.0,
                'verdict': 'Error'
            }

# ----------------------------------------------------------------------
# SINGLETON: load the classifier (and its models) only ONCE per process,
# instead of re-creating it — and re-loading CLIP + SDXL — on every call.
# This is the fix for repeated "Loading models..." on every upload and
# the memory crash after a few images.
# ----------------------------------------------------------------------
_classifier_instance = None

def get_classifier():
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = ImageClassifier(auto_fix=True)
    return _classifier_instance

def detect_image(file_path, verbose=True):
    """Quick detection function - reuses a single cached classifier instance."""
    classifier = get_classifier()
    return classifier.run_detection(file_path, verbose)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        result = detect_image(sys.argv[1])
        print(json.dumps(result, indent=2, default=str))
    else:
        print("Usage: python inference.py <image_path>")
