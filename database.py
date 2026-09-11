import sqlite3
import os
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "people_counter.db")

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database tables and runs schema migrations if needed."""
    conn = get_db()
    cursor = conn.cursor()

    # Individual crossing event logs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entrances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            date_str TEXT NOT NULL,
            hour_int INTEGER NOT NULL,
            zone TEXT NOT NULL DEFAULT 'men',          -- 'men' or 'women'
            direction TEXT NOT NULL DEFAULT 'in',      -- 'in' or 'out'
            person_type TEXT NOT NULL,                 -- 'adult' or 'child'
            fee_charged REAL NOT NULL DEFAULT 0.0,
            track_id INTEGER
        )
    """)

    # Schema migration for existing entrances table
    cursor.execute("PRAGMA table_info(entrances)")
    cols = [row[1] for row in cursor.fetchall()]
    if "zone" not in cols:
        cursor.execute("ALTER TABLE entrances ADD COLUMN zone TEXT NOT NULL DEFAULT 'men'")
    if "direction" not in cols:
        cursor.execute("ALTER TABLE entrances ADD COLUMN direction TEXT NOT NULL DEFAULT 'in'")

    # Daily aggregated summaries
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_summaries (
            date_str TEXT PRIMARY KEY,
            men_in INTEGER DEFAULT 0,
            men_out INTEGER DEFAULT 0,
            women_in INTEGER DEFAULT 0,
            women_out INTEGER DEFAULT 0,
            total_adults INTEGER DEFAULT 0,
            total_children INTEGER DEFAULT 0,
            total_entrances INTEGER DEFAULT 0,
            total_revenue REAL DEFAULT 0.0,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Schema migration for existing daily_summaries table
    cursor.execute("PRAGMA table_info(daily_summaries)")
    dcols = [row[1] for row in cursor.fetchall()]
    for col, ctype in [
        ("men_in", "INTEGER DEFAULT 0"),
        ("men_out", "INTEGER DEFAULT 0"),
        ("women_in", "INTEGER DEFAULT 0"),
        ("women_out", "INTEGER DEFAULT 0")
    ]:
        if col not in dcols:
            cursor.execute(f"ALTER TABLE daily_summaries ADD COLUMN {col} {ctype}")

    conn.commit()
    conn.close()

def record_event(zone="men", direction="in", person_type="adult", fee=20.0, track_id=None):
    """Records an entrance or exit event for a specific zone and updates daily summaries."""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    hour_int = now.hour
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")

    # Only charge fee for entrance
    effective_fee = fee if direction == "in" else 0.0

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO entrances (timestamp, date_str, hour_int, zone, direction, person_type, fee_charged, track_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (timestamp_str, date_str, hour_int, zone, direction, person_type, effective_fee, track_id))

        is_adult = 1 if (direction == "in" and person_type == "adult") else 0
        is_child = 1 if (direction == "in" and person_type == "child") else 0
        is_entrance = 1 if direction == "in" else 0
        men_in_inc = 1 if (zone == "men" and direction == "in") else 0
        men_out_inc = 1 if (zone == "men" and direction == "out") else 0
        women_in_inc = 1 if (zone == "women" and direction == "in") else 0
        women_out_inc = 1 if (zone == "women" and direction == "out") else 0

        cursor.execute("""
            INSERT INTO daily_summaries (
                date_str, men_in, men_out, women_in, women_out,
                total_adults, total_children, total_entrances, total_revenue, last_updated
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date_str) DO UPDATE SET
                men_in = men_in + excluded.men_in,
                men_out = men_out + excluded.men_out,
                women_in = women_in + excluded.women_in,
                women_out = women_out + excluded.women_out,
                total_adults = total_adults + excluded.total_adults,
                total_children = total_children + excluded.total_children,
                total_entrances = total_entrances + excluded.total_entrances,
                total_revenue = total_revenue + excluded.total_revenue,
                last_updated = excluded.last_updated
        """, (date_str, men_in_inc, men_out_inc, women_in_inc, women_out_inc,
              is_adult, is_child, is_entrance, effective_fee, timestamp_str))

        conn.commit()
    finally:
        conn.close()

def record_entrance(person_type="adult", fee=20.0, track_id=None, zone="men"):
    """Backwards compatibility wrapper for entrance events."""
    return record_event(zone=zone, direction="in", person_type=person_type, fee=fee, track_id=track_id)

def get_today_stats(fee_per_adult=20.0, fee_per_child=0.0, charge_children=False):
    """Retrieves live real-time metrics broken down by zone (Men/Women) and overall total."""
    today_str = date.today().strftime("%Y-%m-%d")
    conn = get_db()
    cursor = conn.cursor()

    try:
        # Query men metrics
        cursor.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN direction = 'in' AND person_type = 'adult' THEN 1 ELSE 0 END), 0) as men_adults,
                COALESCE(SUM(CASE WHEN direction = 'in' AND person_type = 'child' THEN 1 ELSE 0 END), 0) as men_children,
                COALESCE(SUM(CASE WHEN direction = 'in' THEN 1 ELSE 0 END), 0) as men_in,
                COALESCE(SUM(CASE WHEN direction = 'out' THEN 1 ELSE 0 END), 0) as men_out
            FROM entrances
            WHERE date_str = ? AND zone = 'men'
        """, (today_str,))
        mrow = cursor.fetchone()
        men_adults = mrow["men_adults"] if mrow else 0
        men_children = mrow["men_children"] if mrow else 0
        men_in = mrow["men_in"] if mrow else 0
        men_out = mrow["men_out"] if mrow else 0
        men_inside = max(0, men_in - men_out)

        # Query women metrics
        cursor.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN direction = 'in' AND person_type = 'adult' THEN 1 ELSE 0 END), 0) as women_adults,
                COALESCE(SUM(CASE WHEN direction = 'in' AND person_type = 'child' THEN 1 ELSE 0 END), 0) as women_children,
                COALESCE(SUM(CASE WHEN direction = 'in' THEN 1 ELSE 0 END), 0) as women_in,
                COALESCE(SUM(CASE WHEN direction = 'out' THEN 1 ELSE 0 END), 0) as women_out
            FROM entrances
            WHERE date_str = ? AND zone = 'women'
        """, (today_str,))
        wrow = cursor.fetchone()
        women_adults = wrow["women_adults"] if wrow else 0
        women_children = wrow["women_children"] if wrow else 0
        women_in = wrow["women_in"] if wrow else 0
        women_out = wrow["women_out"] if wrow else 0
        women_inside = max(0, women_in - women_out)

        # Totals
        total_adults = men_adults + women_adults
        total_children = men_children + women_children
        total_in = men_in + women_in
        total_out = men_out + women_out
        total_inside = men_inside + women_inside

        # Revenue calculations
        men_revenue = men_adults * fee_per_adult
        if charge_children:
            men_revenue += men_children * fee_per_child

        women_revenue = women_adults * fee_per_adult
        if charge_children:
            women_revenue += women_children * fee_per_child

        total_revenue = men_revenue + women_revenue

        return {
            "date": today_str,
            "total_count": total_in,
            "total_out": total_out,
            "total_inside": total_inside,
            "adult_count": total_adults,
            "child_count": total_children,
            "total_revenue": total_revenue,
            "price_per_adult": fee_per_adult,
            "price_per_child": fee_per_child,
            "charge_children": charge_children,
            "men": {
                "in": men_in,
                "out": men_out,
                "inside": men_inside,
                "adults": men_adults,
                "children": men_children,
                "revenue": men_revenue
            },
            "women": {
                "in": women_in,
                "out": women_out,
                "inside": women_inside,
                "adults": women_adults,
                "children": women_children,
                "revenue": women_revenue
            }
        }
    finally:
        conn.close()

def get_hourly_breakdown(date_str=None):
    """Returns hourly entrance distribution split by men and women."""
    if not date_str:
        date_str = date.today().strftime("%Y-%m-%d")

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT hour_int,
                   COUNT(*) as count,
                   SUM(CASE WHEN zone = 'men' AND direction = 'in' THEN 1 ELSE 0 END) as men_in,
                   SUM(CASE WHEN zone = 'women' AND direction = 'in' THEN 1 ELSE 0 END) as women_in,
                   SUM(CASE WHEN direction = 'in' AND person_type = 'adult' THEN 1 ELSE 0 END) as adults,
                   SUM(CASE WHEN direction = 'in' AND person_type = 'child' THEN 1 ELSE 0 END) as children
            FROM entrances
            WHERE date_str = ? AND direction = 'in'
            GROUP BY hour_int
            ORDER BY hour_int ASC
        """, (date_str,))
        rows = cursor.fetchall()

        hourly_data = {
            h: {
                "hour": f"{h:02d}:00",
                "total": 0,
                "men_in": 0,
                "women_in": 0,
                "adults": 0,
                "children": 0
            } for h in range(24)
        }
        for r in rows:
            h = r["hour_int"]
            hourly_data[h] = {
                "hour": f"{h:02d}:00",
                "total": r["count"],
                "men_in": r["men_in"],
                "women_in": r["women_in"],
                "adults": r["adults"],
                "children": r["children"]
            }

        return list(hourly_data.values())
    finally:
        conn.close()

def get_recent_entrances(limit=25):
    """Lists the most recent entrance and exit events."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, timestamp, zone, direction, person_type, fee_charged, track_id
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
            SELECT date_str, men_in, men_out, women_in, women_out,
                   total_adults, total_children, total_entrances, total_revenue, last_updated
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
