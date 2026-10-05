import sqlite3
import hashlib
from urllib.parse import urlparse, urlunparse
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import json
import os

def get_db_path() -> Path:
    return Path.home() / ".job-apply-mcp" / "applications.db"

def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))

def init_db():
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS pipeline_jobs (
                url TEXT PRIMARY KEY,
                norm_url TEXT NOT NULL,
                title TEXT,
                company TEXT,
                platform TEXT,
                description TEXT,
                status TEXT NOT NULL,
                llm_score INTEGER,
                verdict TEXT,
                rating_json TEXT,
                resume_path TEXT,
                cover_note TEXT,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_pipeline_norm_url ON pipeline_jobs(norm_url)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_pipeline_status ON pipeline_jobs(status)')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS qa_cache (
                key TEXT PRIMARY KEY,
                answer TEXT,
                source TEXT NOT NULL,
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

def _qa_key(question: str, options: Optional[List[str]]) -> str:
    norm_q = question.strip().lower()
    if options:
        opts = sorted([o.strip().lower() for o in options])
        norm_q += "|" + "|".join(opts)
    return hashlib.sha1(norm_q.encode('utf-8')).hexdigest()

def get_cached_answer(question: str, options: Optional[List[str]] = None) -> Optional[Tuple[Any, str, float]]:
    key = _qa_key(question, options)
    with sqlite3.connect(get_db_path()) as conn:
        cur = conn.execute('SELECT answer, source, confidence FROM qa_cache WHERE key = ?', (key,))
        row = cur.fetchone()
        if row:
            ans, src, conf = row
            try:
                ans = json.loads(ans)
            except Exception:
                pass
            return ans, src, conf
    return None

def save_answer(question: str, options: Optional[List[str]], answer: Any, source: str, confidence: float):
    key = _qa_key(question, options)
    with sqlite3.connect(get_db_path()) as conn:
        # Check if existing is user
        cur = conn.execute('SELECT source FROM qa_cache WHERE key = ?', (key,))
        row = cur.fetchone()
        if row and row[0] == 'user' and source != 'user':
            return # NEVER overwrite user source with LLM
            
        ans_str = json.dumps(answer)
        conn.execute('''
            INSERT INTO qa_cache (key, answer, source, confidence)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                answer=excluded.answer,
                source=excluded.source,
                confidence=excluded.confidence
        ''', (key, ans_str, source, confidence))

def upsert_job(url: str, **kwargs):
    norm_url = normalize_url(url)
    updates = [f"{k}=?" for k in kwargs.keys()]
    values = list(kwargs.values())
    
    with sqlite3.connect(get_db_path()) as conn:
        cur = conn.execute('SELECT url FROM pipeline_jobs WHERE url = ?', (url,))
        if cur.fetchone():
            if updates:
                updates.append("updated_at=CURRENT_TIMESTAMP")
                q = f"UPDATE pipeline_jobs SET {', '.join(updates)} WHERE url = ?"
                conn.execute(q, values + [url])
        else:
            cols = ['url', 'norm_url'] + list(kwargs.keys())
            places = ', '.join(['?'] * len(cols))
            vals = [url, norm_url] + values
            conn.execute(f"INSERT INTO pipeline_jobs ({', '.join(cols)}) VALUES ({places})", vals)

def get_job(url: str) -> Optional[Dict[str, Any]]:
    with sqlite3.connect(get_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute('SELECT * FROM pipeline_jobs WHERE url = ?', (url,))
        row = cur.fetchone()
        return dict(row) if row else None
        
def get_jobs_by_status(status: str) -> List[Dict[str, Any]]:
    with sqlite3.connect(get_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute('SELECT * FROM pipeline_jobs WHERE status = ?', (status,))
        return [dict(r) for r in cur.fetchall()]
