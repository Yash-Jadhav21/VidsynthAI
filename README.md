# VidsynthAI
> Turn any YouTube video into structured knowledge — instantly.

VidSynth AI is a full-stack AI application that takes any YouTube video and transforms it into interactive learning material using Google Gemini and LangChain.

---

## ✨ Features

| Feature | Description |
|---|---|
| 💬 **Chat with Video** | Ask any question about the video using a RAG pipeline |
| 📓 **Auto Notes** | Get clean, structured bullet-point notes |
| 🐱 **Tiny Cats Explainer** | Hard concepts explained through cute cat analogies with SVG visuals |
| 🧠 **Quiz Zone** | Auto-generated 5-question MCQ quiz with explanations |
| 🗺️ **Mindmap** | Interactive visual mindmap of the entire video |

---

## 🛠️ Tech Stack

- **Frontend** — Streamlit
- **AI Model** — Google Gemini 2.5 Flash Lite
- **LLM Framework** — LangChain
- **Vector Database** — Chroma (for RAG)
- **Embeddings** — Google Gemini Embedding 001
- **Transcript** — YouTube Transcript API
- **Language** — Python

---

## 🏗️ Architecture

```
YouTube URL
    │
    ▼
YouTube Transcript API  ──►  Raw Transcript
                                    │
              ┌─────────────────────┼──────────────────────┐
              ▼                     ▼                      ▼
        Gemini LLM            Text Splitter          Gemini LLM
        (Notes/Quiz/         (Chunks)                (Tiny Cats/
         Topics/Mindmap)          │                   Mindmap)
                              Chroma DB
                                  │
                              RAG Answer
```

---

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/vidsynth-ai.git
cd vidsynth-ai
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up environment variables

Create a `.env` file in the root folder:
```
GOOGLE_API_KEY=your_gemini_api_key_here
```

Get your free Gemini API key at: https://aistudio.google.com/app/apikey

### 4. Run the app
```bash
streamlit run app.py
```

---

## 📁 Project Structure

```
vidsynth-ai/
├── app.py                  # Main Streamlit app — UI and routing
├── supporting_functions.py # All AI functions — LLM, RAG, transcript
├── requirements.txt        # Python dependencies
└── .env                    # API keys (never commit this)
```

---

## 🔑 Environment Variables

| Variable | Description |
|---|---|
| `GOOGLE_API_KEY` | Your Google Gemini API key |

---

## 📦 Deployment

This app is deployed on **Streamlit Community Cloud**.

To deploy your own instance:
1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Add `GOOGLE_API_KEY` in **Settings → Secrets**
5. Click Deploy

---

## ⚠️ Known Limitations

- YouTube may block transcript requests from cloud server IPs
- Videos without captions or subtitles cannot be processed
- Private or age-restricted videos are not supported
- Transcript is limited to the first 15,000 characters for LLM calls

---

## 🙏 Acknowledgements

- [LangChain](https://langchain.com) — LLM orchestration framework
- [Google Gemini](https://deepmind.google/technologies/gemini/) — AI model
- [YouTube Transcript API](https://github.com/jdepoix/youtube-transcript-api) — Transcript fetching
- [Streamlit](https://streamlit.io) — App framework

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).
