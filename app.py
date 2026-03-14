# app.py
import streamlit as st
from streamlit import spinner
import streamlit.components.v1 as components
import json

# Ensure these are all available in your supporting_functions.py
from supporting_functions import (
    extract_video_id,
    get_transcript,
    translate_transcript,
    generate_notes,
    get_important_topics,
    create_chunks,
    create_vector_store,
    rag_answer,
    generate_mindmap_data,
    generate_tiny_cats_data,
    generate_quiz_data
)

# =========================
# 🌟 1. CONFIG & STYLING
# =========================
st.set_page_config(
    page_title="VidSynth AI",
    page_icon="🎬",
    layout="wide",
)

st.markdown("""
<style>
    .main {
        background: linear-gradient(135deg, #0d1117, #161b22);
        color: white !important;
    }
    section[data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.04);
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255,255,255,0.1);
    }
    input, textarea {
        border-radius: 12px !important;
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        background: linear-gradient(90deg, #4c8bf5, #884ffc);
        color: white;
        height: 45px;
        font-size: 16px;
        border: none;
        transition: 0.3s ease;
    }
    .stButton>button:hover {
        transform: scale(1.03);
        background: linear-gradient(90deg, #5d96ff, #a36bff);
    }
    div[data-testid="stChatMessage"] {
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 10px;
        background: rgba(255, 255, 255, 0.05);
    }
    /* Tiny Cats Card Style */
    .cat-card {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "show_mindmap" not in st.session_state:
    st.session_state.show_mindmap = False

# =========================
# 🌟 2. SIDEBAR INPUTS
# =========================
with st.sidebar:
    st.title("🎬 VidSynth AI")
    st.caption("Turn any YouTube video into **notes, topics, and chat** powered by AI.")
    st.markdown("---")

    youtube_url = st.text_input("🔗 YouTube URL", placeholder="https://youtu.be/video_id")
    language = st.text_input("🌐 Video Language Code", value="en")

    st.markdown("### 🎯 What do you want to generate?")
    task_option = st.radio(
        "Select Mode",
        ["Chat with Video", "Notes For You", "Tiny Cats Explainer 🐱", "Quiz Zone 🧠"],
        label_visibility="collapsed"
    )

    submit_button = st.button("✨ Start Processing")

    st.markdown("---")

    if st.button("🧠 Mindmap This Video"):
        if "full_transcript" in st.session_state:
            st.session_state.show_mindmap = True
            st.rerun()
        else:
            st.warning("⚠️ Process a video first!")

# =========================
# 🌟 3. MINDMAP OVERLAY
# =========================
if st.session_state.show_mindmap:
    st.title("🧠 Interactive Video Mindmap")
    
    if st.button("⬅ Back to Dashboard"):
        st.session_state.show_mindmap = False
        st.rerun()

    if "full_transcript" in st.session_state:
        # Generate Data if missing
        if "mindmap_data" not in st.session_state:
            with st.spinner("✨ AI is brainstorming the structure..."):
                st.session_state.mindmap_data = generate_mindmap_data(st.session_state.full_transcript)

        # Render HTML
        md_json = json.dumps(st.session_state.mindmap_data)
        html_code = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body, html {{ margin: 0; padding: 0; width: 100%; height: 100%; background-color: #0d1117; overflow: hidden; }}
                svg {{ width: 100%; height: 100%; }}
                .markmap {{ color: #e6edf3; }}
                .markmap-link {{ stroke: #7d8590; }}
            </style>
            <script src="https://cdn.jsdelivr.net/npm/markmap-autoloader@0.15.2"></script>
        </head>
        <body>
            <div class="markmap" style="height: 100vh;">
                <script type="text/template">{st.session_state.mindmap_data}</script>
            </div>
        </body>
        </html>
        """
        components.html(html_code, height=600)
        
        # Download Buttons
        d1, d2 = st.columns(2)
        with d1:
            st.download_button("📄 Download Markdown", st.session_state.mindmap_data, "mindmap.md")
        with d2:
            st.download_button("🌐 Download HTML", html_code, "mindmap.html", "text/html")
    else:
        st.warning("⚠️ Please process a video first!")
    
    st.stop() # Stop here so the rest of the dashboard is hidden

# =========================
# 🌟 4. BACKEND PROCESSING
# =========================
if submit_button:
    if youtube_url.strip():
        video_id = extract_video_id(youtube_url)

        if video_id:
            # Reset UI state
            st.session_state.show_mindmap = False
            st.session_state.messages = []

            # 1. Fetch Transcript
            with st.spinner("📥 Step 1/3: Fetching Transcript..."):
                full_transcript = get_transcript(video_id, language)
                st.session_state.full_transcript = full_transcript
                st.session_state.video_id = video_id

            if not full_transcript:
                st.error("Failed to fetch transcript.")
                st.stop()

            # 2. Translate if needed
            if language != "en":
                with st.spinner("🌍 Translating to English..."):
                    full_transcript = translate_transcript(full_transcript)
                    st.session_state.full_transcript = full_transcript

            # 3. Route based on Selection
            # NOTES
            if task_option == "Notes For You":
                with st.spinner("🧠 Extracting Topics..."):
                    st.session_state.topics = get_important_topics(full_transcript)
                with st.spinner("📝 Generating Notes..."):
                    st.session_state.notes = generate_notes(full_transcript)
                st.success("✨ Notes Ready!")

            # CHAT
            elif task_option == "Chat with Video":
                with st.spinner("🔍 Creating Vector Store..."):
                    chunks = create_chunks(full_transcript)
                    vectorstore = create_vector_store(chunks)
                    st.session_state.vector_store = vectorstore
                st.success("💬 Ready for Chat!")

            # TINY CATS
            elif task_option == "Tiny Cats Explainer 🐱":
                with st.spinner("🐱 Gathering the tiny cats..."):
                    st.session_state.cat_data = generate_tiny_cats_data(full_transcript)
                if st.session_state.cat_data:
                    st.success("🐱 Meow! Visuals ready.")
                else:
                    st.error("Cats failed to generate.")

            # QUIZ ZONE (Added Logic)
            elif task_option == "Quiz Zone 🧠":
                with st.spinner("👨‍🏫 Drafting questions..."):
                    st.session_state.quiz_data = generate_quiz_data(full_transcript)
                    st.session_state.quiz_score = 0
                if st.session_state.quiz_data:
                    st.success("🧠 Quiz Ready!")
                else:
                    st.error("Failed to generate quiz.")

# =========================
# 🌟 5. FRONTEND DISPLAY LOGIC
# =========================

# LANDING PAGE (Show if no video processed)
if "full_transcript" not in st.session_state:
    components.html("""
    <style>
    @keyframes fadeIn { 0% { opacity:0; transform:translateY(25px);} 100% {opacity:1; transform:translateY(0);} }
    .hero-box { animation: fadeIn 1.3s ease-in-out; text-align:center; padding:60px 20px; color:white; }
    </style>
    <div class="hero-box">
        <h1 style="font-size:54px; font-weight:700;">✨ VidSynthAI</h1>
        <p style="color:#c9d1d9; font-size:20px;">Illuminate your learning. One video at a time.</p>
        <p style="color:#9da7b0; font-size:15px;">Paste a YouTube link in the sidebar to begin.</p>
    </div>
    """, height=400)

# --- DISPLAY: NOTES ---
if task_option == "Notes For You" and "notes" in st.session_state:
    st.subheader("📌 Important Topics")
    st.write(st.session_state.topics)
    st.markdown("---")
    st.subheader("📓 Notes")
    st.write(st.session_state.notes)
    
    st.markdown("---")
    notes_content = f"TOPICS:\n{st.session_state.topics}\n\nNOTES:\n{st.session_state.notes}"
    st.download_button("📥 Download Notes", notes_content, "generated_notes.txt")

# --- DISPLAY: CHAT ---
if task_option == "Chat with Video" and "vector_store" in st.session_state:
    st.markdown("---")
    st.subheader("💬 Chat with Video")
    
    for msg in st.session_state.get("messages", []):
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if user_msg := st.chat_input("Ask anything about the video..."):
        st.session_state.messages.append({"role": "user", "content": user_msg})
        with st.chat_message("user"):
            st.write(user_msg)

        with st.chat_message("assistant"):
            response = rag_answer(user_msg, st.session_state.vector_store)
            st.write(response)

        st.session_state.messages.append({"role": "assistant", "content": response})

# --- DISPLAY: TINY CATS ---
if task_option == "Tiny Cats Explainer 🐱" and "cat_data" in st.session_state:
    st.markdown("---")
    st.subheader("🐱 Tiny Cats Explain...")
    
    for card in st.session_state.cat_data:
        with st.container():
            st.markdown(f"### {card.get('title', 'Concept')}")
            c1, c2 = st.columns([1, 2])
            with c1:
                st.markdown(f'<div style="background:white;border-radius:10px;padding:10px;">{card.get("svg","")}</div>', unsafe_allow_html=True)
            with c2:
                st.info(card.get('explanation', ''))
            st.markdown("---")

# --- DISPLAY: QUIZ ZONE ---
if task_option == "Quiz Zone 🧠" and "quiz_data" in st.session_state:
    st.header("🧠 Test Your Knowledge")
    
    with st.form("quiz_form"):
        user_answers = {}
        for index, item in enumerate(st.session_state.quiz_data):
            st.subheader(f"Q{index+1}: {item['question']}")
            user_answers[index] = st.radio(
                "Select an answer:", 
                item['options'], 
                key=f"q_{index}", 
                index=None
            )
            st.markdown("---")
        
        submit_quiz = st.form_submit_button("✅ Submit Answers")

    if submit_quiz:
        score = 0
        for index, item in enumerate(st.session_state.quiz_data):
            correct = item['answer']
            user_choice = user_answers.get(index)
            
            if user_choice == correct:
                score += 1
                st.success(f"Q{index+1} Correct! ({correct})")
            else:
                st.error(f"Q{index+1} Incorrect. Correct: {correct}")
                st.info(f"💡 Reason: {item['explanation']}")
        
        # Score Visualization
        final_score = (score / len(st.session_state.quiz_data)) * 100
        if final_score == 100:
            st.balloons()
            st.markdown("## 🏆 Perfect Score!")
        elif final_score >= 80:
            st.markdown(f"## 🥈 Great Job! Score: {score}/{len(st.session_state.quiz_data)}")
        else:
            st.markdown(f"## 📚 Keep Studying! Score: {score}/{len(st.session_state.quiz_data)}")