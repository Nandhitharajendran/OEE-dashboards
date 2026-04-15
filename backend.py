# backend.py  — OEE Command Center
# Run: python backend.py
# Requires: pip install flask flask-cors pymysql requests

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import requests, logging, os
try:
    import pymysql
    pymysql.install_as_MySQLdb()
    import MySQLdb
except ImportError:
    MySQLdb = None

app = Flask(__name__, static_folder=".")
CORS(app, resources={r"/api/*": {"origins": "*"}})
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Superset (for guest token) ─────────────────────────────
SUPERSET_URL      = "http://localhost:8088"
SUPERSET_USERNAME = "admin"
SUPERSET_PASSWORD = "admin@123"

DASHBOARDS = {
    "oee":      {"uuid": "2a79fbe2-ee28-4c4c-bb11-c71ab0789fe7"},
    "downtime": {"uuid": "db1ff3aa-3cf9-47ec-9698-e67d6e785e6e"},
    "quality":  {"uuid": "d8e59cac-3eb6-4155-bb27-961d4a38b55a"},
    "energy":   {"uuid": "6d456c38-9613-452a-899d-96f89a1ee9f2"},
}

# ── MySQL connection (same DB Superset uses) ────────────────
DB_CONFIG = {
    "host":   "localhost",
    "port":   3306,
    "user":   "root",          # ← change if needed
    "password": "Nandy0827",   # ← change if needed
    "db":     "digifacto_index",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor if pymysql else None,
}

def get_db():
    if MySQLdb is None:
        raise RuntimeError("pymysql not installed: pip install pymysql")
    return pymysql.connect(**{k:v for k,v in DB_CONFIG.items() if v is not None and k != "cursorclass"},
                           cursorclass=pymysql.cursors.DictCursor)

def query(sql, params=None):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    finally:
        conn.close()

# ════════════════════════════════════════════════════════════
#  DATA API ENDPOINTS  (exact Superset SQL queries)
# ════════════════════════════════════════════════════════════

# ── OEE Master View ─────────────────────────────────────────
@app.route("/api/data/oee")
def api_oee():
    """Returns OEE Master View data — same SQL as Superset dataset"""
    try:
        rows = query("""
            SELECT
              s.shift_date,
              s.shift_name,
              s.shift_code,
              s.overall_status,
              GREATEST(o.availability, 0)                          AS availability,
              GREATEST(o.performance,  0)                          AS performance,
              GREATEST(o.quality,      0)                          AS quality,
              GREATEST((o.availability * o.performance * o.quality) / 10000, 0) AS oee_score,
              GREATEST(pp.plan_qty,    0)                          AS plan_qty,
              GREATEST(pp.actual_qty,  0)                          AS actual_qty,
              pp.line_name,
              pp.status AS line_status,
              CASE WHEN pp.plan_qty > 0
                   THEN ROUND((pp.actual_qty / pp.plan_qty) * 100, 1)
                   ELSE 0
              END AS achievement_pct
            FROM shift s
            LEFT JOIN oee_snapshot o        ON o.shift_id = s.id
            LEFT JOIN production_performance pp ON pp.shift_id = s.id
            WHERE s.shift_date IS NOT NULL
            ORDER BY s.shift_date DESC, s.shift_name
            LIMIT 2000
        """)
        # Convert date objects to strings
        for r in rows:
            if hasattr(r.get("shift_date"), "isoformat"):
                r["shift_date"] = r["shift_date"].isoformat()
        return jsonify({"data": rows, "count": len(rows)})
    except Exception as e:
        logger.error(f"OEE query error: {e}")
        return jsonify({"error": str(e)}), 500

# ── Downtime Events ─────────────────────────────────────────
@app.route("/api/data/downtime")
def api_downtime():
    """Returns Downtime Events data — same SQL as Superset dataset"""
    try:
        rows = query("""
            SELECT
              s.shift_date,
              s.shift_name,
              s.shift_code,
              d.machine_name,
              d.issue_description,
              GREATEST(COALESCE(d.duration_minutes, 0), 0) AS duration_minutes,
              GREATEST(COALESCE(d.production_impact, 0), 0) AS production_impact
            FROM shift s
            LEFT JOIN downtime_events d ON d.shift_id = s.id
            WHERE d.machine_name IS NOT NULL
            ORDER BY s.shift_date DESC, d.duration_minutes DESC
            LIMIT 5000
        """)
        for r in rows:
            if hasattr(r.get("shift_date"), "isoformat"):
                r["shift_date"] = r["shift_date"].isoformat()
        return jsonify({"data": rows, "count": len(rows)})
    except Exception as e:
        logger.error(f"Downtime query error: {e}")
        return jsonify({"error": str(e)}), 500

# ── Quality & Defects ────────────────────────────────────────
@app.route("/api/data/quality")
def api_quality():
    """Returns Quality & Defects data — same SQL as Superset dataset"""
    try:
        rows = query("""
            SELECT
              s.shift_date,
              s.shift_name,
              s.shift_code,
              GREATEST(q.rejection_rate, 0)             AS rejection_rate,
              COALESCE(q.threshold_limit, 3.0)          AS threshold_limit,
              COALESCE(q.major_defect, 'None')           AS major_defect,
              GREATEST(COALESCE(q.defect_units, 0), 0)  AS defect_units,
              CASE WHEN q.rejection_rate > COALESCE(q.threshold_limit, 3.0)
                   THEN 'CRITICAL' ELSE 'OK'
              END AS quality_status
            FROM shift s
            LEFT JOIN quality_summary q ON q.shift_id = s.id
            WHERE s.shift_date IS NOT NULL
            ORDER BY s.shift_date DESC
            LIMIT 5000
        """)
        for r in rows:
            if hasattr(r.get("shift_date"), "isoformat"):
                r["shift_date"] = r["shift_date"].isoformat()
        return jsonify({"data": rows, "count": len(rows)})
    except Exception as e:
        logger.error(f"Quality query error: {e}")
        return jsonify({"error": str(e)}), 500

# ── Energy Summary ───────────────────────────────────────────
@app.route("/api/data/energy")
def api_energy():
    """Returns Energy Summary data — same SQL as Superset dataset"""
    try:
        rows = query("""
            SELECT
              s.shift_date,
              s.shift_name,
              s.shift_code,
              GREATEST(e.total_consumption, 0)    AS total_consumption,
              GREATEST(e.energy_per_unit, 0)      AS energy_per_unit,
              COALESCE(e.baseline_target, 100)    AS baseline_target,
              COALESCE(e.abnormal_alert, 0)       AS abnormal_alert,
              CASE WHEN e.energy_per_unit > COALESCE(e.baseline_target, 100)
                   THEN 'OVER' ELSE 'NORMAL'
              END AS energy_status
            FROM shift s
            LEFT JOIN energy_summary e ON e.shift_id = s.id
            WHERE s.shift_date IS NOT NULL
            ORDER BY s.shift_date DESC
            LIMIT 5000
        """)
        for r in rows:
            if hasattr(r.get("shift_date"), "isoformat"):
                r["shift_date"] = r["shift_date"].isoformat()
        return jsonify({"data": rows, "count": len(rows)})
    except Exception as e:
        logger.error(f"Energy query error: {e}")
        return jsonify({"error": str(e)}), 500

# ════════════════════════════════════════════════════════════
#  EXISTING ENDPOINTS (guest token, health, static)
# ════════════════════════════════════════════════════════════

def get_guest_token(dashboard_uuid):
    session = requests.Session()
    r1 = session.post(f"{SUPERSET_URL}/api/v1/security/login",
        json={"username": SUPERSET_USERNAME, "password": SUPERSET_PASSWORD,
              "provider": "db", "refresh": True}, timeout=10)
    r1.raise_for_status()
    token = r1.json()["access_token"]
    r2 = session.get(f"{SUPERSET_URL}/api/v1/security/csrf_token/",
        headers={"Authorization": f"Bearer {token}", "Referer": SUPERSET_URL}, timeout=10)
    r2.raise_for_status()
    csrf = r2.json()["result"]
    r3 = session.post(f"{SUPERSET_URL}/api/v1/security/guest_token/",
        json={"user": {"username": "guest", "first_name": "Guest", "last_name": "User"},
              "resources": [{"type": "dashboard", "id": dashboard_uuid}], "rls": []},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                 "X-CSRFToken": csrf, "Referer": SUPERSET_URL}, timeout=10)
    r3.raise_for_status()
    return r3.json()["token"]

@app.route("/")
def index():
    if os.path.exists("oee_superset_dashboard.html"):
        return send_from_directory(".", "oee_superset_dashboard.html")
    return "<h2>Backend running</h2>"

@app.route("/api/guest-token")
def api_guest_token():
    uuid = DASHBOARDS.get(request.args.get("page", "oee"), DASHBOARDS["oee"])["uuid"]
    try:
        return jsonify({"token": get_guest_token(uuid), "supersetUrl": SUPERSET_URL, "uuid": uuid})
    except Exception as e:
        logger.error(str(e))
        return jsonify({"error": str(e)}), 500

@app.route("/api/health")
def health():
    db_ok = False
    try:
        query("SELECT 1")
        db_ok = True
    except Exception as e:
        pass
    superset_ok = False
    try:
        superset_ok = requests.get(f"{SUPERSET_URL}/health", timeout=3).status_code == 200
    except:
        pass
    return jsonify({"backend": "running", "db_connected": db_ok, "superset_reachable": superset_ok})

if __name__ == "__main__":
    print("=" * 55)
    print("  OEE Command Center — Backend")
    print("  http://127.0.0.1:5000")
    print("  Data APIs:")
    print("    /api/data/oee")
    print("    /api/data/downtime")
    print("    /api/data/quality")
    print("    /api/data/energy")
    print("=" * 55)
    app.run(host="127.0.0.1", port=5000, debug=False)





