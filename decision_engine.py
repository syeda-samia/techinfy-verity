# decision_engine.py - FIXED with better thresholds for real images
import numpy as np
from models import ImageModels
from forensics import ImageForensics

class DecisionEngine:
    def __init__(self, model_weight=0.6, forensic_weight=0.4):
        """
        Initialize decision engine with weights
        Lower model weight to reduce false positives on real images
        """
        self.model_weight = model_weight
        self.forensic_weight = forensic_weight
        self.models = ImageModels()
        self.forensics = ImageForensics()
        
    def combine_scores(self, model_scores, forensic_scores):
        """
        Combine model and forensic scores using weighted average
        """
        # Get average model probability
        model_ai_prob = model_scores.get('average_ai_probability', 0.5)
        
        # Get average forensic probability
        forensic_ai_prob = forensic_scores.get('average_ai_probability', 0.5)
        
        # Weighted combination
        combined_prob = (self.model_weight * model_ai_prob + 
                        self.forensic_weight * forensic_ai_prob)
        
        # Calculate confidence
        model_probs = []
        for model in model_scores.get('scores', {}):
            score_data = model_scores['scores'][model]
            if isinstance(score_data, dict):
                prob = score_data.get('ai_probability')
                if prob is not None and 'error' not in score_data:
                    model_probs.append(float(prob))
        
        if len(model_probs) > 1:
            confidence = 1 - np.std(model_probs)
            confidence = float(max(0.3, min(0.95, confidence)))
        else:
            confidence = 0.5
        
        # ADJUSTED THRESHOLDS - More forgiving for real images
        # AI probability should be > 60% to be considered AI
        if combined_prob < 0.30:  # Lowered from 0.35
            verdict = "Real Image"
            confidence_adjust = 0.1
        elif combined_prob < 0.45:  # Lowered from 0.50
            verdict = "Probably Real"
            confidence_adjust = 0.0
        elif combined_prob < 0.60:  # Increased from 0.55
            verdict = "Uncertain"
            confidence_adjust = -0.1
        elif combined_prob < 0.75:  # Increased from 0.70
            verdict = "Probably AI"
            confidence_adjust = -0.1
        else:
            verdict = "AI Generated"
            confidence_adjust = 0.1
        
        confidence = float(max(0.3, min(0.95, confidence + confidence_adjust)))
        model_agreement = bool(len(model_probs) > 2 and np.std(model_probs) < 0.15)
        
        return {
            'combined_probability': float(combined_prob),
            'model_probability': float(model_ai_prob),
            'forensic_probability': float(forensic_ai_prob),
            'confidence_score': confidence,
            'verdict': str(verdict),
            'model_agreement': model_agreement
        }
    
    def process_image(self, image_path, original_path=None):
        """
        Complete pipeline for image classification
        """
        if original_path is None:
            original_path = image_path

        print(f"Processing image: {image_path}")

        # Step 1: Get model scores
        print("Running models...")
        model_scores = self.models.get_all_scores(original_path)

        # Step 2: Get forensic scores (fixed image use karo)
        print("Running forensic checks...")
        forensic_scores = self.forensics.get_all_forensic_scores(image_path)

        # PRNU sirf ORIGINAL (bina noise wali) image par chalao
        # kyunke fix_compression() synthetic noise dalta hai jo PRNU ko confuse karta hai
        prnu_result = self.forensics.prnu_analysis(original_path)
        forensic_scores['results']['prnu'] = prnu_result

        # average dubara nikalo PRNU update hone ke baad
        valid_scores = [r['score'] for r in forensic_scores['results'].values() if r.get('status') == 'success']
        forensic_scores['average_ai_probability'] = float(np.mean(valid_scores)) if valid_scores else 0.5

        # Step 3: Combine scores
        print("Combining scores...")
        combined_result = self.combine_scores(model_scores, forensic_scores)

        # Step 4: Prepare final output
        result = {
            'type': 'image',
            'ai_probability': float(combined_result['combined_probability']),
            'confidence_score': float(combined_result['confidence_score']),
            'verdict': str(combined_result['verdict']),
            'model_agreement': bool(combined_result.get('model_agreement', False)),
            'forensic_details': {
                'model_scores': {},
                'forensic_checks': {},
                'weights': {
                    'model': float(self.model_weight),
                    'forensic': float(self.forensic_weight)
                }
            }
        }

        # Convert model scores
        for model_name, score_data in model_scores.get('scores', {}).items():
            if isinstance(score_data, dict):
                clean_score = {}
                for key, value in score_data.items():
                    if isinstance(value, np.ndarray):
                        clean_score[key] = value.tolist()
                    elif isinstance(value, np.floating):
                        clean_score[key] = float(value)
                    elif isinstance(value, np.integer):
                        clean_score[key] = int(value)
                    elif isinstance(value, bool):
                        clean_score[key] = bool(value)
                    elif isinstance(value, (int, float, str)):
                        clean_score[key] = value
                    elif value is None:
                        clean_score[key] = None
                    else:
                        try:
                            clean_score[key] = str(value)
                        except:
                            clean_score[key] = None
                result['forensic_details']['model_scores'][model_name] = clean_score

        # Convert forensic scores
        for check_name, check_data in forensic_scores.get('results', {}).items():
            if isinstance(check_data, dict):
                clean_check = {}
                for key, value in check_data.items():
                    if isinstance(value, np.ndarray):
                        clean_check[key] = value.tolist()
                    elif isinstance(value, np.floating):
                        clean_check[key] = float(value)
                    elif isinstance(value, np.integer):
                        clean_check[key] = int(value)
                    elif isinstance(value, bool):
                        clean_check[key] = bool(value)
                    elif isinstance(value, (int, float, str)):
                        clean_check[key] = value
                    elif value is None:
                        clean_check[key] = None
                    else:
                        try:
                            clean_check[key] = str(value)
                        except:
                            clean_check[key] = None
                result['forensic_details']['forensic_checks'][check_name] = clean_check

        return result
