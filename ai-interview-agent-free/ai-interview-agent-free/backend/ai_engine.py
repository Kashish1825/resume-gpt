"""
=============================================================
  ai_engine.py  —  FREE AI Engine using Groq API
=============================================================
  Groq API:
    - BILKUL FREE hai (free tier mein)
    - OpenAI se bhi FAST hai (LPU chips use karta hai)
    - Quality GPT-3.5 jaisi hi hai
    - Free limits: 14,400 requests/day, 30 req/min
      (Ek interview = sirf 4 requests — toh 3600 interviews/day FREE!)

  Free API Key kaise lein:
    1. https://console.groq.com par jao
    2. Sign Up karo (Google se bhi ho sakta hai)
    3. "API Keys" mein jao → "Create API Key"
    4. Key copy karo aur .env mein daalo:
       GROQ_API_KEY=gsk_xxxxxxxxxxxx

  Models available (sab free):
    - llama-3.3-70b-versatile  ← Best quality, hamara default
    - llama-3.1-8b-instant     ← Fastest
    - gemma2-9b-it             ← Google ka model
    - mixtral-8x7b-32768       ← Long context
=============================================================
"""

import os
import json
from groq import Groq
from dotenv import load_dotenv
load_dotenv()
# ── Groq Client initialize karo ──────────────────────────────
# GROQ_API_KEY .env file se load hota hai
client = Groq(api_key="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")

# ── Model choice ─────────────────────────────────────────────
# llama-3.3-70b-versatile = best quality, bilkul free
MODEL = "llama-3.3-70b-versatile"


# ════════════════════════════════════════════════════════════
#  HELPER: JSON parser (AI kabhi kabhi ```json blocks deta hai)
# ════════════════════════════════════════════════════════════

def _parse_json(text: str):
    """
    AI ka response JSON hona chahiye.
    Lekin kabhi kabhi ```json ... ``` wrapper aa jaata hai.
    Yeh function wo wrapper remove karke clean JSON parse karta hai.
    """
    cleaned = text.strip()
    # ```json ... ``` ya ``` ... ``` remove karo
    if cleaned.startswith("```"):
        lines   = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1]).strip()
    return json.loads(cleaned)


def _chat(system_msg: str, user_msg: str, temperature: float = 0.7) -> str:
    """
    Groq API ko ek message bhejta hai aur text response return karta hai.

    Args:
        system_msg   : AI ko batao ki woh kya role play kare
        user_msg     : Actual question ya content
        temperature  : 0 = focused/consistent, 1 = creative

    Returns:
        AI ka text response
    """
    response = client.chat.completions.create(
        model    = MODEL,
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user",   "content": user_msg},
        ],
        temperature = temperature,
        max_tokens  = 1024,
    )
    return response.choices[0].message.content.strip()


# ════════════════════════════════════════════════════════════
#  FUNCTION 1: Resume se Skills nikalo
# ════════════════════════════════════════════════════════════

def extract_skills_from_resume(resume_text: str) -> list:
    """
    Resume text padhkar candidate ki skills ki list banata hai.

    Args:
        resume_text : Resume se extracted plain text

    Returns:
        ['Python', 'React', 'SQL', ...] — max 12 skills
    """
    system = (
        "You are a professional resume analyst. "
        "Extract skills ONLY from the provided resume text. "
        "Do NOT invent or add skills that are not mentioned."
    )

    prompt = f"""
Read the resume below and extract the candidate's skills.
Include: programming languages, frameworks, tools, databases, soft skills.

Resume:
\"\"\"
{resume_text[:3000]}
\"\"\"

Return ONLY a valid JSON array of strings. No explanation. No extra text.
Maximum 12 skills. Example format:
["Python", "React", "MySQL", "Communication", "Git"]
"""

    try:
        reply  = _chat(system, prompt, temperature=0.2)
        skills = _parse_json(reply)

        if isinstance(skills, list):
            return [str(s).strip() for s in skills if s][:12]

        return _fallback_skills()

    except Exception as e:
        print(f"[ai_engine] extract_skills error: {e}")
        return _fallback_skills()


def _fallback_skills() -> list:
    """Agar AI fail ho jaaye toh yeh generic skills return karo."""
    return ["Communication", "Problem Solving", "Teamwork", "Analytical Thinking"]


# ════════════════════════════════════════════════════════════
#  FUNCTION 2: Interview Questions Generate karo
# ════════════════════════════════════════════════════════════

def generate_interview_questions(
        resume_text : str,
        skills      : list,
        total       : int = 8
) -> list:
    """
    Resume aur skills ke basis par interview questions generate karta hai.

    Args:
        resume_text : Resume ka extracted text
        skills      : Pehle extract ki gayi skills ki list
        total       : Kitne questions chahiye (default: 8)

    Returns:
        List of dicts:
        [
          {"question": "Tell me about yourself.", "type": "behavioral", "topic": "Introduction"},
          {"question": "Explain your Python experience.", "type": "technical", "topic": "Python"},
          ...
        ]
    """
    skills_str = ", ".join(skills[:8])

    system = (
        "You are an experienced technical interviewer. "
        "Create relevant, clear interview questions based on the candidate's resume."
    )

    prompt = f"""
Create exactly {total} interview questions for a candidate with these skills: {skills_str}

Resume (first 2000 characters):
\"\"\"
{resume_text[:2000]}
\"\"\"

Rules:
- Question 1 MUST be: "Tell me about yourself."
- Mix: ~60% technical (based on their specific skills), ~40% behavioral (STAR method)
- Start easy, gradually get harder
- Each question must be clear and open-ended

Return ONLY a valid JSON array. No explanation. No extra text.
Format:
[
  {{"question": "Tell me about yourself.", "type": "behavioral", "topic": "Introduction"}},
  {{"question": "...", "type": "technical", "topic": "Python"}}
]
"""

    try:
        reply     = _chat(system, prompt, temperature=0.5)
        questions = _parse_json(reply)

        if isinstance(questions, list) and len(questions) > 0:
            clean = []
            for item in questions[:total]:
                if isinstance(item, dict) and item.get("question"):
                    clean.append({
                        "question" : str(item["question"]).strip(),
                        "type"     : str(item.get("type",  "general")).strip(),
                        "topic"    : str(item.get("topic", "General")).strip(),
                    })
            if clean:
                return clean

        return _fallback_questions()

    except Exception as e:
        print(f"[ai_engine] generate_questions error: {e}")
        return _fallback_questions()


def _fallback_questions() -> list:
    """Agar AI fail ho jaaye toh yeh generic questions return karo."""
    return [
        {"question": "Tell me about yourself.", "type": "behavioral", "topic": "Introduction"},
        {"question": "What are your strongest technical skills?", "type": "technical", "topic": "Skills"},
        {"question": "Describe a challenging project you worked on.", "type": "behavioral", "topic": "Experience"},
        {"question": "How do you approach debugging a complex problem?", "type": "technical", "topic": "Problem Solving"},
        {"question": "How do you keep your technical skills updated?", "type": "behavioral", "topic": "Learning"},
        {"question": "Explain a technical concept from your resume in simple terms.", "type": "technical", "topic": "Communication"},
        {"question": "Describe a time you worked in a team. What was your role?", "type": "behavioral", "topic": "Teamwork"},
        {"question": "Where do you see yourself professionally in 3 years?", "type": "behavioral", "topic": "Goals"},
    ]


# ════════════════════════════════════════════════════════════
#  FUNCTION 3: Answer Evaluate karo
# ════════════════════════════════════════════════════════════

def evaluate_answer(question: str, answer: str) -> dict:
    """
    Candidate ke ek jawab ko evaluate karke score aur feedback deta hai.

    Args:
        question : Interview question jo poocha gaya tha
        answer   : Candidate ka jawab

    Returns:
        {
          "score"        : 75,          (0 se 100 tak)
          "feedback"     : "Good answer...",
          "strengths"    : ["Clear explanation", "Good example"],
          "improvements" : ["Add more detail", "Mention specific tools"]
        }
    """
    system = (
        "You are a fair and constructive interview evaluator. "
        "Give honest scores and helpful, specific feedback."
    )

    prompt = f"""
Evaluate this interview answer fairly.

Question: "{question}"

Candidate's Answer: "{answer}"

Scoring criteria (total 100 points):
- Relevance to the question: 30 points
- Depth and detail of knowledge: 25 points  
- Clarity of communication: 25 points
- Use of concrete examples: 20 points

Return ONLY a valid JSON object. No explanation. No extra text.
{{
  "score"        : <integer 0 to 100>,
  "feedback"     : "<2-3 sentence honest assessment>",
  "strengths"    : ["<what they did well>", "<another strength>"],
  "improvements" : ["<specific improvement>", "<another improvement>"]
}}
"""

    try:
        reply  = _chat(system, prompt, temperature=0.3)
        result = _parse_json(reply)

        if isinstance(result, dict):
            return {
                "score"        : max(0, min(100, int(result.get("score", 50)))),
                "feedback"     : str(result.get("feedback", "")),
                "strengths"    : list(result.get("strengths", [])),
                "improvements" : list(result.get("improvements", [])),
            }

    except Exception as e:
        print(f"[ai_engine] evaluate_answer error: {e}")

    # Fallback agar kuch bhi kaam na kare
    return {
        "score"        : 50,
        "feedback"     : "Answer received. Please ensure your GROQ_API_KEY is set correctly.",
        "strengths"    : ["You attempted the question"],
        "improvements" : ["Provide more specific examples", "Check API key configuration"],
    }


# ════════════════════════════════════════════════════════════
#  FUNCTION 4: Final Holistic Feedback Generate karo
# ════════════════════════════════════════════════════════════

def generate_final_feedback(qa_results: list, overall_score: int) -> dict:
    """
    Poore interview ka ek holistic summary banata hai.

    Args:
        qa_results    : Saare {question, answer, score} objects ki list
        overall_score : Average score (0-100)

    Returns:
        {
          "summary"          : "Overall, the candidate showed...",
          "top_strengths"    : ["strength 1", "strength 2", "strength 3"],
          "top_improvements" : ["area 1", "area 2", "area 3"]
        }
    """
    # Compact transcript banao (token save karne ke liye)
    transcript = "\n\n".join([
        f"Q: {r['question']}\nA: {r['answer']}\nScore: {r.get('score','N/A')}/100"
        for r in qa_results
    ])

    system = (
        "You are a senior hiring manager writing a concise candidate performance summary. "
        "Be constructive and specific."
    )

    prompt = f"""
Overall interview score: {overall_score}/100

Interview transcript:
\"\"\"
{transcript[:3000]}
\"\"\"

Write a brief holistic assessment.

Return ONLY a valid JSON object. No extra text.
{{
  "summary"          : "<3-4 sentence overall assessment of the candidate>",
  "top_strengths"    : ["<strength 1>", "<strength 2>", "<strength 3>"],
  "top_improvements" : ["<area 1>", "<area 2>", "<area 3>"]
}}
"""

    try:
        reply  = _chat(system, prompt, temperature=0.4)
        result = _parse_json(reply)
        if isinstance(result, dict):
            return result

    except Exception as e:
        print(f"[ai_engine] final_feedback error: {e}")

    return {
        "summary"          : f"The candidate completed the interview with an overall score of {overall_score}/100.",
        "top_strengths"    : ["Completed all questions", "Showed engagement", "Provided responses"],
        "top_improvements" : ["Review technical concepts", "Use STAR method for behavioral questions", "Add more specific examples"],
    }
