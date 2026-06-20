"""
TAXFLOW - Python Flask Backend
File: app.py
Description: Complete REST API connecting to Oracle DB via PL/SQL
"""

from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import oracledb
import bcrypt
import os
import uuid
import logging
from functools import wraps
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

from bank_parser import BankStatementParser
from tally_export import generate_tally_xml

load_dotenv()

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app, supports_credentials=True)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
EXPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 15 * 1024 * 1024  # 15 MB
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── DATABASE CONNECTION ──────────────────────────────────────
def get_db():
    """Returns an Oracle DB connection."""
    return oracledb.connect(
        user=os.getenv('DB_USER', 'taxflow'),
        password=os.getenv('DB_PASSWORD', 'taxflow123'),
        dsn=os.getenv('DB_DSN', 'localhost:1521/XEPDB1')
    )


# ── AUTH DECORATOR ────────────────────────────────────────────
def require_auth(f):
    """Decorator: validates Bearer token before allowing access."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'status': 'ERROR', 'message': 'Authorization token required'}), 401

        token = auth_header.split(' ')[1]
        try:
            conn = get_db()
            cur  = conn.cursor()
            out_user_id   = cur.var(oracledb.NUMBER)
            out_email     = cur.var(oracledb.STRING)
            out_full_name = cur.var(oracledb.STRING)
            out_role      = cur.var(oracledb.STRING)
            out_status    = cur.var(oracledb.STRING)

            cur.callproc('PKG_AUTH.SP_GET_USER_BY_TOKEN', [
                token, out_user_id, out_email, out_full_name, out_role, out_status
            ])
            cur.close(); conn.close()

            if out_status.getvalue() != 'SUCCESS':
                return jsonify({'status': 'ERROR', 'message': 'Invalid or expired session'}), 401

            request.user_id   = int(out_user_id.getvalue())
            request.user_email     = out_email.getvalue()
            request.user_full_name = out_full_name.getvalue()
            request.user_role      = out_role.getvalue()

        except Exception as e:
            logger.error(f"Auth error: {e}")
            return jsonify({'status': 'ERROR', 'message': 'Authentication failed'}), 401

        return f(*args, **kwargs)
    return decorated


# ════════════════════════════════════════════════════════════
#  ROUTE: Serve Frontend
# ════════════════════════════════════════════════════════════
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


# ════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ════════════════════════════════════════════════════════════

@app.route('/api/auth/register', methods=['POST'])
def register():
    """
    POST /api/auth/register
    Body: { first_name, last_name, email, phone, password, product }
    """
    data = request.get_json()
    required = ['first_name', 'last_name', 'email', 'password', 'product']
    if not all(k in data for k in required):
        return jsonify({'status': 'ERROR', 'message': 'Missing required fields'}), 400

    # Hash password with bcrypt
    password_hash = bcrypt.hashpw(
        data['password'].encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

    try:
        conn = get_db()
        cur  = conn.cursor()

        out_user_id = cur.var(oracledb.NUMBER)
        out_status  = cur.var(oracledb.STRING)
        out_message = cur.var(oracledb.STRING)

        cur.callproc('PKG_AUTH.SP_REGISTER_USER', [
            data['first_name'],
            data['last_name'],
            data['email'],
            data.get('phone', ''),
            password_hash,
            data['product'],
            out_user_id,
            out_status,
            out_message
        ])
        cur.close(); conn.close()

        status  = out_status.getvalue()
        message = out_message.getvalue()
        user_id = int(out_user_id.getvalue()) if out_user_id.getvalue() else 0

        http_code = 201 if status == 'SUCCESS' else 400
        return jsonify({
            'status':  status,
            'message': message,
            'user_id': user_id
        }), http_code

    except Exception as e:
        logger.error(f"Register error: {e}")
        return jsonify({'status': 'ERROR', 'message': 'Server error. Please try again.'}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """
    POST /api/auth/login
    Body: { email, password }
    """
    data = request.get_json()
    if not data.get('email') or not data.get('password'):
        return jsonify({'status': 'ERROR', 'message': 'Email and password required'}), 400

    try:
        conn = get_db()
        cur  = conn.cursor()

        # First fetch the stored hash from DB for bcrypt comparison
        cur.execute("SELECT password_hash FROM USERS WHERE LOWER(email) = LOWER(:email)",
                    {'email': data['email']})
        row = cur.fetchone()

        if not row:
            cur.close(); conn.close()
            return jsonify({'status': 'ERROR', 'message': 'Invalid email or password'}), 401

        stored_hash = row[0]

        # Verify password with bcrypt
        if not bcrypt.checkpw(data['password'].encode('utf-8'), stored_hash.encode('utf-8')):
            cur.close(); conn.close()
            return jsonify({'status': 'ERROR', 'message': 'Invalid email or password'}), 401

        # Call PL/SQL login procedure (pass hash to match)
        out_token     = cur.var(oracledb.STRING)
        out_user_id   = cur.var(oracledb.NUMBER)
        out_full_name = cur.var(oracledb.STRING)
        out_status    = cur.var(oracledb.STRING)
        out_message   = cur.var(oracledb.STRING)

        cur.callproc('PKG_AUTH.SP_LOGIN_USER', [
            data['email'],
            stored_hash,           # pass stored hash so PL/SQL matches it
            request.remote_addr,
            request.headers.get('User-Agent', ''),
            out_token, out_user_id, out_full_name, out_status, out_message
        ])
        cur.close(); conn.close()

        status = out_status.getvalue()
        if status == 'SUCCESS':
            return jsonify({
                'status':    'SUCCESS',
                'message':   out_message.getvalue(),
                'token':     out_token.getvalue(),
                'user_id':   int(out_user_id.getvalue()),
                'full_name': out_full_name.getvalue()
            }), 200
        else:
            return jsonify({'status': 'ERROR', 'message': out_message.getvalue()}), 401

    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'status': 'ERROR', 'message': 'Server error'}), 500


@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    """POST /api/auth/logout  (requires Bearer token)"""
    token = request.headers.get('Authorization').split(' ')[1]
    try:
        conn = get_db()
        cur  = conn.cursor()
        out_status  = cur.var(oracledb.STRING)
        out_message = cur.var(oracledb.STRING)
        cur.callproc('PKG_AUTH.SP_LOGOUT_USER', [token, out_status, out_message])
        cur.close(); conn.close()
        return jsonify({'status': out_status.getvalue(), 'message': out_message.getvalue()}), 200
    except Exception as e:
        return jsonify({'status': 'ERROR', 'message': str(e)}), 500


@app.route('/api/auth/me', methods=['GET'])
@require_auth
def get_me():
    """GET /api/auth/me  — returns logged-in user info"""
    return jsonify({
        'status':    'SUCCESS',
        'user_id':   request.user_id,
        'email':     request.user_email,
        'full_name': request.user_full_name,
        'role':      request.user_role
    }), 200


# ════════════════════════════════════════════════════════════
#  LEADS ROUTES
# ════════════════════════════════════════════════════════════

@app.route('/api/leads/demo', methods=['POST'])
def request_demo():
    """
    POST /api/leads/demo
    Body: { full_name, email, phone, product_code }
    """
    data = request.get_json()
    required = ['full_name', 'email', 'phone', 'product_code']
    if not all(k in data for k in required):
        return jsonify({'status': 'ERROR', 'message': 'All fields are required'}), 400

    try:
        conn = get_db()
        cur  = conn.cursor()
        out_demo_id = cur.var(oracledb.NUMBER)
        out_status  = cur.var(oracledb.STRING)
        out_message = cur.var(oracledb.STRING)

        cur.callproc('PKG_LEADS.SP_SUBMIT_DEMO_REQUEST', [
            data['full_name'], data['email'], data['phone'],
            data['product_code'], out_demo_id, out_status, out_message
        ])
        cur.close(); conn.close()

        return jsonify({
            'status':  out_status.getvalue(),
            'message': out_message.getvalue(),
            'demo_id': int(out_demo_id.getvalue()) if out_demo_id.getvalue() else 0
        }), 200

    except Exception as e:
        logger.error(f"Demo request error: {e}")
        return jsonify({'status': 'ERROR', 'message': 'Failed to submit'}), 500


@app.route('/api/leads/contact', methods=['POST'])
def contact():
    """
    POST /api/leads/contact
    Body: { full_name, email, phone, subject, message }
    """
    data = request.get_json()
    if not data.get('full_name') or not data.get('email') or not data.get('message'):
        return jsonify({'status': 'ERROR', 'message': 'Name, email and message are required'}), 400

    try:
        conn = get_db()
        cur  = conn.cursor()
        out_msg_id  = cur.var(oracledb.NUMBER)
        out_status  = cur.var(oracledb.STRING)
        out_message = cur.var(oracledb.STRING)

        cur.callproc('PKG_LEADS.SP_SUBMIT_CONTACT', [
            data['full_name'], data['email'], data.get('phone', ''),
            data.get('subject', 'General Enquiry'), data['message'],
            out_msg_id, out_status, out_message
        ])
        cur.close(); conn.close()

        return jsonify({
            'status':  out_status.getvalue(),
            'message': out_message.getvalue()
        }), 200

    except Exception as e:
        logger.error(f"Contact error: {e}")
        return jsonify({'status': 'ERROR', 'message': 'Failed to send message'}), 500


# ════════════════════════════════════════════════════════════
#  DASHBOARD ROUTES  (Protected)
# ════════════════════════════════════════════════════════════

@app.route('/api/dashboard', methods=['GET'])
@require_auth
def get_dashboard():
    """GET /api/dashboard  — user's dashboard stats"""
    try:
        conn = get_db()
        cur  = conn.cursor()
        out_filings   = cur.var(oracledb.NUMBER)
        out_conv      = cur.var(oracledb.NUMBER)
        out_sub       = cur.var(oracledb.STRING)
        out_trial     = cur.var(oracledb.NUMBER)
        out_status    = cur.var(oracledb.STRING)

        cur.callproc('PKG_DASHBOARD.SP_GET_USER_DASHBOARD', [
            request.user_id, out_filings, out_conv, out_sub, out_trial, out_status
        ])
        cur.close(); conn.close()

        return jsonify({
            'status':         out_status.getvalue(),
            'total_filings':  int(out_filings.getvalue() or 0),
            'total_conversions': int(out_conv.getvalue() or 0),
            'active_subscription': out_sub.getvalue(),
            'trial_days_left': int(out_trial.getvalue() or 0),
            'user_name':      request.user_full_name
        }), 200

    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return jsonify({'status': 'ERROR', 'message': str(e)}), 500


@app.route('/api/dashboard/conversions', methods=['GET'])
@require_auth
def get_conversions():
    """GET /api/dashboard/conversions — list user's bank conversions"""
    try:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("""
            SELECT conversion_id, bank_name, file_name, total_entries,
                   status, TO_CHAR(created_at, 'DD-Mon-YYYY HH24:MI') as created_at
            FROM BANK_CONVERSIONS
            WHERE user_id = :uid
            ORDER BY created_at DESC
            FETCH FIRST 20 ROWS ONLY
        """, {'uid': request.user_id})

        rows = cur.fetchall()
        cur.close(); conn.close()

        conversions = [
            {
                'conversion_id': r[0], 'bank_name': r[1], 'file_name': r[2],
                'total_entries': r[3], 'status': r[4], 'created_at': r[5]
            } for r in rows
        ]
        return jsonify({'status': 'SUCCESS', 'conversions': conversions}), 200

    except Exception as e:
        return jsonify({'status': 'ERROR', 'message': str(e)}), 500


@app.route('/api/dashboard/filings', methods=['GET'])
@require_auth
def get_filings():
    """GET /api/dashboard/filings — list user's GST filings"""
    try:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("""
            SELECT filing_id, gstin, filing_month, platform,
                   total_sales, total_tax, status,
                   TO_CHAR(created_at, 'DD-Mon-YYYY') as created_at
            FROM GST_FILINGS
            WHERE user_id = :uid
            ORDER BY created_at DESC
            FETCH FIRST 20 ROWS ONLY
        """, {'uid': request.user_id})

        rows = cur.fetchall()
        cur.close(); conn.close()

        filings = [
            {
                'filing_id': r[0], 'gstin': r[1], 'filing_month': r[2],
                'platform': r[3], 'total_sales': float(r[4] or 0),
                'total_tax': float(r[5] or 0), 'status': r[6], 'created_at': r[7]
            } for r in rows
        ]
        return jsonify({'status': 'SUCCESS', 'filings': filings}), 200

    except Exception as e:
        return jsonify({'status': 'ERROR', 'message': str(e)}), 500
# ════════════════════════════════════════════════════════════
#  BANK STATEMENT CONVERTER ROUTES (Protected)
# ════════════════════════════════════════════════════════════

def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/api/bank/upload', methods=['POST'])
@require_auth
def upload_bank_statement():
    """
    POST /api/bank/upload  (multipart/form-data, field name: 'file')
    Parses the uploaded PDF, extracts transactions, generates Tally XML,
    saves a BANK_CONVERSIONS row, and returns a summary + download link.
    """
    if 'file' not in request.files:
        return jsonify({'status': 'ERROR', 'message': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'ERROR', 'message': 'No file selected'}), 400

    if not _allowed_file(file.filename):
        return jsonify({'status': 'ERROR', 'message': 'Only PDF files are supported'}), 400

    # Optional: exact Tally ledger name as it already exists in the user's
    # company (e.g. "PNB 5416"). If not provided, falls back to an
    # auto-generated name inside generate_tally_xml().
    bank_ledger_name = request.form.get('bank_ledger_name', '').strip() or None
    suspense_ledger_name = request.form.get('suspense_ledger_name', '').strip() or None
    logger.info(f"[BANK UPLOAD] received bank_ledger_name = {bank_ledger_name!r}, "
                f"suspense_ledger_name = {suspense_ledger_name!r}")

    # Save uploaded file with a unique name (avoid collisions between users)
    original_name = secure_filename(file.filename)
    unique_id = uuid.uuid4().hex[:12]
    saved_name = f"{request.user_id}_{unique_id}_{original_name}"
    saved_path = os.path.join(UPLOAD_DIR, saved_name)
    file.save(saved_path)

    conn = None
    try:
        # ── 1. Parse the PDF ────────────────────────────────────
        parser = BankStatementParser(saved_path)
        result = parser.parse()

        if result['total_count'] == 0:
            return jsonify({
                'status': 'ERROR',
                'message': 'No transactions could be detected in this PDF. '
                           'Try a different statement or check the file is not scanned/image-based.'
            }), 422

        # ── 2. Generate Tally XML ───────────────────────────────
        xml_content = generate_tally_xml(
            bank_name=result['bank_name'],
            account_number=result['account_number'],
            transactions=result['transactions'],
            bank_ledger_name=bank_ledger_name,
            suspense_ledger_name=suspense_ledger_name
        )
        xml_filename = f"{unique_id}_tally_export.xml"
        xml_path = os.path.join(EXPORT_DIR, xml_filename)
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)

        # ── 3. Save conversion record in Oracle via PL/SQL ──────
        conn = get_db()
        cur  = conn.cursor()
        out_conv_id = cur.var(oracledb.NUMBER)
        out_status  = cur.var(oracledb.STRING)
        out_message = cur.var(oracledb.STRING)

        cur.callproc('PKG_DASHBOARD.SP_SAVE_BANK_CONVERSION', [
            request.user_id,
            result['bank_name'],
            original_name,
            result['total_count'],
            out_conv_id, out_status, out_message
        ])

        conv_id = int(out_conv_id.getvalue()) if out_conv_id.getvalue() else 0

        # Store the output_url against the conversion row
        cur.execute("""
            UPDATE BANK_CONVERSIONS SET output_url = :url WHERE conversion_id = :cid
        """, {'url': f"/api/bank/download/{xml_filename}", 'cid': conv_id})
        conn.commit()
        cur.close(); conn.close()

        effective_ledger_name = bank_ledger_name or f"{result['bank_name']} Bank Account"
        effective_suspense_name = suspense_ledger_name or 'Suspense Account'

        return jsonify({
            'status': 'SUCCESS',
            'message': f"Converted {result['total_count']} transactions successfully!",
            'conversion_id': conv_id,
            'bank_name': result['bank_name'],
            'account_number': result['account_number'],
            'bank_ledger_used': effective_ledger_name,
            'suspense_ledger_used': effective_suspense_name,
            'total_transactions': result['total_count'],
            'total_debit': float(result['total_debit']),
            'total_credit': float(result['total_credit']),
            'preview': [
                {
                    'date': t['date'], 'narration': t['narration'],
                    'debit': float(t['debit']), 'credit': float(t['credit']),
                    'balance': float(t['balance'])
                } for t in result['transactions'][:10]  # preview first 10 rows
            ],
            'download_url': f"/api/bank/download/{xml_filename}"
        }), 200

    except Exception as e:
        if conn:
            try: conn.close()
            except Exception: pass
        logger.error(f"Bank upload error: {e}")
        return jsonify({'status': 'ERROR', 'message': f'Failed to process PDF: {str(e)}'}), 500

    finally:
        # Clean up uploaded PDF (we don't need to keep the original)
        if os.path.exists(saved_path):
            try: os.remove(saved_path)
            except Exception: pass


@app.route('/api/bank/download/<filename>', methods=['GET'])
def download_tally_xml(filename):
    """GET /api/bank/download/<filename> — serves the generated Tally XML file"""
    safe_name = secure_filename(filename)
    file_path = os.path.join(EXPORT_DIR, safe_name)
    if not os.path.exists(file_path):
        return jsonify({'status': 'ERROR', 'message': 'File not found or expired'}), 404
    return send_file(file_path, as_attachment=True, download_name='TaxFlow_Tally_Export.xml',
                      mimetype='application/xml')




@app.route('/api/products', methods=['GET'])
def get_products():
    """GET /api/products — list all active products"""
    try:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("""
            SELECT product_id, product_code, product_name,
                   description, price_monthly, price_yearly
            FROM PRODUCTS WHERE is_active = 'Y'
            ORDER BY product_id
        """)
        rows = cur.fetchall()
        cur.close(); conn.close()

        products = [
            {
                'product_id': r[0], 'code': r[1], 'name': r[2],
                'description': r[3],
                'price_monthly': float(r[4] or 0),
                'price_yearly':  float(r[5] or 0)
            } for r in rows
        ]
        return jsonify({'status': 'SUCCESS', 'products': products}), 200

    except Exception as e:
        return jsonify({'status': 'ERROR', 'message': str(e)}), 500


# ════════════════════════════════════════════════════════════
#  ERROR HANDLERS
# ════════════════════════════════════════════════════════════

@app.errorhandler(404)
def not_found(e):
    return jsonify({'status': 'ERROR', 'message': 'Route not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'status': 'ERROR', 'message': 'Internal server error'}), 500

if __name__ == "__main__":
    app.run(debug=True)
