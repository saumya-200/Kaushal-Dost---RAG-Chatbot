import sqlite3
import hashlib
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class ChangeDetector:
    def __init__(self, db_path: str = "data/ingestion_state.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chunk_state (
                    source_id    TEXT PRIMARY KEY,
                    hash_sha256  TEXT NOT NULL,
                    version      INTEGER DEFAULT 1,
                    first_seen   TEXT NOT NULL,
                    last_seen    TEXT NOT NULL,
                    last_changed TEXT NOT NULL,
                    chunk_count  INTEGER DEFAULT 0
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_hash ON chunk_state(hash_sha256)')
            conn.commit()
        finally:
            conn.close()

    def _compute_source_hash(self, source_chunks: list[dict]) -> str:
        """Computes a single hash representing all chunks for a given source."""
        # Sort by chunk_index to ensure deterministic hashing
        sorted_chunks = sorted(source_chunks, key=lambda x: x.get('chunk_index', 0))
        combined_hash_content = "".join([c['hash_sha256'] for c in sorted_chunks])
        return hashlib.sha256(combined_hash_content.encode('utf-8')).hexdigest()

    def check_and_update(self, chunks: list[dict]) -> dict:
        """
        Processes chunks, checking against previous state to identify what has changed.
        """
        # Group chunks by source_id
        source_map = {}
        for chunk in chunks:
            source_id = chunk['source_id']
            if source_id not in source_map:
                source_map[source_id] = []
            source_map[source_id].append(chunk)

        new_sources = []
        changed_sources = []
        unchanged_sources = []
        
        now = datetime.now(timezone.utc).isoformat()

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            
            for source_id, source_chunks in source_map.items():
                current_hash = self._compute_source_hash(source_chunks)
                chunk_count = len(source_chunks)
                
                # Check existing state
                cursor.execute('SELECT hash_sha256, version FROM chunk_state WHERE source_id = ?', (source_id,))
                row = cursor.fetchone()
                
                if row is None:
                    # New source
                    cursor.execute('''
                        INSERT INTO chunk_state 
                        (source_id, hash_sha256, version, first_seen, last_seen, last_changed, chunk_count)
                        VALUES (?, ?, 1, ?, ?, ?, ?)
                    ''', (source_id, current_hash, now, now, now, chunk_count))
                    new_sources.append(source_id)
                else:
                    db_hash, db_version = row
                    if db_hash == current_hash:
                        # Unchanged source
                        cursor.execute('''
                            UPDATE chunk_state 
                            SET last_seen = ?, chunk_count = ?
                            WHERE source_id = ?
                        ''', (now, chunk_count, source_id))
                        unchanged_sources.append(source_id)
                    else:
                        # Changed source
                        new_version = db_version + 1
                        cursor.execute('''
                            UPDATE chunk_state 
                            SET hash_sha256 = ?, version = ?, last_seen = ?, last_changed = ?, chunk_count = ?
                            WHERE source_id = ?
                        ''', (current_hash, new_version, now, now, chunk_count, source_id))
                        changed_sources.append(source_id)
                        
            conn.commit()
        finally:
            conn.close()

        return {
            "new": new_sources,
            "changed": changed_sources,
            "unchanged": unchanged_sources,
            "summary": {
                "total_sources": len(source_map),
                "new_count": len(new_sources),
                "changed_count": len(changed_sources),
                "unchanged_count": len(unchanged_sources)
            }
        }

    def get_sources_needing_embedding(self) -> list[str]:
        """Returns source_ids that are new or changed since last embedding run."""
        # Simple implementation: Anything where last_seen == last_changed is considered needing embedding
        # In a real production system, you'd have an 'embedded_at' column to compare against.
        # Since we're doing this locally and embedding everything changed together, this suffices.
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT source_id FROM chunk_state 
                WHERE last_seen = last_changed
            ''')
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    def mark_embedded(self, source_ids: list[str]):
        """Marks sources as embedded. (Placeholder if needed for more complex tracking)"""
        pass
