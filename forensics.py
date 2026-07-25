# forensics.py - FIXED VERSION (no pyexifinfo dependency)
import cv2
import numpy as np
from PIL import Image, ImageChops, ImageStat
from PIL.ExifTags import TAGS
import os
import tempfile
from scipy.fftpack import dct
import warnings
warnings.filterwarnings('ignore')

class ImageForensics:
    def __init__(self):
        self.temp_files = []
    
    def __del__(self):
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
    
    def ela_analysis(self, image_path, quality=95):
        try:
            img = Image.open(image_path).convert('RGB')
            temp_path = tempfile.mktemp(suffix='.jpg')
            self.temp_files.append(temp_path)
            img.save(temp_path, 'JPEG', quality=quality)
            compressed = Image.open(temp_path)
            ela = ImageChops.difference(img, compressed)
            stat = ImageStat.Stat(ela)
            error_magnitude = sum(stat.mean) / 3.0
            ela_score = 1 - min(1, error_magnitude / 100)
            return {
                'score': float(ela_score), 
                'error_magnitude': float(error_magnitude),
                'status': 'success'
            }
        except Exception as e:
            return {'score': 0.5, 'error': str(e), 'status': 'failed'}
    
    def prnu_analysis(self, image_path):
        try:
            img = cv2.imread(image_path)
            if img is None:
                return {'score': 0.5, 'error': 'Could not load image', 'status': 'failed'}
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            kernel = np.array([[-1, -1, -1], [-1, 8, -1], [-1, -1, -1]])
            noise = cv2.filter2D(gray, -1, kernel)
            noise_variance = np.var(noise)
            ai_prob = 1 - min(1, noise_variance / 1000)
            return {
                'score': float(ai_prob),
                'noise_variance': float(noise_variance),
                'noise_mean': float(np.mean(noise)),
                'status': 'success'
            }
        except Exception as e:
            return {'score': 0.5, 'error': str(e), 'status': 'failed'}
    
    def cfa_analysis(self, image_path):
        try:
            img = cv2.imread(image_path)
            if img is None:
                return {'score': 0.5, 'error': 'Could not load image', 'status': 'failed'}
            b, g, r = cv2.split(img)
            r_g_corr = np.corrcoef(r.flatten(), g.flatten())[0, 1]
            b_g_corr = np.corrcoef(b.flatten(), g.flatten())[0, 1]
            if np.isnan(r_g_corr):
                r_g_corr = 0.5
            if np.isnan(b_g_corr):
                b_g_corr = 0.5
            expected_corr = 0.8
            corr_deviation = abs(r_g_corr - expected_corr) + abs(b_g_corr - expected_corr)
            ai_prob = min(1, corr_deviation / 2)
            return {
                'score': float(ai_prob),
                'r_g_correlation': float(r_g_corr),
                'b_g_correlation': float(b_g_corr),
                'status': 'success'
            }
        except Exception as e:
            return {'score': 0.5, 'error': str(e), 'status': 'failed'}
    
    def dct_analysis(self, image_path):
        try:
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return {'score': 0.5, 'error': 'Could not load image', 'status': 'failed'}
            h, w = img.shape
            dct_coeffs = []
            step = 8
            for i in range(0, h - step + 1, step):
                for j in range(0, w - step + 1, step):
                    patch = img[i:i+step, j:j+step].astype(np.float32)
                    dct_patch = dct(dct(patch.T, norm='ortho').T, norm='ortho')
                    dct_coeffs.append(dct_patch.flatten()[:16])
            if not dct_coeffs:
                return {'score': 0.5, 'error': 'No patches extracted', 'status': 'failed'}
            dct_coeffs = np.array(dct_coeffs)
            coeff_variance = np.var(dct_coeffs)
            ai_prob = min(1, coeff_variance / 100)
            return {
                'score': float(ai_prob),
                'coeff_variance': float(coeff_variance),
                'status': 'success'
            }
        except Exception as e:
            return {'score': 0.5, 'error': str(e), 'status': 'failed'}
    
    def chromatic_aberration_analysis(self, image_path):
        try:
            img = cv2.imread(image_path)
            if img is None:
                return {'score': 0.5, 'error': 'Could not load image', 'status': 'failed'}
            b, g, r = cv2.split(img)
            def get_edges(channel):
                return cv2.Canny(channel, 50, 150)
            r_edges = get_edges(r)
            g_edges = get_edges(g)
            b_edges = get_edges(b)
            r_sum = np.sum(r_edges)
            b_sum = np.sum(b_edges)
            if r_sum == 0 or b_sum == 0:
                return {'score': 0.5, 'error': 'No edges detected', 'status': 'failed'}
            rg_overlap = np.sum(np.logical_and(r_edges, g_edges)) / r_sum
            bg_overlap = np.sum(np.logical_and(b_edges, g_edges)) / b_sum
            overlap_deviation = abs(rg_overlap - bg_overlap)
            ai_prob = min(1, overlap_deviation)
            return {
                'score': float(ai_prob),
                'rg_overlap': float(rg_overlap),
                'bg_overlap': float(bg_overlap),
                'status': 'success'
            }
        except Exception as e:
            return {'score': 0.5, 'error': str(e), 'status': 'failed'}
    
    def lighting_consistency_analysis(self, image_path):
        try:
            img = cv2.imread(image_path)
            if img is None:
                return {'score': 0.5, 'error': 'Could not load image', 'status': 'failed'}
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            h, w = l.shape
            regions = []
            region_h = max(1, h // 3)
            region_w = max(1, w // 3)
            for i in range(0, h - region_h + 1, region_h):
                for j in range(0, w - region_w + 1, region_w):
                    region = l[i:i+region_h, j:j+region_w]
                    regions.append(np.mean(region))
            lighting_variance = np.var(regions)
            ai_prob = min(1, lighting_variance / 50)
            return {
                'score': float(ai_prob),
                'lighting_variance': float(lighting_variance),
                'region_means': [float(r) for r in regions],
                'status': 'success'
            }
        except Exception as e:
            return {'score': 0.5, 'error': str(e), 'status': 'failed'}
    
    def exif_analysis(self, image_path):
        """
        EXIF analysis using PIL only - NO external dependencies
        """
        try:
            img = Image.open(image_path)
            exifdata = img.getexif()
            
            if not exifdata:
                return {
                    'score': 0.5,
                    'has_metadata': False,
                    'message': 'No EXIF data found',
                    'status': 'failed'
                }
            
            # Extract EXIF data safely
            exif_dict = {}
            camera_make = 'Unknown'
            camera_model = 'Unknown'
            software = 'Unknown'
            has_gps = False
            
            for tag_id, value in exifdata.items():
                try:
                    tag_name = TAGS.get(tag_id, f"Tag_{tag_id}")
                    
                    # Convert value to string safely
                    if isinstance(value, bytes):
                        try:
                            value_str = value.decode('utf-8', errors='ignore')
                        except:
                            value_str = str(value)
                    else:
                        value_str = str(value)
                    
                    exif_dict[tag_name] = value_str
                    
                    # Check for camera info
                    if tag_name == 'Make':
                        camera_make = value_str
                    elif tag_name == 'Model':
                        camera_model = value_str
                    elif tag_name == 'Software':
                        software = value_str
                    elif 'GPS' in tag_name:
                        has_gps = True
                        
                except Exception:
                    continue
            
            if not exif_dict:
                return {
                    'score': 0.5,
                    'has_metadata': False,
                    'message': 'No usable EXIF data found',
                    'status': 'failed'
                }
            
            # Check for suspicious software
            suspicious_keywords = ['Photoshop', 'GIMP', 'Lightroom', 'Affinity', 
                                  'Paint', 'Editor', 'AI', 'Stable Diffusion', 
                                  'Midjourney', 'DALL-E', 'DeepFace', 'FaceApp']
            
            suspicious_fields = []
            for key, value in exif_dict.items():
                if isinstance(value, str):
                    value_lower = value.lower()
                    for keyword in suspicious_keywords:
                        if keyword.lower() in value_lower:
                            suspicious_fields.append(f"{key}: {value[:50]}")
                            break
            
            has_camera_info = camera_make != 'Unknown' or camera_model != 'Unknown'
            
            # Calculate score
            if has_camera_info and len(suspicious_fields) == 0:
                ai_prob = 0.05  # Likely real photo
            elif has_camera_info:
                ai_prob = max(0.1, min(0.6, len(suspicious_fields) / 3))
            else:
                ai_prob = min(0.7, 0.3 + len(suspicious_fields) / 3)
            
            if has_gps:
                ai_prob = max(0.1, ai_prob - 0.1)
            
            return {
                'score': float(ai_prob),
                'has_metadata': True,
                'has_camera_info': has_camera_info,
                'has_gps': has_gps,
                'suspicious_fields': suspicious_fields,
                'total_fields': len(exif_dict),
                'camera_make': camera_make,
                'camera_model': camera_model,
                'software': software,
                'status': 'success'
            }
            
        except Exception as e:
            return {
                'score': 0.5,
                'has_metadata': False,
                'message': f'EXIF extraction failed: {str(e)}',
                'status': 'failed'
            }
    
    def get_all_forensic_scores(self, image_path):
        """Get scores from all forensic checks"""
        results = {
            'ela': self.ela_analysis(image_path),
            'prnu': self.prnu_analysis(image_path),
            'cfa': self.cfa_analysis(image_path),
            'dct': self.dct_analysis(image_path),
            'chromatic_aberration': self.chromatic_aberration_analysis(image_path),
            'lighting_consistency': self.lighting_consistency_analysis(image_path),
            'exif': self.exif_analysis(image_path)
        }
        
        valid_scores = []
        successful_checks = []
        failed_checks = []
        
        for key, result in results.items():
            if result.get('status') == 'success' and 'score' in result:
                valid_scores.append(result['score'])
                successful_checks.append(key)
            else:
                failed_checks.append(key)
        
        if valid_scores:
            avg_score = np.mean(valid_scores)
        else:
            avg_score = 0.5
        
        return {
            'results': results,
            'average_ai_probability': float(avg_score),
            'successful_checks': len(successful_checks),
            'total_checks': len(results),
            'successful_check_names': successful_checks,
            'failed_check_names': failed_checks
        }

if __name__ == "__main__":
    print("Initializing Image Forensics...")
    forensics = ImageForensics()
    print("Forensics initialized successfully!")
