# superset_config.py  — FIXED VERSION
# Place this file in:  D:\Python Intern 2026\week6\ApacheSuperset\superset_config.py
# Then restart Superset: superset run -p 8088 --with-threads --reload

import os

# ── Required for embedding ─────────────────────────────────────────────────────
FEATURE_FLAGS = {
    "EMBEDDED_SUPERSET":        True,   # enables /embedded/<uuid> route
    "EMBEDDABLE_CHARTS":        True,   # enables chart embedding
    "ENABLE_TEMPLATE_PROCESSING": True,
}

# ── Allow iframes from your HTML page ─────────────────────────────────────────
# This removes the X-Frame-Options: SAMEORIGIN header that blocks embedding
TALISMAN_ENABLED = False

# Suppress the CSP warning in your logs
CONTENT_SECURITY_POLICY_WARNING = False

# ── CORS — allow your backend (localhost:5000) to call Superset ────────────────
CORS_OPTIONS = {
    "supports_credentials": True,
    "allow_headers":        ["*"],
    "resources":            ["*"],
    "origins":              [
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "http://localhost:5500",    # VS Code Live Server
        "http://127.0.0.1:5500",
        "null",                     # file:// origin
    ]
}
HTTP_HEADERS = {}

# ── MySQL fix — use PyMySQL instead of MySQLdb ────────────────────────────────
# This fixes the "No module named 'MySQLdb'" error in your logs
# Run once:  pip install PyMySQL
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass   # if PyMySQL not installed yet, Superset will still run with SQLite

# ── Guest token permissions ────────────────────────────────────────────────────
# The public/guest role — guests will see dashboards with this role's permissions
GUEST_ROLE_NAME = "Public"

# ── Suppress rate limiter warning ─────────────────────────────────────────────
RATELIMIT_STORAGE_URI = "memory://"

# ── Secret key (change this to a random string in production!) ─────────────────
SECRET_KEY = "Rzl46Mq5M3kMZXyKOhzCo_aAZgvosJs8T29OZRigHKatJ6rce8ZEmyDq"

# ── SQLite database (default — already set up in your install) ─────────────────
# SQLALCHEMY_DATABASE_URI = "sqlite:///superset.db"
# If you want MySQL:
# pip install PyMySQL
# SQLALCHEMY_DATABASE_URI = "mysql+pymysql://user:password@localhost/superset"
# ── Disable CSRF for local development (fixes 401/400 embedding issues) ────────
WTF_CSRF_ENABLED = False
WTF_CSRF_CHECK_DEFAULT = False
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = False

# Fix embedded route audience mismatch
SUPERSET_WEBSERVER_PROTOCOL = "http"
SUPERSET_WEBSERVER_ADDRESS = "127.0.0.1"
SUPERSET_WEBSERVER_PORT = 8088

from flask_appbuilder.security.manager import AUTH_DB

# Enable embedded dashboards
FEATURE_FLAGS = {
    "EMBEDDED_SUPERSET": True,
    "ENABLE_TEMPLATE_PROCESSING": True,
}

GUEST_TOKEN_JWT_SECRET = "Rzl46Mq5M3kMZXyKOhzCo_aAZgvosJs8T29OZRigHKatJ6rce8ZEmyDq"   # any long random string
GUEST_TOKEN_JWT_ALGO = "HS256"
GUEST_TOKEN_JWT_EXP_SECONDS = 3600

# Allow your frontend origin
TALISMAN_ENABLED = False   # or configure CSP properly
CORS_OPTIONS = {
    "supports_credentials": True,
    "allow_headers": ["*"],
    "resources": {"*": {"origins": "http://localhost:5000"}},
}