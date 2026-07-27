# # fastapi_app.py - COMPLETE FIXED VERSION (Corrected Upload Box)
# from fastapi import FastAPI, File, UploadFile, HTTPException
# from fastapi.responses import JSONResponse, HTMLResponse
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# import os
# import shutil
# import uuid
# import sys
# import warnings
# from datetime import datetime
# from typing import Optional, List
# import uvicorn
# import traceback
# import json
# import numpy as np

# # Suppress warnings
# warnings.filterwarnings('ignore')

# # Force reload modules
# for module in ['forensics', 'models', 'decision_engine', 'inference']:
#     if module in sys.modules:
#         del sys.modules[module]

# from inference import detect_image

# app = FastAPI(
#     title="Techinfy Verity - Image Classifier API",
#     description="Detect AI-generated images using 4 vision models + 7 forensic checks",
#     version="2.0.0"
# )

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# UPLOAD_DIR = "uploads"
# os.makedirs(UPLOAD_DIR, exist_ok=True)

# class DetectionResponse(BaseModel):
#     filename: str
#     type: str
#     ai_probability: float
#     confidence_score: float
#     verdict: str
#     forensic_details: Optional[dict] = None
#     timestamp: str
#     test_id: Optional[str] = None
#     classification: Optional[str] = None
#     message: Optional[str] = None
#     model_agreement: Optional[bool] = None

# # HTML Interface (Fixed upload box layout)
# HTML_PAGE = """
# <!DOCTYPE html>
# <html>
# <head>
#     <meta charset="UTF-8">
#     <meta name="viewport" content="width=device-width, initial-scale=1.0">
#     <title>Techinfy Verity - Image Forensics</title>
#     <link rel="preconnect" href="https://fonts.googleapis.com">
#     <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
#     <style>
#         footer a:hover { color: #2DD4BF !important; }
    
#         * { margin: 0; padding: 0; box-sizing: border-box; }
#         body {
#             font-family: 'Segoe UI', Arial, sans-serif;
#             background: #0A0D12;
#             min-height: 100vh;
#             display: flex;
#             flex-direction: column;
#             justify-content: center;
#             align-items: center;
#             padding: 20px;
#         }
#         .topbar{
#             display:flex;
#             align-items:center;
#             justify-content:space-between;
#             padding:26px clamp(20px,5vw,56px);
#             border-bottom:1px solid #1C212C;
#             margin-bottom:24px;
#         }
#         .brand{ display:flex; align-items:center; gap:14px; }
#         .brand-mark{
#             width:42px; height:42px;
#             border:1.5px solid #2DD4BF;
#             border-radius:9px;
#             display:flex; align-items:center; justify-content:center;
#             font-size:22px;
#             flex-shrink:0;
#         }
#         .brand-name{
#             font-family:'Space Grotesk', sans-serif;
#             font-weight:700;
#             font-size:26px;
#             letter-spacing:0.01em;
#             color:#E7ECF4;
#         }
#         .brand-tag{
#             font-family:'IBM Plex Mono', monospace;
#             font-size:13px;
#             color:#8892A6;
#             letter-spacing:0.04em;
#             white-space:nowrap;
#             display:none;
#         }
#         @media (min-width:640px){ .brand-tag{ display:block; } }
#         .topbar-right{
#             font-family:'IBM Plex Mono', monospace;
#             font-size:13px;
#             color:#8892A6;
#             display:flex;
#             align-items:center;
#             gap:8px;
#             white-space:nowrap;
#             flex-shrink:0;
#         }
#         .dot{ width:7px; height:7px; border-radius:50%; background:#2DD4BF; box-shadow:0 0 8px #2DD4BF; }
#         .container {
#             max-width: 800px;
#             width: 100%;
#             background: #12161F;
#             padding: 40px;
#             border-radius: 16px;
#             border: 1px solid #232938;
#         }
#         h1 {
#             color: #E7ECF4;
#             font-size: 28px;
#             margin-bottom: 8px;
#         }
#         .accent { color: #2DD4BF; }
#         .subtitle {
#             color: #8892A6;
#             font-size: 15px;
#             margin-bottom: 30px;
#         }
#         .upload-area {
#             border: 2px dashed #232938;
#             padding: 50px;
#             text-align: center;
#             border-radius: 12px;
#             background: #171C26;
#             cursor: pointer;
#             transition: all .3s ease;
#         }
#         .upload-area:hover {
#             border-color: #2DD4BF;
#             background: rgba(45, 212, 191, 0.05);
#         }
#         .upload-area.dragover {
#             border-color: #2DD4BF;
#             background: rgba(45, 212, 191, 0.1);
#         }
#         input[type="file"] { 
#             display: none; 
#         }
#         .upload-icon { font-size: 48px; margin-bottom: 12px; }
#         .upload-text { color: #E7ECF4; font-size: 16px; margin-bottom: 4px; }
#         .upload-hint { color: #5B6478; font-size: 13px; }
#         .btn {
#             background: #2DD4BF;
#             color: #052420;
#             padding: 14px 32px;
#             border: none;
#             border-radius: 8px;
#             cursor: pointer;
#             font-size: 15px;
#             font-weight: 600;
#             margin-top: 16px;
#             transition: background .2s;
#             display: inline-block;
#         }
#         .btn:hover { background: #45E0CC; }
#         .btn:disabled { opacity: 0.5; cursor: not-allowed; }
#         .btn-wrapper {
#             text-align: center;
#         }
#         .loading {
#             display: none;
#             margin-top: 24px;
#             text-align: center;
#         }
#         .spinner {
#             border: 3px solid #232938;
#             border-top: 3px solid #2DD4BF;
#             border-radius: 50%;
#             width: 40px;
#             height: 40px;
#             animation: spin .8s linear infinite;
#             margin: 0 auto;
#         }
#         @keyframes spin {
#             0% { transform: rotate(0deg); }
#             100% { transform: rotate(360deg); }
#         }
#         .loading p {
#             color: #8892A6;
#             margin-top: 12px;
#             font-size: 14px;
#         }
#         .result {
#             display: none;
#             margin-top: 28px;
#             animation: fadeIn .4s ease;
#         }
#         @keyframes fadeIn {
#             from { opacity: 0; transform: translateY(16px); }
#             to { opacity: 1; transform: translateY(0); }
#         }
#         .verdict-box {
#             padding: 20px;
#             border-radius: 10px;
#             text-align: center;
#             margin-bottom: 16px;
#         }
#         .verdict-box.real {
#             background: rgba(45, 212, 191, 0.10);
#             border: 1px solid #2DD4BF;
#         }
#         .verdict-box.fake {
#             background: rgba(251, 91, 91, 0.10);
#             border: 1px solid #FB5B5B;
#         }
#         .verdict-box.uncertain {
#             background: rgba(245, 166, 35, 0.10);
#             border: 1px solid #F5A623;
#         }
#         .verdict-box.probably-real {
#             background: rgba(45, 212, 191, 0.05);
#             border: 1px solid #2DD4BF;
#         }
#         .verdict-box.probably-fake {
#             background: rgba(251, 91, 91, 0.05);
#             border: 1px solid #FB5B5B;
#         }
#         .verdict-label {
#             font-size: 24px;
#             font-weight: 700;
#         }
#         .verdict-box.real .verdict-label { color: #2DD4BF; }
#         .verdict-box.fake .verdict-label { color: #FB5B5B; }
#         .verdict-box.uncertain .verdict-label { color: #F5A623; }
#         .verdict-box.probably-real .verdict-label { color: #66D9C4; }
#         .verdict-box.probably-fake .verdict-label { color: #FB7B7B; }
#         .verdict-sub {
#             color: #8892A6;
#             font-size: 14px;
#             margin-top: 4px;
#         }
#         .model-agreement {
#             font-size: 12px;
#             margin-top: 8px;
#             padding: 4px 12px;
#             border-radius: 4px;
#             display: inline-block;
#         }
#         .model-agreement.warn {
#             color: #F5A623;
#             background: rgba(245, 166, 35, 0.1);
#         }
#         .model-agreement.good {
#             color: #2DD4BF;
#             background: rgba(45, 212, 191, 0.1);
#         }
#         .meta {
#             color: #5B6478;
#             font-size: 12px;
#             text-align: center;
#             margin-bottom: 16px;
#         }
#         .stats {
#             display: grid;
#             grid-template-columns: 1fr 1fr 1fr;
#             gap: 12px;
#             margin: 16px 0;
#         }
#         .stat-card {
#             background: #171C26;
#             border: 1px solid #1B2130;
#             border-radius: 8px;
#             padding: 16px;
#             text-align: center;
#         }
#         .stat-value {
#             font-size: 24px;
#             font-weight: 700;
#             color: #E7ECF4;
#         }
#         .stat-label {
#             color: #5B6478;
#             font-size: 11px;
#             text-transform: uppercase;
#             letter-spacing: 0.06em;
#             margin-top: 4px;
#         }
#         .prob-bar {
#             margin: 12px 0;
#         }
#         .prob-bar-label {
#             display: flex;
#             justify-content: space-between;
#             color: #8892A6;
#             font-size: 13px;
#             margin-bottom: 4px;
#         }
#         .prob-bar-track {
#             width: 100%;
#             height: 6px;
#             background: #1B2130;
#             border-radius: 3px;
#             overflow: hidden;
#         }
#         .prob-bar-fill {
#             height: 100%;
#             border-radius: 3px;
#             transition: width .6s ease;
#         }
#         .bar-real { background: #2DD4BF; }
#         .bar-fake { background: #FB5B5B; }
#         details {
#             margin-top: 16px;
#         }
#         summary {
#             cursor: pointer;
#             color: #8892A6;
#             font-size: 13px;
#             padding: 10px 14px;
#             background: #171C26;
#             border-radius: 6px;
#             border: 1px solid #1B2130;
#         }
#         summary:hover { border-color: #232938; }
#         pre {
#             background: #0A0D12;
#             color: #8892A6;
#             padding: 16px;
#             border-radius: 0 0 6px 6px;
#             overflow-x: auto;
#             font-size: 12px;
#             max-height: 300px;
#             overflow-y: auto;
#             border: 1px solid #1B2130;
#             border-top: none;
#         }
#         .error {
#             color: #FB5B5B;
#             padding: 16px;
#             background: rgba(251, 91, 91, 0.10);
#             border: 1px solid #FB5B5B;
#             border-radius: 8px;
#         }
#         .file-info {
#             color: #2DD4BF;
#             font-size: 14px;
#             margin-top: 8px;
#             display: none;
#         }
#         .file-info.show {
#             display: block;
#         }
#         @media (max-width: 600px) {
#             .stats { grid-template-columns: 1fr 1fr; }
#             .container { padding: 24px; }
#         }
#     </style>
# </head>
# <body>
#     <div class="container">
#         <div class="topbar">
#             <div class="brand">
#                 <div class="brand-mark">🔍</div>
#                 <div class="brand-name">Techinfy</div>
#                 <div class="brand-tag">/ image authenticity scanner</div>
#             </div>
#             <div class="topbar-right"><span class="dot"></span> models online</div>
#         </div>
#         <form id="uploadForm" enctype="multipart/form-data">
#             <div class="upload-area" id="dropZone">
#                 <div class="upload-icon">📸</div>
#                 <div class="upload-text" id="dzText">Drop your image here or click to browse</div>
#                 <div class="upload-hint" id="dzHint">JPG · PNG · BMP · TIFF · WEBP</div>
#                 <input type="file" name="file" id="fileInput" accept="image/*" required>
#                 <div class="file-info" id="fileInfo">📎 <span id="fileName"></span></div>
#             </div>
#             <div class="btn-wrapper">
#                 <button type="submit" class="btn" id="uploadBtn">🔍 Analyze Image</button>
#             </div>
#         </form>

#         <div id="loading" class="loading">
#             <div class="spinner"></div>
#             <p>Running models and forensic checks...</p>
#         </div>

#         <div id="result" class="result"></div>
#     </div>

#     <script>
#         const form = document.getElementById('uploadForm');
#         const fileInput = document.getElementById('fileInput');
#         const loading = document.getElementById('loading');
#         const resultDiv = document.getElementById('result');
#         const uploadBtn = document.getElementById('uploadBtn');
#         const dzText = document.getElementById('dzText');
#         const dzHint = document.getElementById('dzHint');
#         const fileInfo = document.getElementById('fileInfo');
#         const fileName = document.getElementById('fileName');
#         const dropZone = document.getElementById('dropZone');

#         // Click on drop zone triggers file input
#         dropZone.addEventListener('click', () => {
#             fileInput.click();
#         });

#         // File selected
#         fileInput.addEventListener('change', () => {
#             if (fileInput.files.length > 0) {
#                 const file = fileInput.files[0];
#                 dzText.textContent = '📎 File selected';
#                 dzHint.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
#                 fileName.textContent = file.name;
#                 fileInfo.classList.add('show');
#             } else {
#                 dzText.textContent = 'Drop your image here or click to browse';
#                 dzHint.textContent = 'JPG · PNG · BMP · TIFF · WEBP';
#                 fileInfo.classList.remove('show');
#             }
#         });

#         // Drag and drop support
#         dropZone.addEventListener('dragover', (e) => {
#             e.preventDefault();
#             dropZone.classList.add('dragover');
#         });

#         dropZone.addEventListener('dragleave', (e) => {
#             e.preventDefault();
#             dropZone.classList.remove('dragover');
#         });

#         dropZone.addEventListener('drop', (e) => {
#             e.preventDefault();
#             dropZone.classList.remove('dragover');
#             if (e.dataTransfer.files.length > 0) {
#                 fileInput.files = e.dataTransfer.files;
#                 fileInput.dispatchEvent(new Event('change'));
#             }
#         });

#         form.addEventListener('submit', async (e) => {
#             e.preventDefault();
#             if (!fileInput.files.length) {
#                 alert('Please select an image first.');
#                 return;
#             }

#             const formData = new FormData(form);
#             loading.style.display = 'block';
#             resultDiv.style.display = 'none';
#             uploadBtn.disabled = true;
#             uploadBtn.textContent = '⏳ Processing...';

#             try {
#                 const response = await fetch('/upload', {
#                     method: 'POST',
#                     body: formData
#                 });
#                 const data = await response.json();

#                 loading.style.display = 'none';
#                 resultDiv.style.display = 'block';
#                 uploadBtn.disabled = false;
#                 uploadBtn.textContent = '🔍 Analyze Image';

#                 if (data.error || !response.ok) {
#                     resultDiv.innerHTML = `<div class="error">❌ Error: ${data.error || data.detail || 'Something went wrong'}</div>`;
#                     return;
#                 }

#                 const aiProb = data.ai_probability || 0;
#                 const realProb = 1 - aiProb;
#                 const confidence = data.confidence_score || 0;
#                 const classification = data.classification || 'UNCERTAIN';
#                 const message = data.message || '';
#                 const modelAgreement = data.model_agreement;

#                 let verdictClass = 'uncertain';
#                 if (classification.includes('REAL IMAGE')) verdictClass = 'real';
#                 else if (classification.includes('PROBABLY REAL')) verdictClass = 'probably-real';
#                 else if (classification.includes('AI GENERATED')) verdictClass = 'fake';
#                 else if (classification.includes('PROBABLY AI')) verdictClass = 'probably-fake';

#                 resultDiv.innerHTML = `
#                     <div class="verdict-box ${verdictClass}">
#                         <div class="verdict-label">${classification}</div>
#                         <div class="verdict-sub">${message}</div>
#                         ${modelAgreement !== undefined ? 
#                             `<div class="model-agreement ${modelAgreement ? 'good' : 'warn'}">
#                                 ${modelAgreement ? '✅ Models agree on this result' : '⚠️ Models disagree - use caution'}
#                             </div>` : ''}
#                     </div>

#                     <div class="meta">📁 ${data.filename} · Test ID: ${data.test_id || 'N/A'}</div>

#                     <div class="prob-bar">
#                         <div class="prob-bar-label">
#                             <span>📸 Real Probability</span>
#                             <span>${(realProb * 100).toFixed(1)}%</span>
#                         </div>
#                         <div class="prob-bar-track">
#                             <div class="prob-bar-fill bar-real" style="width: ${(realProb * 100).toFixed(1)}%"></div>
#                         </div>
#                     </div>

#                     <div class="prob-bar">
#                         <div class="prob-bar-label">
#                             <span>🤖 AI Probability</span>
#                             <span>${(aiProb * 100).toFixed(1)}%</span>
#                         </div>
#                         <div class="prob-bar-track">
#                             <div class="prob-bar-fill bar-fake" style="width: ${(aiProb * 100).toFixed(1)}%"></div>
#                         </div>
#                     </div>

#                     <div class="stats">
#                         <div class="stat-card">
#                             <div class="stat-value">${(confidence * 100).toFixed(1)}%</div>
#                             <div class="stat-label">Confidence</div>
#                         </div>
#                         <div class="stat-card">
#                             <div class="stat-value">${data.verdict || 'N/A'}</div>
#                             <div class="stat-label">Verdict</div>
#                         </div>
#                         <div class="stat-card">
#                             <div class="stat-value">${new Date(data.timestamp).toLocaleTimeString()}</div>
#                             <div class="stat-label">Time</div>
#                         </div>
#                     </div>

#                     <details>
#                         <summary>📊 View Full Report</summary>
#                         <pre>${JSON.stringify(data, null, 2)}</pre>
#                     </details>
#                 `;
#             } catch (error) {
#                 loading.style.display = 'none';
#                 resultDiv.style.display = 'block';
#                 uploadBtn.disabled = false;
#                 uploadBtn.textContent = '🔍 Analyze Image';
#                 resultDiv.innerHTML = `<div class="error">❌ Error: ${error.message}</div>`;
#             }
#         });
#     </script>

#     <footer style="
#         text-align:center;
#         padding:24px 20px;
#         font-family:'IBM Plex Mono', monospace;
#         font-size:11px;
#         color:#565D6E;
#         border-top:1px solid #1C212C;
#         margin-top:20px;
#     ">
#         <div style="margin-bottom:10px;">
#             Verity analyzes images in real time and does not retain uploads. All results reflect a probabilistic assessment, not a definitive verdict.
#         </div>
#         <div style="margin-bottom:10px; color:#8892A6;">
#             Built by <span style="color:#2DD4BF; font-weight:600;">Syeda Samia</span>
#         </div>
#         <div style="display:flex; justify-content:center; gap:18px;">
#             <a href="https://www.linkedin.com/in/syeda-samia-836960319" target="_blank" style="color:#8892A6; text-decoration:none;">
#                 🔗 LinkedIn
#             </a>
#             <a href="https://github.com/syeda-samia" target="_blank" style="color:#8892A6; text-decoration:none;">
#                 💻 GitHub
#             </a>
#             <a href="mailto:samiagohar1150@gmail.com" style="color:#8892A6; text-decoration:none;">
#                 ✉️ Email
#             </a>
#         </div>
#     </footer>
# </body>
# </html>
# """

# @app.get("/", response_class=HTMLResponse)
# async def root():
#     return HTML_PAGE

# @app.post("/upload")
# async def upload_image(file: UploadFile = File(...)):
#     allowed = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
#     ext = os.path.splitext(file.filename)[1].lower()
    
#     if ext not in allowed:
#         raise HTTPException(400, f"Invalid type. Allowed: {', '.join(allowed)}")
    
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
#     unique_id = str(uuid.uuid4())[:8]
#     safe_filename = f"{timestamp}_{unique_id}_{file.filename}"
#     file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
#     try:
#         # Save uploaded file
#         with open(file_path, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)
        
#         # Run detection
#         result = detect_image(file_path, verbose=True)
        
#         # Handle errors
#         if result.get('error'):
#             return JSONResponse(
#                 status_code=500,
#                 content={'error': result['error']}
#             )
        
#         ai_prob = float(result.get("ai_probability", 0))
        
#         # ====================================================
#         # ADJUSTED CLASSIFICATION - More forgiving for real images
#         # ====================================================
#         if ai_prob >= 0.75:
#             result["classification"] = "AI GENERATED"
#             result["message"] = "⚠️ This image is very likely AI-generated"
#             result["verdict"] = "Fake"
#         elif ai_prob >= 0.60:
#             result["classification"] = "PROBABLY AI"
#             result["message"] = "⚠️ This image shows signs of AI generation"
#             result["verdict"] = "Probably Fake"
#         elif ai_prob >= 0.45:
#             result["classification"] = "UNCERTAIN"
#             result["message"] = "❓ Mixed signals - system is uncertain"
#             result["verdict"] = "Uncertain"
#         elif ai_prob >= 0.25:
#             result["classification"] = "PROBABLY REAL"
#             result["message"] = "✅ This image is likely a real photo"
#             result["verdict"] = "Probably Real"
#         else:
#             result["classification"] = "REAL IMAGE"
#             result["message"] = "✅ This appears to be a real camera photo"
#             result["verdict"] = "Real"
#         # ====================================================
        
#         # Ensure model_agreement is a bool
#         if 'model_agreement' in result:
#             result['model_agreement'] = bool(result['model_agreement'])
        
#         # Add metadata
#         result['filename'] = file.filename
#         result['timestamp'] = datetime.now().isoformat()
#         result['test_id'] = unique_id
        
#         # Ensure all values are JSON serializable
#         def make_json_serializable(obj):
#             if isinstance(obj, (np.integer, np.int64, np.int32)):
#                 return int(obj)
#             elif isinstance(obj, (np.floating, np.float64, np.float32)):
#                 return float(obj)
#             elif isinstance(obj, np.ndarray):
#                 return obj.tolist()
#             elif isinstance(obj, bool):
#                 return bool(obj)
#             elif isinstance(obj, dict):
#                 return {k: make_json_serializable(v) for k, v in obj.items()}
#             elif isinstance(obj, list):
#                 return [make_json_serializable(v) for v in obj]
#             else:
#                 return obj
        
#         result = make_json_serializable(result)
        
#         return JSONResponse(content=result)
        
#     except Exception as e:
#         error_trace = traceback.format_exc()
#         print(f"Error: {e}")
#         print(error_trace)
#         return JSONResponse(
#             status_code=500,
#             content={'error': str(e), 'trace': error_trace}
#         )
#     finally:
#         # Clean up uploaded file
#         if os.path.exists(file_path):
#             try:
#                 os.remove(file_path)
#             except:
#                 pass

# @app.get("/api/health")
# async def health_check():
#     return {
#         "status": "healthy",
#         "timestamp": datetime.now().isoformat(),
#         "version": "2.0.0"
#     }

# @app.get("/api/models")
# async def get_models():
#     return {
#         "models": ["CLIP", "DINOv2", "ResNet50", "ViT"],
#         "forensic_checks": ["ELA", "PRNU", "CFA", "DCT", "Chromatic Aberration", "Lighting Consistency", "EXIF"],
#         "weights": {"model": 0.7, "forensic": 0.3}
#     }

# if __name__ == "__main__":
#     print("="*60)
#     print("🚀 Techinfy - Image Classifier API")
#     print("="*60)
#     print(f"🌐 Web Interface: http://localhost:8000")
#     print(f"📖 API Docs: http://localhost:8000/docs")
#     print(f"📊 Health: http://localhost:8000/api/health")
#     print("="*60)
#     uvicorn.run(app, host="0.0.0.0", port=8000)
