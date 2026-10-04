import streamlit as st
from PIL import Image
import hashlib
from datetime import date

st.set_page_config(page_title="AI Identity & Document Screening", page_icon="🛂", layout="wide")
st.title("🛂 AI-Based Fake Identity & Document Screening System")
st.caption("AI-assisted screening • Human officer remains the final decision-maker")

with st.sidebar:
    st.header("Screening Controls")
    st.toggle("Demo analysis mode", value=True)
    st.info("This is a demonstration prototype. Production identity verification requires validated models and authorized data sources.")

st.subheader("1. Document Upload")
uploaded = st.file_uploader("Upload passport / visa / ID / license / permit image", type=["png", "jpg", "jpeg"])
if uploaded is None:
    st.info("Upload a document image above to start.")
    st.stop()

img = Image.open(uploaded)
left, right = st.columns([1, 1.5])
with left:
    st.image(img, caption="Uploaded document", use_container_width=True)

digest = hashlib.sha256(uploaded.getvalue()).hexdigest()
demo_flag = int(digest[-2:], 16) % 5 == 0

with right:
    st.subheader("2. OCR Extraction")
    st.caption("Demo OCR fields — replace with a real OCR engine for production.")
    name = st.text_input("Name", "RAHUL SHARMA")
    document_no = st.text_input("Document Number", "P1234567")
    nationality = st.text_input("Nationality", "IND")
    dob = st.text_input("Date of Birth", "15-08-2000")
    expiry = st.date_input("Expiry Date", date(2030, 8, 15))

st.divider()
st.subheader("3. Document Validation")
checks = [
    ("Required fields present", bool(name and document_no and nationality and dob)),
    ("Document not expired", expiry >= date.today()),
    ("Document number format consistent", len(document_no) >= 6),
    ("Demo tampering signal", not demo_flag),
]
cols = st.columns(4)
for i, (label, ok) in enumerate(checks):
    with cols[i]:
        if ok:
            st.success("PASS\n\n" + label)
        else:
            st.error("FLAG\n\n" + label)

st.subheader("4. Tampering Detection")
tamper_score = 72 if demo_flag else 18
st.progress(tamper_score / 100)
st.write(f"Estimated manipulation signal: **{tamper_score}/100**")
if tamper_score >= 50:
    st.warning("Potentially unusual document region or metadata signal detected.")
else:
    st.success("No strong tampering signal detected in this demo analysis.")

st.subheader("5. Face Verification")
face_col1, face_col2 = st.columns(2)
with face_col1:
    st.file_uploader("Upload presented person's photo", type=["png", "jpg", "jpeg"], key="face_photo")
with face_col2:
    face_similarity = st.slider("Demo face similarity", 0, 100, 91)
    if face_similarity >= 85:
        st.success(f"Similarity: {face_similarity}% — PASS")
    elif face_similarity >= 70:
        st.warning(f"Similarity: {face_similarity}% — REVIEW")
    else:
        st.error(f"Similarity: {face_similarity}% — FLAG")

st.subheader("6. Explainable Risk Assessment")
risk = 0
reasons = []
if not all(x[1] for x in checks[:3]):
    risk += 30
    reasons.append("Document field or validity check requires review.")
if tamper_score >= 50:
    risk += 35
    reasons.append("Potential tampering signal detected.")
if face_similarity < 85:
    risk += 30
    reasons.append("Face-to-document similarity is below the demo threshold.")
risk = min(risk, 100)
if risk < 30:
    level = "LOW"
    st.success(f"Risk Score: {risk}/100 — {level}")
elif risk < 65:
    level = "MEDIUM"
    st.warning(f"Risk Score: {risk}/100 — {level}")
else:
    level = "HIGH"
    st.error(f"Risk Score: {risk}/100 — {level}")

st.write("### Reason Codes")
if reasons:
    for reason in reasons:
        st.write("• " + reason)
else:
    st.write("• No demo risk reason was triggered.")

st.divider()
st.subheader("7. Officer Review")
st.info("The system provides screening evidence and a review recommendation. The final decision remains with the authorized human officer.")
decision = st.radio("Officer action", ["Pending Review", "Approve / Clear", "Refer for Further Review"], horizontal=True)
st.write(f"**Current officer action:** {decision}")
st.divider()
st.caption("AI-Based Fake Identity & Document Screening System — Prototype")
