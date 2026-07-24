"""
app.py - Streamlit frontend for Techinfy Verity
Uses the existing backend (inference.py -> decision_engine.py -> models.py + forensics.py)
without any changes to the detection logic.
"""

import streamlit as st
import tempfile
import os
import time
import plotly.graph_objects as go

from inference import detect_image

# ----------------------------------------------------------------------
# Page config
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="Techinfy Verity - Image Forensics",
    page_icon="🔍",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ----------------------------------------------------------------------
# Theme (matches the FastAPI frontend: dark ink + teal/red/amber verdicts)
# ----------------------------------------------------------------------
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root{
    --ink:#0A0D12;
    --panel:#12161F;
    --panel-2:#171C26;
    --line:#232938;
    --text:#E7ECF4;
    --muted:#8892A6;
    --muted-dim:#565D6E;
    --scan:#2DD4BF;
    --alert:#FB5B5B;
    --warn:#F5A623;
}

html, body, [class*="css"]  { font-family: 'Inter', sans-serif; }
.stApp { background: var(--ink); color: var(--text); }

/* header */
.verity-topbar{
    display:flex; align-items:center; justify-content:space-between;
    padding:18px 6px 22px; border-bottom:1px solid var(--line); margin-bottom:26px;
}
.verity-brand{ display:flex; align-items:center; gap:14px; }
.verity-mark{
    width:42px; height:42px; border:1.5px solid var(--scan); border-radius:9px;
    display:flex; align-items:center; justify-content:center; font-size:22px; flex-shrink:0;
}
.verity-name{ font-family:'Space Grotesk', sans-serif; font-weight:700; font-size:26px; color:var(--text); }
.verity-tag{ font-family:'IBM Plex Mono', monospace; font-size:13px; color:var(--muted); white-space:nowrap; }
.verity-right{ font-family:'IBM Plex Mono', monospace; font-size:12px; color:var(--muted); display:flex; align-items:center; gap:8px; white-space:nowrap; }
.verity-dot{ width:7px; height:7px; border-radius:50%; background:var(--scan); box-shadow:0 0 8px var(--scan); }

/* upload box (streamlit's native uploader dropzone) */
[data-testid="stFileUploaderDropzone"]{
    background: var(--panel-2) !important;
    border: 2px dashed var(--line) !important;
    border-radius: 12px !important;
}
[data-testid="stFileUploaderDropzone"]:hover{ border-color: var(--scan) !important; }

/* verdict box */
.verdict-box{ padding:26px 20px; border-radius:12px; text-align:center; margin:18px 0; }
.verdict-box.real, .verdict-box.probably-real{ background:rgba(45,212,191,0.08); border:1px solid var(--scan); }
.verdict-box.fake, .verdict-box.probably-fake{ background:rgba(251,91,91,0.08); border:1px solid var(--alert); }
.verdict-box.uncertain{ background:rgba(245,166,35,0.08); border:1px solid var(--warn); }
.verdict-label{ font-family:'Space Grotesk', sans-serif; font-size:24px; font-weight:700; }
.verdict-label.real, .verdict-label.probably-real{ color:var(--scan); }
.verdict-label.fake, .verdict-label.probably-fake{ color:var(--alert); }
.verdict-label.uncertain{ color:var(--warn); }
.verdict-msg{ color:var(--muted); font-size:14px; margin-top:8px; }

.agree-chip{
    display:inline-flex; align-items:center; gap:6px; font-family:'IBM Plex Mono', monospace;
    font-size:11px; padding:5px 12px; border-radius:20px; margin-top:14px;
}
.agree-chip.good{ color:var(--scan); background:rgba(45,212,191,0.1); }
.agree-chip.warn{ color:var(--warn); background:rgba(245,166,35,0.1); }

.meta-line{
    font-family:'IBM Plex Mono', monospace; font-size:11.5px; color:var(--muted-dim);
    text-align:center; margin-bottom:6px;
}

/* footer */
.verity-footer{
    text-align:center; padding:24px 10px; font-family:'IBM Plex Mono', monospace;
    font-size:11px; color:var(--muted-dim); border-top:1px solid var(--line); margin-top:36px;
}
.verity-footer a{ color:var(--muted); text-decoration:none; margin:0 10px; }
.verity-footer a:hover{ color:var(--scan); }
.verity-footer .credit{ margin-bottom:10px; color:var(--muted); }
.verity-footer .credit b{ color:var(--scan); }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ----------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------
st.markdown("""
<div class="verity-topbar">
    <div class="verity-brand">
        <div class="verity-mark">🔍</div>
        <div>
            <div class="verity-name">Techinfy</div>
            <div class="verity-tag">/ image authenticity scanner</div>
        </div>
    </div>
    <div class="verity-right"><span class="verity-dot"></span> models online</div>
</div>
""", unsafe_allow_html=True)

st.markdown(
    "<p style='color:var(--muted); font-size:15px; margin-bottom:22px;'>"
    "Upload an image and Verity runs it through CLIP + a dedicated AI-image detector, "
    "plus seven forensic checks, to weigh the evidence.</p>",
    unsafe_allow_html=True
)

# ----------------------------------------------------------------------
# Upload
# ----------------------------------------------------------------------
uploaded_file = st.file_uploader(
    "Drop your image here or click to browse",
    type=["jpg", "jpeg", "png", "bmp", "tiff", "webp"],
)

analyze_clicked = st.button("🔍 Analyze Image", type="primary", use_container_width=True, disabled=(uploaded_file is None))

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def tier_from_classification(cls: str):
    cls = (cls or "").upper()
    if "REAL IMAGE" in cls:
        return "real", "Real Image"
    if "PROBABLY REAL" in cls:
        return "probably-real", "Probably Real"
    if "AI GENERATED" in cls:
        return "fake", "AI Generated"
    if "PROBABLY AI" in cls:
        return "probably-fake", "Probably AI"
    return "uncertain", "Uncertain"


def build_gauge(ai_prob: float, css_key: str):
    color_map = {
        "real": "#2DD4BF", "probably-real": "#2DD4BF",
        "fake": "#FB5B5B", "probably-fake": "#FB5B5B",
        "uncertain": "#F5A623",
    }
    color = color_map.get(css_key, "#F5A623")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=ai_prob * 100,
        number={"suffix": "%", "font": {"size": 34, "color": color, "family": "IBM Plex Mono"}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#565D6E", "tickfont": {"color": "#565D6E", "size": 10}},
            "bar": {"color": color, "thickness": 0.28},
            "bgcolor": "#171C26",
            "borderwidth": 0,
            "steps": [{"range": [0, 100], "color": "#171C26"}],
        },
        domain={"x": [0, 1], "y": [0, 1]},
    ))
    fig.update_layout(
        height=220,
        margin=dict(l=20, r=20, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#8892A6"},
    )
    return fig


def format_pct(v):
    try:
        return f"{float(v) * 100:.1f}%"
    except (TypeError, ValueError):
        return "n/a"


def render_evidence(title: str, scores: dict):
    if not scores:
        return
    st.markdown(f"**{title}**")
    for name, data in scores.items():
        if not isinstance(data, dict):
            continue
        if "error" in data:
            val = "unavailable"
        elif isinstance(data.get("ai_probability"), (int, float)):
            val = format_pct(data["ai_probability"])
        elif isinstance(data.get("score"), (int, float)):
            val = format_pct(data["score"])
        else:
            val = "n/a"
        label = name.replace("_", " ").title()
        c1, c2 = st.columns([3, 1])
        c1.markdown(f"<span style='color:#8892A6;'>{label}</span>", unsafe_allow_html=True)
        c2.markdown(f"<span style='font-family:IBM Plex Mono; font-size:13px;'>{val}</span>", unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Run detection
# ----------------------------------------------------------------------
if analyze_clicked and uploaded_file is not None:
    suffix = os.path.splitext(uploaded_file.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = tmp.name

    steps = [
        "Reading file",
        "Checking compression level",
        "Running CLIP vision model",
        "Running SDXL detector",
        "Running forensic sweep — 7 checks",
        "Weighing combined evidence",
    ]

    result = None
    error_msg = None
    with st.status("Scanning image…", expanded=True) as status:
        try:
            for step in steps:
                st.write(f"› {step}")
                time.sleep(0.15)
            result = detect_image(tmp_path, verbose=False)
            if result.get("error"):
                error_msg = result["error"]
                status.update(label="Scan failed", state="error")
            else:
                status.update(label="Scan complete", state="complete")
        except Exception as e:
            error_msg = str(e)
            status.update(label="Scan failed", state="error")
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    if error_msg:
        st.error(f"Scan failed: {error_msg}")
    elif result:
        ai_prob = float(result.get("ai_probability", 0))

        # Same classification thresholds used in the FastAPI version
        if ai_prob >= 0.75:
            classification, message = "AI GENERATED", "⚠️ This image is very likely AI-generated"
        elif ai_prob >= 0.60:
            classification, message = "PROBABLY AI", "⚠️ This image shows signs of AI generation"
        elif ai_prob >= 0.45:
            classification, message = "UNCERTAIN", "❓ Mixed signals - system is uncertain"
        elif ai_prob >= 0.25:
            classification, message = "PROBABLY REAL", "✅ This image is likely a real photo"
        else:
            classification, message = "REAL IMAGE", "✅ This appears to be a real camera photo"

        css_key, label = tier_from_classification(classification)
        confidence = float(result.get("confidence_score", 0))
        model_agreement = result.get("model_agreement")

        st.markdown(f"""
        <div class="verdict-box {css_key}">
            <div class="verdict-label {css_key}">{label}</div>
            <div class="verdict-msg">{message}</div>
        </div>
        """, unsafe_allow_html=True)

        st.plotly_chart(build_gauge(ai_prob, css_key), use_container_width=True, config={"displayModeBar": False})

        if model_agreement is not None:
            chip_class = "good" if model_agreement else "warn"
            chip_text = "● Signals agree" if model_agreement else "● Signals mixed — treat with caution"
            st.markdown(f'<div style="text-align:center;"><span class="agree-chip {chip_class}">{chip_text}</span></div>', unsafe_allow_html=True)

        st.markdown(
            f'<div class="meta-line">📁 {uploaded_file.name} · confidence {format_pct(confidence)}</div>',
            unsafe_allow_html=True
        )

        with st.expander("📊 View evidence breakdown"):
            fd = result.get("forensic_details", {})
            render_evidence("Vision models", fd.get("model_scores", {}))
            st.divider()
            render_evidence("Forensic checks", fd.get("forensic_checks", {}))

            comp = result.get("compression_info", {})
            if comp:
                st.divider()
                st.markdown("**File**")
                c1, c2 = st.columns(2)
                c1.metric("Compression ratio", f"{comp.get('compression_ratio', 0):.1f}x")
                c2.metric("Size", f"{comp.get('file_size_kb', 0):.0f} KB")

# ----------------------------------------------------------------------
# Footer
# ----------------------------------------------------------------------
st.markdown("""
<div class="verity-footer">
    <div>Verity analyzes images in real time and does not retain uploads. All results reflect a probabilistic assessment, not a definitive verdict.</div>
    <div class="credit">Built by <b>Syeda Samia</b></div>
    <div>
        <a href="https://www.linkedin.com/in/syeda-samia-836960319" target="_blank">🔗 LinkedIn</a>
        <a href="https://github.com/syeda-samia" target="_blank">💻 GitHub</a>
        <a href="mailto:samiagohar1150@gmail.com">✉️ Email</a>
    </div>
</div>
""", unsafe_allow_html=True)
