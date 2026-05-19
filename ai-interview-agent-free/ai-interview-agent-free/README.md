# 🤖 AI Interview Agent — FREE Version (Groq API)

## ✅ Ab BILKUL FREE hai! OpenAI ki zaroorat NAHI!

Is version mein **Groq API** use hota hai jo completely free hai.

---

## 🆓 Groq API kyun free hai?

| Feature | OpenAI | Groq (Free) |
|---|---|---|
| Cost | Paid (per token) | **FREE** |
| Speed | Normal | **Ultra Fast** (LPU chips) |
| Quality | GPT-3.5 level | **Same level** |
| Daily limit | — | 14,400 requests/day |
| Per interview | ~₹0.42 | **₹0** |

**14,400 requests/day = 3,600 free interviews per day!**

---

## 🔑 Free API Key Kaise Lein (2 minute)

1. **https://console.groq.com** par jao
2. **"Sign Up"** karo — Google account se bhi ho sakta hai
3. Left menu mein **"API Keys"** par click karo
4. **"Create API Key"** button dabao
5. Key **copy** karo — `gsk_` se shuru hogi
6. `.env` file mein paste karo

---

## 🚀 Setup aur Run Karne ke Steps

### Step 1 — Python check karo
```bash
python --version
# 3.8 ya upar chahiye
```

### Step 2 — Backend setup
```bash
cd backend

# Virtual environment banao
python -m venv venv

# Activate karo
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Packages install karo
pip install -r requirements.txt
```

### Step 3 — API Key add karo
```bash
# .env file banao
cp .env.example .env

# .env file kholo aur key daalo:
# GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxx
```

### Step 4 — Server chalao
```bash
python app.py
```

Output dikhega:
```
==========================================================
  🤖  AI Interview Agent — FREE Version (Groq)
==========================================================
  ✅  Server:    http://localhost:5000
  🆓  AI Model:  Groq llama-3.3-70b (FREE!)
  📂  Uploads:   ./uploads/
  🗄️   Database:  ./database/interviews.db
==========================================================
```

### Step 5 — Browser mein kholo
```
http://localhost:5000
```

---

## 📁 Folder Structure

```
ai-interview-agent-free/
│
├── backend/
│   ├── app.py              ← Flask server (5 routes)
│   ├── ai_engine.py        ← Groq AI calls (FREE!)
│   ├── resume_parser.py    ← PDF/DOCX/TXT text extractor
│   ├── database.py         ← SQLite helper
│   ├── requirements.txt    ← Python packages
│   └── .env.example        ← API key template
│
├── frontend/
│   ├── index.html          ← 4 screens SPA
│   └── static/
│       ├── css/style.css   ← Dark UI styling
│       └── js/app.js       ← Frontend logic
│
├── uploads/                ← Temp (auto-delete)
├── database/
│   └── interviews.db       ← SQLite (auto-create)
└── README.md
```

---

## ❓ Common Problems

| Problem | Fix |
|---|---|
| `groq module not found` | `pip install groq` |
| `AuthenticationError` | `.env` mein sahi key check karo |
| PDF text empty | Text-based PDF use karo (scanned nahi) |
| Port in use | `app.run(port=5001)` karo |

---

## 💡 Model Change karna ho toh

`backend/ai_engine.py` mein line 47:
```python
MODEL = "llama-3.3-70b-versatile"   # Best quality (default)
# MODEL = "llama-3.1-8b-instant"    # Fastest
# MODEL = "gemma2-9b-it"            # Google ka model
# MODEL = "mixtral-8x7b-32768"      # Long context
```

Sab free hain!
