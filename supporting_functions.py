import time
import json
import random
from dotenv import load_dotenv
import re
import streamlit as st
import requests

from youtube_transcript_api import YouTubeTranscriptApi

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

TRANSCRIPT_LIMIT = 15000

# =========================
# REAL BROWSER USER AGENTS
# =========================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]


def get_random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }


def human_delay(min_sec=1.0, max_sec=3.0):
    time.sleep(random.uniform(min_sec, max_sec))


def get_scraper_proxy():
    """
    Builds ScraperAPI proxy URL from Streamlit secrets.
    Returns proxy dict or None if key not found.
    """
    try:
        scraper_key = st.secrets["SCRAPER_API_KEY"]
        proxy_url = f"http://scraperapi:{scraper_key}@proxy-server.scraperapi.com:8001"
        return {"http": proxy_url, "https": proxy_url}
    except Exception:
        return None


# =========================
# LLM — cached once per session
# =========================
@st.cache_resource
def get_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0.2
    )


# =========================
# HELPER: Extract Video ID
# =========================
def extract_video_id(url):
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    if match:
        return match.group(1)
    st.error("Invalid YouTube URL. Please enter a valid video link.")
    return None


# =========================
# GET TRANSCRIPT
# — ScraperAPI proxy
# — random user agent
# — human-like delays
# — retries up to 3 times
# — cached after success
# =========================
@st.cache_data(show_spinner=False)
def get_transcript(video_id, language):
    max_retries = 3
    proxies = get_scraper_proxy()

    for attempt in range(max_retries):
        try:
            if attempt == 0:
                human_delay(1.0, 2.5)
            else:
                human_delay(3.0, 6.0)

            # Build session with real browser headers + ScraperAPI proxy
            session = requests.Session()
            session.headers.update(get_random_headers())
            session.verify = False

            if proxies:
                session.proxies.update(proxies)

            ytt_api = YouTubeTranscriptApi(http_client=session)
            transcript = ytt_api.fetch(video_id, languages=[language])

            # Small delay after fetching
            human_delay(0.5, 1.5)

            return " ".join([i.text for i in transcript])

        except Exception as e:
            error_msg = str(e).lower()

            if attempt < max_retries - 1:
                wait = round(random.uniform(3.0, 7.0), 1)
                st.warning(f"⚠️ Attempt {attempt + 1} failed. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                if "blocked" in error_msg or "429" in error_msg or "too many" in error_msg:
                    st.error("🚫 YouTube is blocking requests. Check your ScraperAPI key in Streamlit Secrets.")
                elif "no transcript" in error_msg or "not available" in error_msg:
                    st.error("📭 No transcript available for this video. The video may not have captions.")
                elif "private" in error_msg:
                    st.error("🔒 This video is private or unavailable.")
                elif "parsable" in error_msg:
                    st.error("🚫 YouTube blocked this request. Check your ScraperAPI key.")
                else:
                    st.error(f"❌ Failed after {max_retries} attempts: {e}")
                return None


# =========================
# TRANSLATE TRANSCRIPT
# =========================
@st.cache_data(show_spinner=False)
def translate_transcript(transcript):
    try:
        llm = get_llm()
        prompt = ChatPromptTemplate.from_template("""
        You are an expert translator with deep cultural and linguistic knowledge.
        Translate the following transcript into English with absolute accuracy, preserving:
        - Full meaning and context (no omissions, no additions).
        - Tone and style (formal/informal, emotional/neutral as in original).
        - Nuances, idioms, and cultural expressions.
        - Speaker's voice (same perspective).
        Do not summarize or simplify.

        Transcript:
        {transcript}
        """)
        chain = prompt | llm
        response = chain.invoke({"transcript": transcript[:TRANSCRIPT_LIMIT]})
        return response.content
    except Exception as e:
        st.error(f"Error translating transcript: {e}")
        return transcript


# =========================
# GET IMPORTANT TOPICS
# =========================
@st.cache_data(show_spinner=False)
def get_important_topics(transcript):
    try:
        llm = get_llm()
        prompt = ChatPromptTemplate.from_template("""
        You are an assistant that extracts the 5 most important topics discussed in a video transcript.

        Rules:
        - Summarize into exactly 5 major points.
        - Each point should represent a key topic or concept, not small details.
        - Keep wording concise and focused on the technical content.
        - Do not phrase them as questions or opinions.
        - Output should be a numbered list.
        - Show only points that are discussed in the transcript.

        Transcript:
        {transcript}
        """)
        chain = prompt | llm
        response = chain.invoke({"transcript": transcript[:TRANSCRIPT_LIMIT]})
        return response.content
    except Exception as e:
        st.error(f"Error extracting topics: {e}")
        return None


# =========================
# GENERATE NOTES
# =========================
@st.cache_data(show_spinner=False)
def generate_notes(transcript):
    try:
        llm = get_llm()
        prompt = ChatPromptTemplate.from_template("""
        You are an AI note-taker. Read the following YouTube video transcript
        and produce well-structured, concise notes.

        Requirements:
        - Present the output as bulleted points, grouped into clear sections.
        - Highlight key takeaways, important facts, and examples.
        - Use short, clear sentences (no long paragraphs).
        - If the transcript includes multiple themes, organize them under subheadings.
        - Do not add information that is not present in the transcript.

        Transcript:
        {transcript}
        """)
        chain = prompt | llm
        response = chain.invoke({"transcript": transcript[:TRANSCRIPT_LIMIT]})
        return response.content
    except Exception as e:
        st.error(f"Error generating notes: {e}")
        return None


# =========================
# CREATE CHUNKS
# =========================
def create_chunks(transcript):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=10000,
        chunk_overlap=1000
    )
    doc = text_splitter.create_documents([transcript])
    return doc


# =========================
# FIXED EMBEDDINGS WRAPPER
# =========================
class FixedEmbeddings:
    def __init__(self):
        self.model = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001"
        )

    def embed_documents(self, texts):
        embeddings = self.model.embed_documents(texts)
        fixed = []
        for e in embeddings:
            if isinstance(e, list) and len(e) > 0 and isinstance(e[0], list):
                fixed.append(e[0])
            else:
                fixed.append(e)
        return fixed

    def embed_query(self, text):
        e = self.model.embed_query(text)
        if isinstance(e, list) and len(e) > 0 and isinstance(e[0], list):
            return e[0]
        return e


# =========================
# CREATE VECTOR STORE
# =========================
@st.cache_resource
def create_vector_store(docs):
    embedding = FixedEmbeddings()
    vector_store = Chroma.from_documents(docs, embedding)
    return vector_store


# =========================
# RAG ANSWER
# =========================
def rag_answer(question, vectorstore):
    try:
        llm = get_llm()
        results = vectorstore.similarity_search(question, k=4)
        context_text = "\n".join([i.page_content for i in results])

        prompt = ChatPromptTemplate.from_template("""
        You are a kind, polite, and precise assistant.
        - Understand the user's intent even with typos or grammatical mistakes.
        - Answer ONLY using the retrieved context.
        - If the answer is not in context, say:
          "I couldn't find that information in the video. Could you rephrase or ask something else?"
        - Keep answers clear, concise, and friendly.

        Context:
        {context}

        User Question:
        {question}

        Answer:
        """)
        chain = prompt | llm
        response = chain.invoke({"context": context_text, "question": question})
        return response.content
    except Exception as e:
        st.error(f"Error answering question: {e}")
        return None


# =========================
# GENERATE MINDMAP
# =========================
@st.cache_data(show_spinner=False)
def generate_mindmap_data(transcript):
    try:
        llm = get_llm()
        prompt = ChatPromptTemplate.from_template("""
        You are an expert at structuring information.
        Read the transcript and create a hierarchical Mindmap structure in Markdown format.

        Rules:
        1. The Root node should be a single H1 (# Title).
        2. Main branches should be bullet points with bold text (- **Main Branch**).
        3. Sub-branches should be indented bullet points.
        4. Keep text concise (max 4-6 words per node).
        5. Do NOT add any code blocks, just return the raw markdown text.

        Transcript:
        {transcript}
        """)
        chain = prompt | llm
        response = chain.invoke({"transcript": transcript[:TRANSCRIPT_LIMIT]})
        clean_md = response.content.replace("```markdown", "").replace("```", "").strip()
        return clean_md
    except Exception as e:
        st.error(f"Error generating mindmap: {e}")
        return "# Error\n- Could not generate mindmap"


# =========================
# GENERATE TINY CATS
# =========================
@st.cache_data(show_spinner=False)
def generate_tiny_cats_data(transcript):
    try:
        llm = get_llm()
        prompt = ChatPromptTemplate.from_template("""
        You are "Tiny Cats AI". Explain complex topics from the transcript using cute tiny cat analogies.

        Transcript:
        {transcript}

        INSTRUCTIONS:
        1. Identify the 3 most difficult or important concepts.
        2. Explain each concept using a specific scenario with CUTE TINY CATS.
        3. For EACH concept, write a valid, cute, simple SVG image code that visualizes this cat scenario.

        OUTPUT FORMAT (Return strictly a JSON List, no markdown):
        [
          {{
            "title": "Concept Name",
            "explanation": "Simple explanation using cats...",
            "svg": "<svg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'> ... </svg>"
          }}
        ]

        IMPORTANT SVG RULES:
        - Use simple shapes (circles, rects, paths).
        - Use bright colors.
        - Ensure the SVG string is valid and complete.
        """)
        chain = prompt | llm
        response = chain.invoke({"transcript": transcript[:TRANSCRIPT_LIMIT]})
        clean_json = response.content.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except Exception as e:
        st.error(f"Error generating cats: {e}")
        return []


# =========================
# GENERATE QUIZ
# =========================
@st.cache_data(show_spinner=False)
def generate_quiz_data(transcript):
    try:
        llm = get_llm()
        prompt = ChatPromptTemplate.from_template("""
        You are a Professor. Create a quiz of 5 multiple-choice questions based on this transcript.

        Return strictly a JSON List in this format:
        [
            {{
                "question": "What is the main advantage of X?",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "answer": "Option B",
                "explanation": "Option B is correct because..."
            }}
        ]

        Transcript:
        {transcript}
        """)
        chain = prompt | llm
        response = chain.invoke({"transcript": transcript[:TRANSCRIPT_LIMIT]})
        clean_json = response.content.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except Exception as e:
        st.error(f"Quiz generation error: {e}")
        return []
