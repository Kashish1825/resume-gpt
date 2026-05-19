"""
=============================================================
  database.py  —  SQLite Database Helper
=============================================================
  Stores every interview session so you can review them later.

  Table: interview_sessions
  Columns:
    id             INTEGER  Primary key, auto-incremented
    candidate_name TEXT     Name entered on the upload screen
    resume_text    TEXT     Raw text extracted from resume
    skills         TEXT     JSON array of skills
    questions      TEXT     JSON array of question objects
    qa_results     TEXT     JSON array of {question,answer,score}
    overall_score  INTEGER  Final average score (0–100)
    grade          TEXT     A / B / C / D
    summary        TEXT     AI-written holistic feedback
    created_at     TEXT     ISO timestamp

  Functions exported:
    init_db()               ─ Create table if it doesn't exist
    save_session(...)       ─ Insert a new session, return its id
    update_session_score()  ─ Add score + grade after interview ends
    get_all_sessions()      ─ Return all rows as a list of dicts
=============================================================
"""

import os
import sqlite3
from datetime import datetime


# Path to the SQLite file  (stored in  ../database/interviews.db)
DB_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'database', 'interviews.db'
)

# Make sure the database directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


# ════════════════════════════════════════════════════════════
#  CONNECTION HELPER
# ════════════════════════════════════════════════════════════

def _get_conn() -> sqlite3.Connection:
    """
    Opens (or creates) the SQLite database file and returns a connection.
    row_factory lets us get results as dictionaries instead of plain tuples.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # Access columns by name: row['score']
    return conn


# ════════════════════════════════════════════════════════════
#  1.  Create the table (called once at app startup)
# ════════════════════════════════════════════════════════════

def init_db():
    """
    Creates the interview_sessions table if it doesn't already exist.
    Safe to call every time the app starts — won't overwrite existing data.
    """
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS interview_sessions (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_name TEXT    NOT NULL,
            resume_text    TEXT,
            skills         TEXT,
            questions      TEXT,
            qa_results     TEXT,
            overall_score  INTEGER,
            grade          TEXT,
            summary        TEXT,
            created_at     TEXT    NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    print("[database] ✅ SQLite ready:", DB_PATH)


# ════════════════════════════════════════════════════════════
#  2.  Save a new interview session (at the START)
# ════════════════════════════════════════════════════════════

def save_session(
    candidate_name : str,
    resume_text    : str,
    skills         : str,   # JSON string
    questions      : str    # JSON string
) -> int:
    """
    Inserts a new row with the resume + questions.
    The score columns are left empty — filled in later.

    Returns:
        The auto-generated integer ID of the new row.
    """
    conn = _get_conn()
    cursor = conn.execute(
        """
        INSERT INTO interview_sessions
            (candidate_name, resume_text, skills, questions, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            candidate_name,
            resume_text[:5000],       # Store only first 5000 chars
            skills,
            questions,
            datetime.now().isoformat()
        )
    )
    session_id = cursor.lastrowid     # SQLite gives us the new row's id
    conn.commit()
    conn.close()
    return session_id


# ════════════════════════════════════════════════════════════
#  3.  Update session with final score (at the END)
# ════════════════════════════════════════════════════════════

def update_session_score(
    session_id    : int,
    overall_score : int,
    grade         : str,
    qa_results    : str,   # JSON string
    summary       : str
):
    """
    Updates an existing row to add:
      - the Q&A results (questions + answers + per-question scores)
      - the overall score
      - the letter grade
      - the AI-written summary
    """
    conn = _get_conn()
    conn.execute(
        """
        UPDATE interview_sessions
        SET qa_results    = ?,
            overall_score = ?,
            grade         = ?,
            summary       = ?
        WHERE id = ?
        """,
        (qa_results, overall_score, grade, summary, session_id)
    )
    conn.commit()
    conn.close()


# ════════════════════════════════════════════════════════════
#  4.  Read all sessions (for the History screen)
# ════════════════════════════════════════════════════════════

def get_all_sessions() -> list[dict]:
    """
    Fetches every row from interview_sessions, newest first.

    Returns:
        A list of dicts with keys matching the column names.
    """
    conn  = _get_conn()
    rows  = conn.execute(
        "SELECT id, candidate_name, overall_score, grade, summary, created_at "
        "FROM interview_sessions ORDER BY id DESC"
    ).fetchall()
    conn.close()

    # Convert sqlite3.Row objects to plain dicts
    return [dict(row) for row in rows]
