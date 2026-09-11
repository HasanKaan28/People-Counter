import sqlite3
import os
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "people_counter.db")

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database tables."""
    conn = get_db()
    cursor = conn.cursor()

    # Individual entrance event logs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entrances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            date_str TEXT NOT NULL,
            hour_int INTEGER NOT NULL,
            person_type TEXT NOT NULL,  -- 'adult' or 'child'
            fee_charged REAL NOT NULL,
            track_id INTEGER
        )
    """)

    # Daily aggregated summaries
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_summaries (
            date_str TEXT PRIMARY KEY,
            total_adults INTEGER DEFAULT 0,
            total_children INTEGER DEFAULT 0,
            total_entrances INTEGER DEFAULT 0,
            total_revenue REAL DEFAULT 0.0,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

def record_entrance(person_type="adult", fee=20.0, track_id=None):
    """Records a new entrance event and updates daily summaries."""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    hour_int = now.hour
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO entrances (timestamp, date_str, hour_int, person_type, fee_charged, track_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (timestamp_str, date_str, hour_int, person_type, fee, track_id))

        is_adult = 1 if person_type == "adult" else 0
        is_child = 1 if person_type == "child" else 0

        cursor.execute("""
            INSERT INTO daily_summaries (date_str, total_adults, total_children, total_entrances, total_revenue, last_updated)
            VALUES (?, ?, ?, 1, ?, ?)
            ON CONFLICT(date_str) DO UPDATE SET
                total_adults = total_adults + excluded.total_adults,
                total_children = total_children + excluded.total_children,
                total_entrances = total_entrances + 1,
                total_revenue = total_revenue + excluded.total_revenue,
                last_updated = excluded.last_updated
        """, (date_str, is_adult, is_child, fee, timestamp_str))

        conn.commit()
    finally:
        conn.close()

def get_today_stats(fee_per_adult=20.0, fee_per_child=0.0, charge_children=False):
    """Retrieves live real-time metrics for the current date."""
    today_str = date.today().strftime("%Y-%m-%d")
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN person_type = 'adult' THEN 1 ELSE 0 END), 0) as adult_count,
                COALESCE(SUM(CASE WHEN person_type = 'child' THEN 1 ELSE 0 END), 0) as child_count,
                COUNT(*) as total_count,
                COALESCE(SUM(fee_charged), 0.0) as recorded_revenue
            FROM entrances
            WHERE date_str = ?
        """, (today_str,))
        row = cursor.fetchone()

        adult_count = row["adult_count"]
        child_count = row["child_count"]
        total_count = row["total_count"]

        # Dynamically calculate revenue based on active rate configuration
        calculated_revenue = (adult_count * fee_per_adult)
        if charge_children:
            calculated_revenue += (child_count * fee_per_child)

        return {
            "date": today_str,
            "adult_count": adult_count,
            "child_count": child_count,
            "total_count": total_count,
            "total_revenue": calculated_revenue,
            "price_per_adult": fee_per_adult,
            "price_per_child": fee_per_child,
            "charge_children": charge_children
        }
    finally:
        conn.close()

def get_hourly_breakdown(date_str=None):
    """Returns hourly entrance distribution."""
    if not date_str:
        date_str = date.today().strftime("%Y-%m-%d")

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT hour_int,
                   COUNT(*) as count,
                   SUM(CASE WHEN person_type = 'adult' THEN 1 ELSE 0 END) as adults,
                   SUM(CASE WHEN person_type = 'child' THEN 1 ELSE 0 END) as children
            FROM entrances
            WHERE date_str = ?
            GROUP BY hour_int
            ORDER BY hour_int ASC
        """, (date_str,))
        rows = cursor.fetchall()

        hourly_data = {h: {"hour": f"{h:02d}:00", "total": 0, "adults": 0, "children": 0} for h in range(24)}
        for r in rows:
            h = r["hour_int"]
            hourly_data[h] = {
                "hour": f"{h:02d}:00",
                "total": r["count"],
                "adults": r["adults"],
                "children": r["children"]
            }

        return list(hourly_data.values())
    finally:
        conn.close()

def get_recent_entrances(limit=20):
    """Lists the most recent entrance events."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, timestamp, person_type, fee_charged, track_id
            FROM entrances
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def get_daily_history(limit=30):
    """Retrieves summaries for previous dates."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT date_str, total_adults, total_children, total_entrances, total_revenue, last_updated
            FROM daily_summaries
            ORDER BY date_str DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def reset_today_data():
    """Resets counter metrics for the current date."""
    today_str = date.today().strftime("%Y-%m-%d")
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM entrances WHERE date_str = ?", (today_str,))
        cursor.execute("DELETE FROM daily_summaries WHERE date_str = ?", (today_str,))
        conn.commit()
    finally:
        conn.close()

# Initialize tables upon module load
init_db()
