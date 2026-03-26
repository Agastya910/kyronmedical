import aiosqlite
import json
import os
from typing import Optional, Dict, Any

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "kyron.db")

async def init_db():
    # Ensure data dir exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                patient_id TEXT PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                dob TEXT,
                phone TEXT,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS kv_store (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        await db.commit()

async def get_availability() -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT value FROM kv_store WHERE key = ?', ('availability',)) as cursor:
            row = await cursor.fetchone()
            if row:
                return json.loads(row[0])
            return None

async def save_availability(avail_data: Dict[str, Any]):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT OR REPLACE INTO kv_store (key, value) VALUES (?, ?)',
            ('availability', json.dumps(avail_data))
        )
        await db.commit()

async def save_patient(patient: Dict[str, Any]):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT OR REPLACE INTO patients (patient_id, first_name, last_name, dob, phone, email)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            patient.get('patient_id'),
            patient.get('first_name', '').strip(),
            patient.get('last_name', '').strip(),
            patient.get('dob', '').strip(),
            patient.get('phone', '').strip(),
            patient.get('email', '').strip()
        ))
        await db.commit()

async def get_patient_by_id(patient_id: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM patients WHERE patient_id = ?', (patient_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

async def search_patient(phone: str = "", first_name: str = "", last_name: str = "", email: str = "") -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        if phone:
            async with db.execute('SELECT * FROM patients WHERE phone = ?', (phone.strip(),)) as cursor:
                row = await cursor.fetchone()
                if row: return dict(row)
                
        if email:
            async with db.execute('SELECT * FROM patients WHERE LOWER(email) = ?', (email.strip().lower(),)) as cursor:
                row = await cursor.fetchone()
                if row: return dict(row)

        if first_name and last_name:
            async with db.execute(
                'SELECT * FROM patients WHERE LOWER(first_name) = ? AND LOWER(last_name) = ?',
                (first_name.strip().lower(), last_name.strip().lower())
            ) as cursor:
                row = await cursor.fetchone()
                if row: return dict(row)

        return None
