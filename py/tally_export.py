"""
TAXFLOW - Tally XML Generator
File: tally_export.py
Description: Converts normalized bank transactions into Tally-compatible
             XML (Voucher import format) with proper Dr/Cr ledger entries.

Tally XML structure reference: <ENVELOPE><BODY><IMPORTDATA><REQUESTDATA>
Each transaction becomes one <TALLYMESSAGE> containing a <VOUCHER> with
two <ALLLEDGERENTRIES.LIST> blocks (one Dr, one Cr) — standard double-entry.
"""

from xml.sax.saxutils import escape
from datetime import datetime


def _tally_date(iso_date):
    """Converts YYYY-MM-DD to Tally's YYYYMMDD format."""
    return datetime.strptime(iso_date, '%Y-%m-%d').strftime('%Y%m%d')


def _guess_ledger_name(narration, suspense_ledger_name='Suspense Account'):
    """
    All transactions are routed to a single suspense-type ledger.
    This is intentional: auto-classification can misclassify real entries,
    so every imported voucher is parked in Suspense for the accountant to
    manually reassign to the correct ledger inside Tally after review.

    suspense_ledger_name: the EXACT name of this ledger as it already
        exists in the user's Tally company (e.g. "Suspense", not
        "Suspense Account" — company setups vary).
    """
    return suspense_ledger_name


def generate_tally_xml(bank_name, account_number, transactions,
                        company_name='TaxFlow Demo Company', bank_ledger_name=None,
                        suspense_ledger_name=None):
    """
    Builds the full Tally XML document.

    transactions: list of dicts with keys
        date (YYYY-MM-DD), narration, debit (Decimal), credit (Decimal),
        balance (Decimal), ref_no

    bank_ledger_name: the EXACT ledger name as it already exists in the
        user's Tally company (e.g. "PNB 5416"). If not provided, falls
        back to an auto-generated name ("{bank_name} Bank Account") —
        but that auto-generated name will almost never match a real
        company's actual ledger, so callers should pass this whenever
        the real ledger name is known.

    suspense_ledger_name: the EXACT name of the counter-party ledger as
        it exists in the user's Tally company (e.g. "Suspense", not
        "Suspense Account"). Defaults to "Suspense Account" if not given.
    """
    bank_ledger = escape(bank_ledger_name) if bank_ledger_name else escape(f"{bank_name} Bank Account")
    suspense_name = suspense_ledger_name.strip() if suspense_ledger_name else 'Suspense Account'

    vouchers_xml = []
    for idx, txn in enumerate(transactions, start=1):
        tally_date = _tally_date(txn['date'])
        narration  = escape(txn['narration'] or 'Bank Transaction')
        ref_no     = escape(txn.get('ref_no') or f"TXN{idx:05d}")
        counter_ledger = escape(_guess_ledger_name(txn['narration'], suspense_name))

        debit  = float(txn['debit'])
        credit = float(txn['credit'])

        if credit > 0:
            # Money IN: Bank A/c Dr, Counter-party Cr
            voucher_type = 'Receipt'
            bank_amount, bank_is_deemed_positive = credit, 'Yes'
            counter_amount, counter_is_deemed_positive = credit, 'No'
        else:
            # Money OUT: Counter-party Dr, Bank A/c Cr
            voucher_type = 'Payment'
            bank_amount, bank_is_deemed_positive = debit, 'No'
            counter_amount, counter_is_deemed_positive = debit, 'Yes'

        voucher = f"""
        <TALLYMESSAGE xmlns:UDF="TallyUDF">
          <VOUCHER VCHTYPE="{voucher_type}" ACTION="Create" OBJVIEW="Accounting Voucher View">
            <DATE>{tally_date}</DATE>
            <EFFECTIVEDATE>{tally_date}</EFFECTIVEDATE>
            <VOUCHERTYPENAME>{voucher_type}</VOUCHERTYPENAME>
            <VOUCHERNUMBER>{ref_no}</VOUCHERNUMBER>
            <REFERENCE>{ref_no}</REFERENCE>
            <NARRATION>{narration}</NARRATION>
            <PARTYLEDGERNAME>{counter_ledger}</PARTYLEDGERNAME>
            <ISINVOICE>No</ISINVOICE>
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>{bank_ledger}</LEDGERNAME>
              <ISDEEMEDPOSITIVE>{bank_is_deemed_positive}</ISDEEMEDPOSITIVE>
              <AMOUNT>{bank_amount if bank_is_deemed_positive == 'No' else -bank_amount:.2f}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>{counter_ledger}</LEDGERNAME>
              <ISDEEMEDPOSITIVE>{counter_is_deemed_positive}</ISDEEMEDPOSITIVE>
              <AMOUNT>{counter_amount if counter_is_deemed_positive == 'No' else -counter_amount:.2f}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
          </VOUCHER>
        </TALLYMESSAGE>"""
        vouchers_xml.append(voucher)

    # Ledger master creation block — INTENTIONALLY DISABLED.
    #
    # Earlier versions tried to auto-create the bank ledger (and originally
    # "Suspense Account" too) via ACTION="Create". In practice, the target
    # Tally company almost always already has its own ledgers — sometimes
    # under a different parent group than what we'd guess here. When our
    # XML's <PARENT> doesn't exactly match what's already stored in Tally,
    # Tally treats it as a conflicting/ambiguous definition and silently
    # drops the master, which cascades into "Master name is missing" /
    # "Referenced master is missing" on every voucher that references it.
    #
    # Fix: don't create ANY ledger masters from this export. Vouchers only
    # reference ledger names by string — Tally resolves those against
    # whatever already exists in the company (bank ledger, Suspense
    # Account, etc.). The accountant is expected to have both ledgers
    # already set up before importing, which matches real-world workflow.
    ledger_masters = ''

    xml_doc = f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Import Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <IMPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>All Masters</REPORTNAME>
        <STATICVARIABLES>
          <SVCURRENTCOMPANY>{escape(company_name)}</SVCURRENTCOMPANY>
        </STATICVARIABLES>
      </REQUESTDESC>
      <REQUESTDATA>
        {ledger_masters}
        {''.join(vouchers_xml)}
      </REQUESTDATA>
    </IMPORTDATA>
  </BODY>
</ENVELOPE>"""

    return xml_doc
