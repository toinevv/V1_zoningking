import sqlite3
from typing import Dict, List
import json
import os

class DocumentStorage:
    def __init__(self, db_path: str = "data/documents.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database with required tables"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create documents table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    gemeente TEXT,
                    doc_type TEXT,
                    title TEXT,
                    url TEXT,
                    local_path TEXT,
                    date_found DATE,
                    metadata TEXT,
                    relevant_paragraphs TEXT
                )
            ''')
            
            # Create opportunities table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS opportunities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    gemeente TEXT,
                    location TEXT,
                    doc_reference INTEGER,
                    opportunity_type TEXT,
                    description TEXT,
                    score FLOAT,
                    metadata TEXT,
                    FOREIGN KEY(doc_reference) REFERENCES documents(id)
                )
            ''')
            
            conn.commit()

    def store_document(self, doc_info: Dict) -> int:
        """Store document information in the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO documents (
                    gemeente, doc_type, title, url, local_path, 
                    date_found, metadata, relevant_paragraphs
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                doc_info['gemeente'],
                doc_info['type'],
                doc_info['title'],
                doc_info['url'],
                doc_info.get('local_path', ''),
                doc_info['date_found'],
                json.dumps(doc_info.get('metadata', {})),
                json.dumps(doc_info.get('relevant_paragraphs', []))
            ))
            
            return cursor.lastrowid

    def get_documents(self, gemeente: str = None) -> List[Dict]:
        """Retrieve documents from the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if gemeente:
                cursor.execute('SELECT * FROM documents WHERE gemeente = ?', (gemeente,))
            else:
                cursor.execute('SELECT * FROM documents')
            
            columns = [description[0] for description in cursor.description]
            documents = []
            
            for row in cursor.fetchall():
                doc = dict(zip(columns, row))
                doc['metadata'] = json.loads(doc['metadata'])
                doc['relevant_paragraphs'] = json.loads(doc['relevant_paragraphs'])
                documents.append(doc)
            
            return documents

    def store_opportunity(self, opportunity: Dict) -> int:
        """Store an identified opportunity"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO opportunities (
                    gemeente, location, doc_reference, opportunity_type,
                    description, score, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                opportunity['gemeente'],
                opportunity['location'],
                opportunity['doc_reference'],
                opportunity['type'],
                opportunity['description'],
                opportunity['score'],
                json.dumps(opportunity.get('metadata', {}))
            ))
            
            return cursor.lastrowid

    def get_opportunities(self, gemeente: str = None) -> List[Dict]:
        """Retrieve opportunities from the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if gemeente:
                cursor.execute('''
                    SELECT o.*, d.title as doc_title 
                    FROM opportunities o
                    LEFT JOIN documents d ON o.doc_reference = d.id
                    WHERE o.gemeente = ?
                ''', (gemeente,))
            else:
                cursor.execute('''
                    SELECT o.*, d.title as doc_title 
                    FROM opportunities o
                    LEFT JOIN documents d ON o.doc_reference = d.id
                ''')
            
            columns = [description[0] for description in cursor.description]
            opportunities = []
            
            for row in cursor.fetchall():
                opp = dict(zip(columns, row))
                opp['metadata'] = json.loads(opp['metadata'])
                opportunities.append(opp)
            
            return opportunities
        