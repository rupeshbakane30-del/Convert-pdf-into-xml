-- ============================================================
-- TAXFLOW - ORACLE DATABASE SCHEMA
-- File: 01_schema.sql
-- Description: All tables, sequences, constraints
-- ============================================================

-- ── DROP EXISTING (for clean reinstall) ────────────────────
BEGIN
  FOR t IN (SELECT table_name FROM user_tables 
            WHERE table_name IN ('USERS','DEMO_REQUESTS','CONTACT_MESSAGES',
                                 'SUBSCRIPTIONS','AUDIT_LOGS','USER_SESSIONS',
                                 'PRODUCTS','GST_FILINGS','BANK_CONVERSIONS')) LOOP
    EXECUTE IMMEDIATE 'DROP TABLE ' || t.table_name || ' CASCADE CONSTRAINTS';
  END LOOP;
END;
/

BEGIN
  FOR s IN (SELECT sequence_name FROM user_sequences
            WHERE sequence_name LIKE 'SEQ_%') LOOP
    EXECUTE IMMEDIATE 'DROP SEQUENCE ' || s.sequence_name;
  END LOOP;
END;
/

-- ── SEQUENCES ──────────────────────────────────────────────
CREATE SEQUENCE SEQ_USERS          START WITH 1 INCREMENT BY 1 NOCACHE NOCYCLE;
CREATE SEQUENCE SEQ_DEMO_REQUESTS  START WITH 1 INCREMENT BY 1 NOCACHE NOCYCLE;
CREATE SEQUENCE SEQ_CONTACT        START WITH 1 INCREMENT BY 1 NOCACHE NOCYCLE;
CREATE SEQUENCE SEQ_SUBSCRIPTIONS  START WITH 1 INCREMENT BY 1 NOCACHE NOCYCLE;
CREATE SEQUENCE SEQ_AUDIT          START WITH 1 INCREMENT BY 1 NOCACHE NOCYCLE;
CREATE SEQUENCE SEQ_SESSIONS       START WITH 1 INCREMENT BY 1 NOCACHE NOCYCLE;
CREATE SEQUENCE SEQ_GST_FILINGS    START WITH 1 INCREMENT BY 1 NOCACHE NOCYCLE;
CREATE SEQUENCE SEQ_BANK_CONV      START WITH 1 INCREMENT BY 1 NOCACHE NOCYCLE;

-- ── PRODUCTS TABLE ─────────────────────────────────────────
CREATE TABLE PRODUCTS (
  product_id    NUMBER PRIMARY KEY,
  product_code  VARCHAR2(20)  NOT NULL UNIQUE,
  product_name  VARCHAR2(100) NOT NULL,
  description   VARCHAR2(500),
  price_monthly NUMBER(10,2),
  price_yearly  NUMBER(10,2),
  is_active     CHAR(1) DEFAULT 'Y' CHECK (is_active IN ('Y','N')),
  created_at    TIMESTAMP DEFAULT SYSTIMESTAMP
);

INSERT INTO PRODUCTS VALUES (1, 'BSC', 'Bank Statement Converter', 'Convert PDF bank statements to Tally XML', 999, 9999, 'Y', SYSTIMESTAMP);
INSERT INTO PRODUCTS VALUES (2, 'EGST', 'E-Commerce GSTR-1', 'GSTR-1 filing for e-commerce sellers', 1499, 14999, 'Y', SYSTIMESTAMP);
INSERT INTO PRODUCTS VALUES (3, 'BOTH', 'Both Products', 'BSC + GSTR-1 combo plan', 1999, 19999, 'Y', SYSTIMESTAMP);
COMMIT;

-- ── USERS TABLE ────────────────────────────────────────────
CREATE TABLE USERS (
  user_id        NUMBER DEFAULT SEQ_USERS.NEXTVAL PRIMARY KEY,
  first_name     VARCHAR2(50)  NOT NULL,
  last_name      VARCHAR2(50)  NOT NULL,
  email          VARCHAR2(150) NOT NULL UNIQUE,
  phone          VARCHAR2(15),
  password_hash  VARCHAR2(256) NOT NULL,
  user_role      VARCHAR2(20)  DEFAULT 'USER' CHECK (user_role IN ('USER','ADMIN','CA')),
  is_active      CHAR(1)       DEFAULT 'Y' CHECK (is_active IN ('Y','N')),
  is_verified    CHAR(1)       DEFAULT 'N' CHECK (is_verified IN ('Y','N')),
  trial_end_date DATE,
  created_at     TIMESTAMP DEFAULT SYSTIMESTAMP,
  updated_at     TIMESTAMP DEFAULT SYSTIMESTAMP,
  last_login     TIMESTAMP
);

CREATE INDEX IDX_USERS_EMAIL ON USERS(email);

-- ── USER SESSIONS TABLE ────────────────────────────────────
CREATE TABLE USER_SESSIONS (
  session_id   NUMBER DEFAULT SEQ_SESSIONS.NEXTVAL PRIMARY KEY,
  user_id      NUMBER NOT NULL REFERENCES USERS(user_id) ON DELETE CASCADE,
  token        VARCHAR2(256) NOT NULL UNIQUE,
  ip_address   VARCHAR2(45),
  user_agent   VARCHAR2(300),
  created_at   TIMESTAMP DEFAULT SYSTIMESTAMP,
  expires_at   TIMESTAMP NOT NULL,
  is_active    CHAR(1) DEFAULT 'Y' CHECK (is_active IN ('Y','N'))
);

CREATE INDEX IDX_SESSIONS_TOKEN   ON USER_SESSIONS(token);
CREATE INDEX IDX_SESSIONS_USER_ID ON USER_SESSIONS(user_id);

-- ── SUBSCRIPTIONS TABLE ────────────────────────────────────
CREATE TABLE SUBSCRIPTIONS (
  sub_id       NUMBER DEFAULT SEQ_SUBSCRIPTIONS.NEXTVAL PRIMARY KEY,
  user_id      NUMBER NOT NULL REFERENCES USERS(user_id) ON DELETE CASCADE,
  product_id   NUMBER NOT NULL REFERENCES PRODUCTS(product_id),
  plan_type    VARCHAR2(10) DEFAULT 'TRIAL' CHECK (plan_type IN ('TRIAL','MONTHLY','YEARLY')),
  status       VARCHAR2(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','EXPIRED','CANCELLED')),
  start_date   DATE DEFAULT SYSDATE,
  end_date     DATE,
  amount_paid  NUMBER(10,2) DEFAULT 0,
  created_at   TIMESTAMP DEFAULT SYSTIMESTAMP
);

-- ── DEMO REQUESTS TABLE ────────────────────────────────────
CREATE TABLE DEMO_REQUESTS (
  demo_id      NUMBER DEFAULT SEQ_DEMO_REQUESTS.NEXTVAL PRIMARY KEY,
  full_name    VARCHAR2(100) NOT NULL,
  email        VARCHAR2(150) NOT NULL,
  phone        VARCHAR2(15)  NOT NULL,
  product_code VARCHAR2(20)  NOT NULL,
  status       VARCHAR2(20)  DEFAULT 'PENDING' CHECK (status IN ('PENDING','SCHEDULED','COMPLETED','CANCELLED')),
  demo_date    DATE,
  notes        VARCHAR2(500),
  created_at   TIMESTAMP DEFAULT SYSTIMESTAMP
);

-- ── CONTACT MESSAGES TABLE ─────────────────────────────────
CREATE TABLE CONTACT_MESSAGES (
  message_id   NUMBER DEFAULT SEQ_CONTACT.NEXTVAL PRIMARY KEY,
  full_name    VARCHAR2(100) NOT NULL,
  email        VARCHAR2(150) NOT NULL,
  phone        VARCHAR2(15),
  subject      VARCHAR2(200),
  message      VARCHAR2(2000) NOT NULL,
  status       VARCHAR2(20) DEFAULT 'UNREAD' CHECK (status IN ('UNREAD','READ','REPLIED')),
  created_at   TIMESTAMP DEFAULT SYSTIMESTAMP
);

-- ── GST FILINGS TABLE ──────────────────────────────────────
CREATE TABLE GST_FILINGS (
  filing_id    NUMBER DEFAULT SEQ_GST_FILINGS.NEXTVAL PRIMARY KEY,
  user_id      NUMBER NOT NULL REFERENCES USERS(user_id),
  gstin        VARCHAR2(15),
  filing_month VARCHAR2(7),   -- Format: YYYY-MM
  platform     VARCHAR2(50),  -- Amazon, Flipkart, etc.
  total_sales  NUMBER(15,2),
  total_tax    NUMBER(15,2),
  status       VARCHAR2(20) DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','SUBMITTED','FILED')),
  file_url     VARCHAR2(500),
  created_at   TIMESTAMP DEFAULT SYSTIMESTAMP
);

-- ── BANK CONVERSIONS TABLE ─────────────────────────────────
CREATE TABLE BANK_CONVERSIONS (
  conversion_id  NUMBER DEFAULT SEQ_BANK_CONV.NEXTVAL PRIMARY KEY,
  user_id        NUMBER NOT NULL REFERENCES USERS(user_id),
  bank_name      VARCHAR2(100),
  file_name      VARCHAR2(200),
  total_entries  NUMBER DEFAULT 0,
  status         VARCHAR2(20) DEFAULT 'PROCESSING' CHECK (status IN ('PROCESSING','COMPLETED','FAILED')),
  output_url     VARCHAR2(500),
  created_at     TIMESTAMP DEFAULT SYSTIMESTAMP
);

-- ── AUDIT LOGS TABLE ───────────────────────────────────────
CREATE TABLE AUDIT_LOGS (
  log_id       NUMBER DEFAULT SEQ_AUDIT.NEXTVAL PRIMARY KEY,
  user_id      NUMBER,
  action       VARCHAR2(100) NOT NULL,
  table_name   VARCHAR2(50),
  record_id    NUMBER,
  old_value    VARCHAR2(1000),
  new_value    VARCHAR2(1000),
  ip_address   VARCHAR2(45),
  created_at   TIMESTAMP DEFAULT SYSTIMESTAMP
);

COMMIT;
PROMPT '✅ Schema created successfully!';
