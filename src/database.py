"""
Database handler for Evolution Gaming Baccarat Scraper
Stores results in SQLite for persistence and analysis
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite

from config import config

logger = logging.getLogger(__name__)


class Database:
    """Async SQLite database for baccarat results"""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.DATABASE_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: Optional[aiosqlite.Connection] = None
        self.rounds_captured: int = 0
        self.last_frame_at: Optional[str] = None

    async def connect(self):
        """Initialize database connection and create tables"""
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._create_tables()
        await self._load_initial_stats()
        logger.info(f"Database connected: {self.db_path}")

    async def close(self):
        """Close database connection"""
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("Database connection closed")

    async def _create_tables(self):
        """Create necessary tables if they don't exist"""
        await self._connection.executescript("""
            -- Main results table
            CREATE TABLE IF NOT EXISTS baccarat_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                round_id TEXT UNIQUE NOT NULL,
                timestamp TEXT NOT NULL,
                result TEXT NOT NULL CHECK(result IN ('P', 'B', 'T')),
                player_score INTEGER,
                banker_score INTEGER,
                player_cards TEXT,
                banker_cards TEXT,
                player_third_card TEXT,
                banker_third_card TEXT,
                is_natural INTEGER DEFAULT 0,
                lightning_cards TEXT,
                multipliers TEXT,
                table_id TEXT,
                shoe_id TEXT,
                raw_data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            -- Index for fast queries
            CREATE INDEX IF NOT EXISTS idx_timestamp ON baccarat_results(timestamp);
            CREATE INDEX IF NOT EXISTS idx_result ON baccarat_results(result);
            CREATE INDEX IF NOT EXISTS idx_table_id ON baccarat_results(table_id);
            CREATE INDEX IF NOT EXISTS idx_shoe_id ON baccarat_results(shoe_id);

            -- Shoes table to track shoe changes
            CREATE TABLE IF NOT EXISTS shoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shoe_id TEXT UNIQUE NOT NULL,
                table_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                total_rounds INTEGER DEFAULT 0,
                player_wins INTEGER DEFAULT 0,
                banker_wins INTEGER DEFAULT 0,
                ties INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            -- Session tracking
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                rounds_captured INTEGER DEFAULT 0,
                errors INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active'
            );
        """)
        await self._connection.commit()
        logger.info("Database tables created/verified")

    async def _load_initial_stats(self):
        """Load initial counters from database"""
        try:
            cursor = await self._connection.execute(
                "SELECT COUNT(*) as total FROM baccarat_results"
            )
            row = await cursor.fetchone()
            self.rounds_captured = int(row["total"] or 0)
        except Exception as e:
            logger.warning(f"Could not load initial stats: {e}")

    async def insert_result(self, result: Dict[str, Any]) -> int:
        """Insert a new baccarat result"""
        try:
            cursor = await self._connection.execute("""
                INSERT OR IGNORE INTO baccarat_results (
                    round_id, timestamp, result,
                    player_score, banker_score,
                    player_cards, banker_cards,
                    player_third_card, banker_third_card,
                    is_natural, lightning_cards, multipliers,
                    table_id, shoe_id, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.get('round_id'),
                result.get('timestamp', datetime.now(timezone.utc).isoformat()),
                result.get('result'),
                result.get('player_score'),
                result.get('banker_score'),
                json.dumps(result.get('player_cards', [])),
                json.dumps(result.get('banker_cards', [])),
                result.get('player_third_card'),
                result.get('banker_third_card'),
                1 if result.get('is_natural') else 0,
                json.dumps(result.get('lightning_cards', [])),
                json.dumps(result.get('multipliers', {})),
                result.get('table_id'),
                result.get('shoe_id'),
                json.dumps(result.get('raw_data', {}))
            ))
            await self._connection.commit()

            if cursor.rowcount > 0:
                self.rounds_captured += 1
                logger.info(
                    f"✅ Result saved: {result.get('result')}"
                    f" (Round: {result.get('round_id')})"
                )
                return cursor.lastrowid
            else:
                logger.debug(f"Result already exists: {result.get('round_id')}")
                return 0

        except Exception as e:
            logger.error(f"Error inserting result: {e}")
            raise

    async def get_recent_results(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get most recent results"""
        cursor = await self._connection.execute("""
            SELECT * FROM baccarat_results
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        rows = await cursor.fetchall()

        results = []
        for row in rows:
            result = dict(row)
            # Parse JSON fields
            for field in ['player_cards', 'banker_cards', 'lightning_cards',
                          'multipliers', 'raw_data']:
                if result.get(field):
                    try:
                        result[field] = json.loads(result[field])
                    except (json.JSONDecodeError, TypeError, ValueError):
                        pass
            results.append(result)

        return results

    async def get_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get statistics for recent period"""
        cursor = await self._connection.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN result = 'P' THEN 1 ELSE 0 END) as player_wins,
                SUM(CASE WHEN result = 'B' THEN 1 ELSE 0 END) as banker_wins,
                SUM(CASE WHEN result = 'T' THEN 1 ELSE 0 END) as ties,
                AVG(player_score) as avg_player_score,
                AVG(banker_score) as avg_banker_score
            FROM baccarat_results
            WHERE timestamp > datetime('now', ?)
        """, (f'-{hours} hours',))

        row = await cursor.fetchone()
        total = row['total'] or 0
        safe_total = total if total > 0 else 1

        return {
            'total_rounds': total,
            'player_wins': row['player_wins'] or 0,
            'banker_wins': row['banker_wins'] or 0,
            'ties': row['ties'] or 0,
            'player_percentage': round((row['player_wins'] or 0) / safe_total * 100, 2),
            'banker_percentage': round((row['banker_wins'] or 0) / safe_total * 100, 2),
            'tie_percentage': round((row['ties'] or 0) / safe_total * 100, 2),
            'avg_player_score': round(row['avg_player_score'] or 0, 2),
            'avg_banker_score': round(row['avg_banker_score'] or 0, 2),
            'period_hours': hours
        }

    async def get_current_streak(self) -> Dict[str, Any]:
        """Get current winning streak"""
        cursor = await self._connection.execute("""
            SELECT result FROM baccarat_results
            WHERE result != 'T'
            ORDER BY timestamp DESC
            LIMIT 50
        """)
        rows = await cursor.fetchall()

        if not rows:
            return {'side': None, 'length': 0}

        current_side = rows[0]['result']
        streak = 0

        for row in rows:
            if row['result'] == current_side:
                streak += 1
            else:
                break

        return {
            'side': 'Player' if current_side == 'P' else 'Banker',
            'side_code': current_side,
            'length': streak
        }


# Singleton instance
db = Database()


async def test_database():
    """Test database functionality"""
    await db.connect()

    # Insert test result
    test_result = {
        'round_id': f'test_{datetime.now().timestamp()}',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'result': 'B',
        'player_score': 5,
        'banker_score': 7,
        'player_cards': ['♠A', '♥4'],
        'banker_cards': ['♦K', '♣7'],
        'table_id': 'xxxtremelightningbaccarat',
        'shoe_id': 'test_shoe_1'
    }

    await db.insert_result(test_result)

    # Get recent results
    results = await db.get_recent_results(5)
    print(f"Recent results: {len(results)}")

    # Get statistics
    stats = await db.get_statistics(24)
    print(f"Statistics: {stats}")

    # Get streak
    streak = await db.get_current_streak()
    print(f"Current streak: {streak}")

    await db.close()


if __name__ == "__main__":
    asyncio.run(test_database())
