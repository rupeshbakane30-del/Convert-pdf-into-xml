"""
TAXFLOW - Bank Statement PDF Parser
File: bank_parser.py
Description: Extracts transactions from ANY bank's PDF statement.
             Auto-detects bank name, column layout (date/narration/debit/credit/balance),
             and normalizes everything into a common transaction format.
"""

import re
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

import pdfplumber

logger = logging.getLogger(__name__)


# ── KNOWN BANK NAME PATTERNS (for auto-detect) ──────────────────────
BANK_PATTERNS = {
    'HDFC BANK':        r'HDFC\s*BANK',
    'STATE BANK OF INDIA': r'STATE\s*BANK\s*OF\s*INDIA|\bSBI\b',
    'ICICI BANK':       r'ICICI\s*BANK',
    'AXIS BANK':        r'AXIS\s*BANK',
    'KOTAK MAHINDRA BANK': r'KOTAK\s*MAHINDRA',
    'BANK OF BARODA':   r'BANK\s*OF\s*BARODA',
    'PUNJAB NATIONAL BANK': r'PUNJAB\s*NATIONAL\s*BANK|\bPNB\b',
    'CANARA BANK':      r'CANARA\s*BANK',
    'IDFC FIRST BANK':  r'IDFC\s*FIRST',
    'YES BANK':         r'YES\s*BANK',
    'INDUSIND BANK':    r'INDUSIND\s*BANK',
    'RBL BANK':         r'RBL\s*BANK',
}

# ── COLUMN HEADER SYNONYMS (used to map arbitrary bank headers → our schema) ──
COLUMN_SYNONYMS = {
    'date':        ['date', 'txn date', 'transaction date', 'value date', 'posting date'],
    'narration':   ['narration', 'description', 'particulars', 'transaction details', 'remarks'],
    'debit':       ['debit', 'withdrawal', 'withdrawal amt', 'debit amount', 'dr'],
    'credit':      ['credit', 'deposit', 'deposit amt', 'credit amount', 'cr'],
    'balance':     ['balance', 'closing balance', 'running balance', 'available balance'],
    'ref_no':      ['ref no', 'cheque no', 'chq/ref no', 'reference', 'cheque/ref number'],
}

DATE_PATTERNS = [
    r'\d{2}[-/]\d{2}[-/]\d{4}',     # 31-12-2025 or 31/12/2025
    r'\d{2}[-/][A-Za-z]{3}[-/]\d{4}',  # 31-Dec-2025
    r'\d{2}[-/]\d{2}[-/]\d{2}',     # 31-12-25
]
DATE_RE = re.compile('|'.join(DATE_PATTERNS))

AMOUNT_RE = re.compile(r'^-?[\d,]+\.?\d{0,2}$')


class BankStatementParser:
    """Parses any bank statement PDF and returns normalized transactions."""

    def __init__(self, filepath):
        self.filepath = filepath
        self.bank_name = 'Unknown Bank'
        self.account_number = None
        self.transactions = []
        self._last_col_map = None  # carries column layout across pages without repeated headers

    # ── MAIN ENTRY POINT ──────────────────────────────────────────
    def parse(self):
        with pdfplumber.open(self.filepath) as pdf:
            full_text = ''
            for page in pdf.pages:
                text = page.extract_text() or ''
                full_text += text + '\n'

            self._detect_bank(full_text)
            self._detect_account_number(full_text)

            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    self._process_table(table)

            # Fallback: if no tables found (image-based or odd layout), try line-based regex parsing
            if not self.transactions:
                self._parse_from_text(full_text)

        self._reconcile_balances()
        return {
            'bank_name': self.bank_name,
            'account_number': self.account_number,
            'transactions': self.transactions,
            'total_count': len(self.transactions),
            'total_debit': sum(t['debit'] for t in self.transactions),
            'total_credit': sum(t['credit'] for t in self.transactions),
        }

    # ── BANK NAME DETECTION ───────────────────────────────────────
    def _detect_bank(self, text):
        upper_text = text.upper()
        for bank_name, pattern in BANK_PATTERNS.items():
            if re.search(pattern, upper_text):
                self.bank_name = bank_name.title()
                return
        # Fallback: grab first line that looks like a bank name
        first_lines = text.split('\n')[:5]
        for line in first_lines:
            if 'bank' in line.lower():
                self.bank_name = line.strip()[:100]
                return

    def _detect_account_number(self, text):
        match = re.search(r'(?:A/?C\s*(?:No)?\.?\s*[:\-]?\s*)(\d{6,20})', text, re.IGNORECASE)
        if match:
            self.account_number = match.group(1)

    # ── TABLE-BASED EXTRACTION (most reliable) ──────────────────────
    def _process_table(self, table):
        if not table or len(table) < 1:
            return

        header_row_idx = self._find_header_row(table)

        if header_row_idx is not None:
            col_map = self._map_columns(table[header_row_idx])
            if 'date' in col_map:
                # Good: this table has its own real header row.
                # Remember this mapping in case later pages reuse the same
                # layout but don't repeat the header row.
                self._last_col_map = col_map
                data_rows = table[header_row_idx + 1:]
                self._extract_rows(data_rows, col_map)
                return

        # No usable header found in THIS table (typical for page 2+ of a
        # statement, where the header only appears once on page 1).
        # Reuse the column mapping detected earlier, and treat every row
        # as data (no header to skip).
        if self._last_col_map:
            self._extract_rows(table, self._last_col_map)

    def _extract_rows(self, rows, col_map):
        for row in rows:
            txn = self._row_to_transaction(row, col_map)
            if txn:
                self.transactions.append(txn)

    def _find_header_row(self, table):
        for idx, row in enumerate(table[:3]):
            row_text = ' '.join(str(c).lower() for c in row if c)
            if 'date' in row_text and ('narration' in row_text or 'description' in row_text
                                        or 'particulars' in row_text):
                return idx
        return None  # no header row found in this table — caller falls back to last known mapping

    def _map_columns(self, header_row):
        col_map = {}
        for idx, cell in enumerate(header_row):
            if not cell:
                continue
            cell_clean = str(cell).strip().lower().replace('\n', ' ')
            for field, synonyms in COLUMN_SYNONYMS.items():
                if any(syn in cell_clean for syn in synonyms):
                    if field not in col_map:  # first match wins
                        col_map[field] = idx
        return col_map

    def _row_to_transaction(self, row, col_map):
        try:
            date_raw = self._safe_cell(row, col_map.get('date'))
            if not date_raw or not DATE_RE.search(date_raw):
                return None

            date_parsed = self._parse_date(date_raw)
            if not date_parsed:
                return None

            narration = self._safe_cell(row, col_map.get('narration')) or 'Transaction'
            debit  = self._parse_amount(self._safe_cell(row, col_map.get('debit')))
            credit = self._parse_amount(self._safe_cell(row, col_map.get('credit')))
            balance = self._parse_amount(self._safe_cell(row, col_map.get('balance')))
            ref_no = self._safe_cell(row, col_map.get('ref_no')) or ''

            if debit == 0 and credit == 0:
                return None  # skip non-transaction rows

            return {
                'date': date_parsed,
                'narration': narration.replace('\n', ' ').strip()[:240],
                'debit': debit,
                'credit': credit,
                'balance': balance,
                'ref_no': ref_no.strip()[:50],
            }
        except Exception as e:
            logger.debug(f"Row skip: {e}")
            return None

    @staticmethod
    def _safe_cell(row, idx):
        if idx is None or idx >= len(row):
            return None
        val = row[idx]
        return str(val).strip() if val else None

    @staticmethod
    def _parse_date(raw):
        raw = raw.strip()
        formats = ['%d-%m-%Y', '%d/%m/%Y', '%d-%m-%y', '%d/%m/%y', '%d-%b-%Y', '%d/%b/%Y']
        for fmt in formats:
            try:
                return datetime.strptime(raw, fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
        match = DATE_RE.search(raw)
        if match:
            for fmt in formats:
                try:
                    return datetime.strptime(match.group(), fmt).strftime('%Y-%m-%d')
                except ValueError:
                    continue
        return None

    @staticmethod
    def _parse_amount(raw):
        if not raw:
            return Decimal('0')
        cleaned = raw.replace(',', '').replace('₹', '').replace('Cr', '').replace('Dr', '').strip()
        if not cleaned or cleaned in ('-', '—'):
            return Decimal('0')
        try:
            return abs(Decimal(cleaned))
        except InvalidOperation:
            return Decimal('0')

    # ── FALLBACK: line-by-line regex parsing for non-table PDFs ─────
    def _parse_from_text(self, full_text):
        lines = full_text.split('\n')
        for line in lines:
            date_match = DATE_RE.search(line)
            if not date_match:
                continue
            date_parsed = self._parse_date(date_match.group())
            if not date_parsed:
                continue

            amounts = re.findall(r'[\d,]+\.\d{2}', line)
            if len(amounts) < 1:
                continue

            narration_part = line[date_match.end():].strip()
            narration = re.sub(r'[\d,]+\.\d{2}', '', narration_part).strip()[:240]

            # Heuristic: last number = balance, second-last = txn amount
            txn_amount = self._parse_amount(amounts[-2]) if len(amounts) >= 2 else self._parse_amount(amounts[0])
            balance    = self._parse_amount(amounts[-1]) if len(amounts) >= 2 else Decimal('0')

            is_credit = bool(re.search(r'\bCr\b|credit|deposit', line, re.IGNORECASE))

            self.transactions.append({
                'date': date_parsed,
                'narration': narration or 'Transaction',
                'debit':  Decimal('0') if is_credit else txn_amount,
                'credit': txn_amount if is_credit else Decimal('0'),
                'balance': balance,
                'ref_no': '',
            })

    # ── RECONCILE: infer debit/credit from balance deltas when missing ──
    def _reconcile_balances(self):
        """If a row has a balance but debit/credit both came out as 0,
        infer the direction by comparing with the previous balance."""
        prev_balance = None
        for txn in self.transactions:
            if txn['debit'] == 0 and txn['credit'] == 0 and prev_balance is not None and txn['balance']:
                delta = txn['balance'] - prev_balance
                if delta > 0:
                    txn['credit'] = delta
                elif delta < 0:
                    txn['debit'] = abs(delta)
            if txn['balance']:
                prev_balance = txn['balance']
