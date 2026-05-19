"""
=============================================================
  AI Interview Agent (FREE Version) - Flask Backend
=============================================================
  Ab OpenAI ki jagah GROQ use hota hai — BILKUL FREE!

  Yeh file karta hai:
  1. Frontend HTML page serve karta hai
  2. Resume upload handle karta hai
  3. Groq AI se questions generate karta hai
  4. Candidate ke answers evaluate karta hai
  5. SQLite database mein results save karta hai

  CHALANE KA TARIKA:
    1. pip install -r requirements.txt
    2. cp .env.example .env  (aur apni Groq key daalo)
    3. python app.py
    4. Browser mein kholo: http://localhost:5000
=============================================================
"""

import os
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# ── Hamare helper modules import karo ────────────────────────
from resume_parser import extract_text
from ai_engine     import (
    extract_skills_from_resume,
    generate_interview_questions,
    evaluate_answer,
    generate_final_feedback,
)
from database import init_db, save_session, get_all_sessions

# ── .env file load karo (GROQ_API_KEY padhne ke liye) ────────
load_dotenv()

# ── Flask App banao ───────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')
app = Flask(__name__, static_folder=os.path.join(FRONTEND_DIR, 'static'))
CORS(app)

# ── File upload settings ──────────────────────────────────────
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'uploads')
ALLOWED_TYPES = {'pdf', 'docx', 'txt'}
MAX_FILE_SIZE = 5 * 1024 * 1024   # 5 MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER']       = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH']  = MAX_FILE_SIZE

# ── Database initialize karo ─────────────────────────────────
init_db()


def allowed_file(filename):
    """Check karo ki file extension allowed hai ya nahi."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_TYPES


# ════════════════════════════════════════════════════════════
#  ROUTE 1: Frontend serve karo
# ════════════════════════════════════════════════════════════

@app.route('/')
def index():
    """Browser mein http://localhost:5000 khulte hi yeh page dikhta hai."""
    return send_from_directory(FRONTEND_DIR, 'index.html')


# ════════════════════════════════════════════════════════════
#  ROUTE 2: Resume upload → skills → questions
# ════════════════════════════════════════════════════════════

@app.route('/api/start-interview', methods=['POST'])
def start_interview():
    """
    Input  : multipart form — 'resume' (file) + 'candidate_name' (text)
    Output : { session_id, candidate_name, skills, questions }
    """
    if 'resume' not in request.files:
        return jsonify({'error': 'Resume file nahi mila. Please file attach karo.'}), 400

    file = request.files['resume']

    if file.filename == '':
        return jsonify({'error': 'Koi file select nahi ki. Please file choose karo.'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Sirf PDF, DOCX aur TXT files allowed hain.'}), 400

    candidate_name = request.form.get('candidate_name', 'Candidate').strip() or 'Candidate'

    try:
        # Step 1: File save karo temporarily
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Step 2: Resume se text nikalo
        resume_text = extract_text(filepath)
        if not resume_text or len(resume_text.strip()) < 30:
            return jsonify({'error': 'Resume ka text nahi padhа gaya. Text-based PDF ya TXT try karo.'}), 400

        # Step 3: AI se skills nikalo
        skills = extract_skills_from_resume(resume_text)

        # Step 4: AI se questions generate karo
        questions = generate_interview_questions(resume_text, skills)

        # Step 5: Database mein session save karo
        session_id = save_session(
            candidate_name = candidate_name,
            resume_text    = resume_text,
            skills         = json.dumps(skills),
            questions      = json.dumps(questions),
        )

        # Step 6: Upload ki gayi file delete karo
        os.remove(filepath)

        return jsonify({
            'session_id'     : session_id,
            'candidate_name' : candidate_name,
            'skills'         : skills,
            'questions'      : questions,
        })

    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500


# ════════════════════════════════════════════════════════════
#  ROUTE 3: Answer evaluate karo
# ════════════════════════════════════════════════════════════

@app.route('/api/evaluate', methods=['POST'])
def evaluate():
    """
    Input  : JSON { session_id, question, answer, question_index }
    Output : { score, feedback, strengths, improvements }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Koi data nahi mila.'}), 400

    question = data.get('question', '').strip()
    answer   = data.get('answer',   '').strip()

    if not question or not answer:
        return jsonify({'error': 'Question aur answer dono required hain.'}), 400

    if len(answer) < 5:
        return jsonify({'error': 'Thoda aur detail mein jawab do.'}), 400

    try:
        result = evaluate_answer(question, answer)
        return jsonify({
            'score'        : result.get('score',        50),
            'feedback'     : result.get('feedback',     ''),
            'strengths'    : result.get('strengths',    []),
            'improvements' : result.get('improvements', []),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ════════════════════════════════════════════════════════════
#  ROUTE 4: Final report generate karo
# ════════════════════════════════════════════════════════════

@app.route('/api/final-report', methods=['POST'])
def final_report():
    """
    Input  : JSON { session_id, qa_results: [{question,answer,score,...}] }
    Output : { overall_score, grade, emoji, summary, top_strengths, top_improvements }
    """
    data       = request.get_json()
    session_id = data.get('session_id')
    qa_results = data.get('qa_results', [])

    if not qa_results:
        return jsonify({'error': 'Interview results nahi mile.'}), 400

    try:
        # Average score calculate karo
        scores        = [r.get('score', 50) for r in qa_results]
        overall_score = round(sum(scores) / len(scores))

        # Grade assign karo
        if overall_score >= 85:
            grade, emoji = 'A', '🌟'
        elif overall_score >= 70:
            grade, emoji = 'B', '👍'
        elif overall_score >= 55:
            grade, emoji = 'C', '📚'
        else:
            grade, emoji = 'D', '💪'

        # AI se holistic summary lo
        summary_data = generate_final_feedback(qa_results, overall_score)

        # Database update karo
        if session_id:
            from database import update_session_score
            update_session_score(
                session_id    = session_id,
                overall_score = overall_score,
                grade         = grade,
                qa_results    = json.dumps(qa_results),
                summary       = summary_data.get('summary', ''),
            )

        return jsonify({
            'overall_score'    : overall_score,
            'grade'            : grade,
            'emoji'            : emoji,
            'summary'          : summary_data.get('summary',          ''),
            'top_strengths'    : summary_data.get('top_strengths',    []),
            'top_improvements' : summary_data.get('top_improvements', []),
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ════════════════════════════════════════════════════════════
#  ROUTE 5: Interview history dekho
# ════════════════════════════════════════════════════════════

@app.route('/api/history', methods=['GET'])
def history():
    """SQLite se saari past interview sessions return karo."""
    try:
        sessions = get_all_sessions()
        return jsonify({'sessions': sessions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Server start karo ─────────────────────────────────────────
if __name__ == '__main__':
    print("\n" + "=" * 58)
    print("  🤖  AI Interview Agent — FREE Version (Groq)")
    print("=" * 58)
    print("  ✅  Server:    http://localhost:5000")
    print("  🆓  AI Model:  Groq llama-3.3-70b (FREE!)")
    print("  📂  Uploads:   ./uploads/")
    print("  🗄️   Database:  ./database/interviews.db")
    print("=" * 58 + "\n")
    app.run(debug=True, port=5000)
