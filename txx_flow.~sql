PRODUCTS
USERS
USER_SESSIONS
SUBSCRIPTIONS
DEMO_REQUESTS
CONTACT_MESSAGES
GST_FILINGS
BANK_CONVERSIONS
AUDIT_LOGS



ALTER SESSION SET CONTAINER = XEPDB1;



SELECT * FROM CUSTOMER



CREATE USER taxflow IDENTIFIED BY taxflow123;
GRANT CONNECT, RESOURCE TO taxflow;
GRANT UNLIMITED TABLESPACE TO taxflow;
GRANT CREATE VIEW TO taxflow; 


ALTER USER taxflow IDENTIFIED BY Tax1234 ACCOUNT UNLOCK;


Username  : taxflow
Password  : Tax1234
Database  : localhost:1521/XEPDB1
Connect as: NORMAL

---------------------------------------------------------------------------------------------
---------------------------------------------------------------------------------------------

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

--------------------------------------------------------------------------------------------------------------------------------
--------------------------------------------------------------------------------------------------------------------------------

-- ============================================================
-- TAXFLOW - PL/SQL PACKAGES
-- File: 02_packages.sql
-- Description: All stored procedures, functions, packages
-- ============================================================


-- ╔══════════════════════════════════════════════════════════╗
-- ║         PACKAGE: PKG_AUTH  (Authentication)             ║
-- ╚══════════════════════════════════════════════════════════╝
CREATE OR REPLACE PACKAGE PKG_AUTH AS

  -- Register a new user (returns user_id or error code)
  PROCEDURE SP_REGISTER_USER (
    p_first_name  IN  VARCHAR2,
    p_last_name   IN  VARCHAR2,
    p_email       IN  VARCHAR2,
    p_phone       IN  VARCHAR2,
    p_password    IN  VARCHAR2,   -- already hashed by Python
    p_product     IN  VARCHAR2,
    p_user_id     OUT NUMBER,
    p_status      OUT VARCHAR2,
    p_message     OUT VARCHAR2
  );

  -- Login user (returns session token)
  PROCEDURE SP_LOGIN_USER (
    p_email       IN  VARCHAR2,
    p_password    IN  VARCHAR2,
    p_ip_address  IN  VARCHAR2,
    p_user_agent  IN  VARCHAR2,
    p_token       OUT VARCHAR2,
    p_user_id     OUT NUMBER,
    p_full_name   OUT VARCHAR2,
    p_status      OUT VARCHAR2,
    p_message     OUT VARCHAR2
  );

  -- Logout user (invalidate session)
  PROCEDURE SP_LOGOUT_USER (
    p_token   IN  VARCHAR2,
    p_status  OUT VARCHAR2,
    p_message OUT VARCHAR2
  );

  -- Validate session token
  FUNCTION FN_VALIDATE_SESSION (p_token IN VARCHAR2) RETURN NUMBER;

  -- Get user details by token
  PROCEDURE SP_GET_USER_BY_TOKEN (
    p_token     IN  VARCHAR2,
    p_user_id   OUT NUMBER,
    p_email     OUT VARCHAR2,
    p_full_name OUT VARCHAR2,
    p_role      OUT VARCHAR2,
    p_status    OUT VARCHAR2
  );

END PKG_AUTH;


CREATE OR REPLACE PACKAGE BODY PKG_AUTH AS

  -- ── REGISTER USER ────────────────────────────────────────
  PROCEDURE SP_REGISTER_USER (
    p_first_name  IN  VARCHAR2,
    p_last_name   IN  VARCHAR2,
    p_email       IN  VARCHAR2,
    p_phone       IN  VARCHAR2,
    p_password    IN  VARCHAR2,
    p_product     IN  VARCHAR2,
    p_user_id     OUT NUMBER,
    p_status      OUT VARCHAR2,
    p_message     OUT VARCHAR2
  ) AS
    v_count     NUMBER;
    v_user_id   NUMBER;
    v_prod_id   NUMBER;
  BEGIN
    -- Check duplicate email
    SELECT COUNT(*) INTO v_count FROM USERS WHERE LOWER(email) = LOWER(p_email);
    IF v_count > 0 THEN
      p_status  := 'ERROR';
      p_message := 'Email already registered. Please sign in.';
      p_user_id := 0;
      RETURN;
    END IF;

    -- Insert new user
    INSERT INTO USERS (first_name, last_name, email, phone, password_hash, trial_end_date)
    VALUES (p_first_name, p_last_name, LOWER(p_email), p_phone, p_password, SYSDATE + 14)
    RETURNING user_id INTO v_user_id;

    -- Create trial subscription
    SELECT product_id INTO v_prod_id FROM PRODUCTS 
    WHERE product_code = UPPER(p_product) AND ROWNUM = 1;

    INSERT INTO SUBSCRIPTIONS (user_id, product_id, plan_type, status, start_date, end_date)
    VALUES (v_user_id, v_prod_id, 'TRIAL', 'ACTIVE', SYSDATE, SYSDATE + 14);

    -- Log action
    INSERT INTO AUDIT_LOGS (user_id, action, table_name, record_id, new_value)
    VALUES (v_user_id, 'USER_REGISTERED', 'USERS', v_user_id, p_email);

    COMMIT;
    p_user_id := v_user_id;
    p_status  := 'SUCCESS';
    p_message := 'Account created successfully! 14-day free trial started.';

  EXCEPTION
    WHEN NO_DATA_FOUND THEN
      ROLLBACK;
      p_status  := 'ERROR';
      p_message := 'Invalid product selected.';
      p_user_id := 0;
    WHEN OTHERS THEN
      ROLLBACK;
      p_status  := 'ERROR';
      p_message := 'Registration failed: ' || SQLERRM;
      p_user_id := 0;
  END SP_REGISTER_USER;

  -- ── LOGIN USER ───────────────────────────────────────────
  PROCEDURE SP_LOGIN_USER (
    p_email       IN  VARCHAR2,
    p_password    IN  VARCHAR2,
    p_ip_address  IN  VARCHAR2,
    p_user_agent  IN  VARCHAR2,
    p_token       OUT VARCHAR2,
    p_user_id     OUT NUMBER,
    p_full_name   OUT VARCHAR2,
    p_status      OUT VARCHAR2,
    p_message     OUT VARCHAR2
  ) AS
    v_user_id     NUMBER;
    v_pass_hash   VARCHAR2(256);
    v_is_active   CHAR(1);
    v_first_name  VARCHAR2(50);
    v_last_name   VARCHAR2(50);
    v_token       VARCHAR2(256);
  BEGIN
    -- Fetch user
    BEGIN
      SELECT user_id, password_hash, is_active, first_name, last_name
      INTO v_user_id, v_pass_hash, v_is_active, v_first_name, v_last_name
      FROM USERS
      WHERE LOWER(email) = LOWER(p_email);
    EXCEPTION
      WHEN NO_DATA_FOUND THEN
        p_status  := 'ERROR';
        p_message := 'Invalid email or password.';
        p_token   := NULL; p_user_id := 0; p_full_name := NULL;
        RETURN;
    END;

    -- Check account active
    IF v_is_active = 'N' THEN
      p_status  := 'ERROR';
      p_message := 'Your account has been deactivated. Contact support.';
      p_token := NULL; p_user_id := 0; p_full_name := NULL;
      RETURN;
    END IF;

    -- Password validation is done in Python (bcrypt), 
    -- here we just verify the hash matches what Python passed in
    IF v_pass_hash != p_password THEN
      INSERT INTO AUDIT_LOGS (user_id, action, ip_address)
      VALUES (v_user_id, 'LOGIN_FAILED', p_ip_address);
      COMMIT;
      p_status  := 'ERROR';
      p_message := 'Invalid email or password.';
      p_token := NULL; p_user_id := 0; p_full_name := NULL;
      RETURN;
    END IF;

    -- Generate token (SYS_GUID for uniqueness)
    v_token := LOWER(RAWTOHEX(SYS_GUID())) || LOWER(RAWTOHEX(SYS_GUID()));

    -- Invalidate old sessions
    UPDATE USER_SESSIONS SET is_active = 'N'
    WHERE user_id = v_user_id AND is_active = 'Y';

    -- Create new session (24 hour expiry)
    INSERT INTO USER_SESSIONS (user_id, token, ip_address, user_agent, expires_at)
    VALUES (v_user_id, v_token, p_ip_address, p_user_agent, SYSTIMESTAMP + INTERVAL '24' HOUR);

    -- Update last login
    UPDATE USERS SET last_login = SYSTIMESTAMP WHERE user_id = v_user_id;

    -- Audit
    INSERT INTO AUDIT_LOGS (user_id, action, ip_address, table_name, record_id)
    VALUES (v_user_id, 'LOGIN_SUCCESS', p_ip_address, 'USERS', v_user_id);

    COMMIT;
    p_token     := v_token;
    p_user_id   := v_user_id;
    p_full_name := v_first_name || ' ' || v_last_name;
    p_status    := 'SUCCESS';
    p_message   := 'Login successful.';

  EXCEPTION
    WHEN OTHERS THEN
      ROLLBACK;
      p_status  := 'ERROR';
      p_message := 'Login failed: ' || SQLERRM;
      p_token := NULL; p_user_id := 0; p_full_name := NULL;
  END SP_LOGIN_USER;

  -- ── LOGOUT USER ──────────────────────────────────────────
  PROCEDURE SP_LOGOUT_USER (
    p_token   IN  VARCHAR2,
    p_status  OUT VARCHAR2,
    p_message OUT VARCHAR2
  ) AS
  BEGIN
    UPDATE USER_SESSIONS SET is_active = 'N'
    WHERE token = p_token AND is_active = 'Y';

    IF SQL%ROWCOUNT = 0 THEN
      p_status  := 'ERROR';
      p_message := 'Session not found.';
    ELSE
      COMMIT;
      p_status  := 'SUCCESS';
      p_message := 'Logged out successfully.';
    END IF;
  EXCEPTION
    WHEN OTHERS THEN
      ROLLBACK;
      p_status  := 'ERROR';
      p_message := SQLERRM;
  END SP_LOGOUT_USER;

  -- ── VALIDATE SESSION ─────────────────────────────────────
  FUNCTION FN_VALIDATE_SESSION (p_token IN VARCHAR2) RETURN NUMBER AS
    v_user_id NUMBER := 0;
  BEGIN
    SELECT user_id INTO v_user_id
    FROM USER_SESSIONS
    WHERE token = p_token
      AND is_active = 'Y'
      AND expires_at > SYSTIMESTAMP;
    RETURN v_user_id;
  EXCEPTION
    WHEN NO_DATA_FOUND THEN RETURN 0;
    WHEN OTHERS        THEN RETURN 0;
  END FN_VALIDATE_SESSION;

  -- ── GET USER BY TOKEN ─────────────────────────────────────
  PROCEDURE SP_GET_USER_BY_TOKEN (
    p_token     IN  VARCHAR2,
    p_user_id   OUT NUMBER,
    p_email     OUT VARCHAR2,
    p_full_name OUT VARCHAR2,
    p_role      OUT VARCHAR2,
    p_status    OUT VARCHAR2
  ) AS
    v_user_id NUMBER;
  BEGIN
    v_user_id := FN_VALIDATE_SESSION(p_token);
    IF v_user_id = 0 THEN
      p_status := 'ERROR'; RETURN;
    END IF;
    SELECT user_id, email, first_name || ' ' || last_name, user_role
    INTO p_user_id, p_email, p_full_name, p_role
    FROM USERS WHERE user_id = v_user_id;
    p_status := 'SUCCESS';
  EXCEPTION
    WHEN OTHERS THEN p_status := 'ERROR';
  END SP_GET_USER_BY_TOKEN;

END PKG_AUTH;



-- ╔══════════════════════════════════════════════════════════╗
-- ║        PACKAGE: PKG_LEADS  (Demo & Contact)             ║
-- ╚══════════════════════════════════════════════════════════╝
CREATE OR REPLACE PACKAGE PKG_LEADS AS

  PROCEDURE SP_SUBMIT_DEMO_REQUEST (
    p_full_name    IN  VARCHAR2,
    p_email        IN  VARCHAR2,
    p_phone        IN  VARCHAR2,
    p_product_code IN  VARCHAR2,
    p_demo_id      OUT NUMBER,
    p_status       OUT VARCHAR2,
    p_message      OUT VARCHAR2
  );

  PROCEDURE SP_SUBMIT_CONTACT (
    p_full_name IN  VARCHAR2,
    p_email     IN  VARCHAR2,
    p_phone     IN  VARCHAR2,
    p_subject   IN  VARCHAR2,
    p_message   IN  VARCHAR2,
    p_msg_id    OUT NUMBER,
    p_status    OUT VARCHAR2,
    p_out_msg   OUT VARCHAR2
  );

END PKG_LEADS;


CREATE OR REPLACE PACKAGE BODY PKG_LEADS AS

  PROCEDURE SP_SUBMIT_DEMO_REQUEST (
    p_full_name    IN  VARCHAR2,
    p_email        IN  VARCHAR2,
    p_phone        IN  VARCHAR2,
    p_product_code IN  VARCHAR2,
    p_demo_id      OUT NUMBER,
    p_status       OUT VARCHAR2,
    p_message      OUT VARCHAR2
  ) AS
    v_demo_id NUMBER;
    v_count   NUMBER;
  BEGIN
    -- Prevent duplicate demo requests from same email in last 7 days
    SELECT COUNT(*) INTO v_count FROM DEMO_REQUESTS
    WHERE LOWER(email) = LOWER(p_email) AND created_at > SYSTIMESTAMP - INTERVAL '7' DAY;

    IF v_count > 0 THEN
      p_status  := 'INFO';
      p_message := 'Demo already requested. Our team will contact you shortly.';
      p_demo_id := 0;
      RETURN;
    END IF;

    INSERT INTO DEMO_REQUESTS (full_name, email, phone, product_code)
    VALUES (p_full_name, p_email, p_phone, UPPER(p_product_code))
    RETURNING demo_id INTO v_demo_id;

    COMMIT;
    p_demo_id := v_demo_id;
    p_status  := 'SUCCESS';
    p_message := 'Demo request submitted! Our team will contact you within 24 hours.';
  EXCEPTION
    WHEN OTHERS THEN
      ROLLBACK;
      p_status  := 'ERROR';
      p_message := 'Failed to submit: ' || SQLERRM;
      p_demo_id := 0;
  END SP_SUBMIT_DEMO_REQUEST;

  PROCEDURE SP_SUBMIT_CONTACT (
    p_full_name IN  VARCHAR2,
    p_email     IN  VARCHAR2,
    p_phone     IN  VARCHAR2,
    p_subject   IN  VARCHAR2,
    p_message   IN  VARCHAR2,
    p_msg_id    OUT NUMBER,
    p_status    OUT VARCHAR2,
    p_out_msg   OUT VARCHAR2
  ) AS
    v_msg_id NUMBER;
  BEGIN
    INSERT INTO CONTACT_MESSAGES (full_name, email, phone, subject, message)
    VALUES (p_full_name, p_email, p_phone, p_subject, p_message)
    RETURNING message_id INTO v_msg_id;
    COMMIT;
    p_msg_id  := v_msg_id;
    p_status  := 'SUCCESS';
    p_out_msg := 'Message sent! We will reply within 24 hours.';
  EXCEPTION
    WHEN OTHERS THEN
      ROLLBACK;
      p_status  := 'ERROR';
      p_out_msg := SQLERRM;
      p_msg_id  := 0;
  END SP_SUBMIT_CONTACT;

END PKG_LEADS;



-- ╔══════════════════════════════════════════════════════════╗
-- ║       PACKAGE: PKG_DASHBOARD  (User Dashboard)          ║
-- ╚══════════════════════════════════════════════════════════╝
CREATE OR REPLACE PACKAGE PKG_DASHBOARD AS

  PROCEDURE SP_GET_USER_DASHBOARD (
    p_user_id         IN  NUMBER,
    p_total_filings   OUT NUMBER,
    p_total_conv      OUT NUMBER,
    p_active_sub      OUT VARCHAR2,
    p_trial_days_left OUT NUMBER,
    p_status          OUT VARCHAR2
  );

  PROCEDURE SP_SAVE_BANK_CONVERSION (
    p_user_id      IN  NUMBER,
    p_bank_name    IN  VARCHAR2,
    p_file_name    IN  VARCHAR2,
    p_total_entries IN NUMBER,
    p_conv_id      OUT NUMBER,
    p_status       OUT VARCHAR2,
    p_message      OUT VARCHAR2
  );

END PKG_DASHBOARD;


CREATE OR REPLACE PACKAGE BODY PKG_DASHBOARD AS

  PROCEDURE SP_GET_USER_DASHBOARD (
    p_user_id         IN  NUMBER,
    p_total_filings   OUT NUMBER,
    p_total_conv      OUT NUMBER,
    p_active_sub      OUT VARCHAR2,
    p_trial_days_left OUT NUMBER,
    p_status          OUT VARCHAR2
  ) AS
  BEGIN
    SELECT COUNT(*) 
    INTO p_total_filings 
    FROM GST_FILINGS 
    WHERE user_id = p_user_id;
    
    SELECT COUNT(*) 
    INTO p_total_conv    
    FROM BANK_CONVERSIONS 
    WHERE user_id = p_user_id 
    AND status = 'COMPLETED';

    BEGIN
      SELECT p.product_name,
             GREATEST(0, TRUNC(s.end_date - SYSDATE))
      INTO p_active_sub, p_trial_days_left
      FROM SUBSCRIPTIONS s JOIN PRODUCTS p ON s.product_id = p.product_id
      WHERE s.user_id = p_user_id AND s.status = 'ACTIVE'
      AND ROWNUM = 1
      ORDER BY s.end_date DESC;
    EXCEPTION
      WHEN NO_DATA_FOUND THEN
        p_active_sub      := 'No Active Plan';
        p_trial_days_left := 0;
    END;

    p_status := 'SUCCESS';
  EXCEPTION
    WHEN OTHERS THEN p_status := 'ERROR';
  END SP_GET_USER_DASHBOARD;

  PROCEDURE SP_SAVE_BANK_CONVERSION (
    p_user_id       IN  NUMBER,
    p_bank_name     IN  VARCHAR2,
    p_file_name     IN  VARCHAR2,
    p_total_entries IN  NUMBER,
    p_conv_id       OUT NUMBER,
    p_status        OUT VARCHAR2,
    p_message       OUT VARCHAR2
  ) AS
    v_conv_id NUMBER;
  BEGIN
    INSERT INTO BANK_CONVERSIONS (user_id, bank_name, file_name, total_entries, status)
    VALUES (p_user_id, p_bank_name, p_file_name, p_total_entries, 'COMPLETED')
    RETURNING conversion_id INTO v_conv_id;
    COMMIT;
    p_conv_id := v_conv_id;
    p_status  := 'SUCCESS';
    p_message := 'Conversion saved successfully.';
  EXCEPTION
    WHEN OTHERS THEN
      ROLLBACK;
      p_conv_id := 0;
      p_status  := 'ERROR';
      p_message := SQLERRM;
  END SP_SAVE_BANK_CONVERSION;

END PKG_DASHBOARD;


---------------------------------------------------------------------------------------------------------------------------
---------------------------------------------------------------------------------------------------------------------------


-- ============================================================
-- TAXFLOW - ORACLE TRIGGERS
-- File: 03_triggers.sql
-- ============================================================

-- ── TRIGGER 1: Auto-update USERS.updated_at ────────────────
CREATE OR REPLACE TRIGGER TRG_USERS_UPDATED_AT
BEFORE UPDATE ON USERS
FOR EACH ROW
BEGIN
  :NEW.updated_at := SYSTIMESTAMP;
END;
/

-- ── TRIGGER 2: Audit log on user status change ─────────────
CREATE OR REPLACE TRIGGER TRG_USERS_AUDIT
AFTER UPDATE OF is_active, user_role ON USERS
FOR EACH ROW
BEGIN
  IF :OLD.is_active != :NEW.is_active THEN
    INSERT INTO AUDIT_LOGS (user_id, action, table_name, record_id, old_value, new_value)
    VALUES (:NEW.user_id, 'STATUS_CHANGED', 'USERS', :NEW.user_id,
            'is_active=' || :OLD.is_active, 'is_active=' || :NEW.is_active);
  END IF;
  IF :OLD.user_role != :NEW.user_role THEN
    INSERT INTO AUDIT_LOGS (user_id, action, table_name, record_id, old_value, new_value)
    VALUES (:NEW.user_id, 'ROLE_CHANGED', 'USERS', :NEW.user_id,
            :OLD.user_role, :NEW.user_role);
  END IF;
END;


-- ── TRIGGER 3: Expire old sessions on new login ────────────

CREATE OR REPLACE TRIGGER TRG_EXPIRE_OLD_SESSIONS
AFTER INSERT ON USER_SESSIONS
DECLARE
  PRAGMA AUTONOMOUS_TRANSACTION;
BEGIN
  DELETE FROM USER_SESSIONS
  WHERE created_at < SYSTIMESTAMP - INTERVAL '30' DAY;
  COMMIT;
END;
/
/

SELECT line, position, text 
FROM user_errors 
WHERE name = 'TRG_USERS_UPDATED_AT'
ORDER BY line;


-- ── TRIGGER 4: Auto-set subscription end_date ──────────────
CREATE OR REPLACE TRIGGER TRG_SUBSCRIPTION_DATES
BEFORE INSERT ON SUBSCRIPTIONS
FOR EACH ROW
BEGIN
  IF :NEW.end_date IS NULL THEN
    CASE :NEW.plan_type
      WHEN 'TRIAL'   THEN :NEW.end_date := SYSDATE + 14;
      WHEN 'MONTHLY' THEN :NEW.end_date := ADD_MONTHS(SYSDATE, 1);
      WHEN 'YEARLY'  THEN :NEW.end_date := ADD_MONTHS(SYSDATE, 12);
      ELSE :NEW.end_date := SYSDATE + 14;
    END CASE;
  END IF;
END;


-- ── TRIGGER 5: Log demo request inserts ────────────────────
CREATE OR REPLACE TRIGGER TRG_DEMO_REQUEST_LOG
AFTER INSERT ON DEMO_REQUESTS
FOR EACH ROW
BEGIN
  INSERT INTO AUDIT_LOGS (action, table_name, record_id, new_value)
  VALUES ('DEMO_REQUESTED', 'DEMO_REQUESTS', :NEW.demo_id, :NEW.email || ' | ' || :NEW.product_code);
END;

--------------------------------------------------------------------------------

ALTER TRIGGER TRG_USERS_AUDIT COMPILE;
ALTER TRIGGER TRG_EXPIRE_OLD_SESSIONS COMPILE;
ALTER TRIGGER TRG_SUBSCRIPTION_DATES COMPILE;
ALTER TRIGGER TRG_DEMO_REQUEST_LOG COMPILE;


SELECT trigger_name, status FROM user_triggers;

 
---------------------------------------------------------------------------------




SELECT * FROM PRODUCTS;
SELECT * FROM USERS;
SELECT * FROM USER_SESSIONS;
SELECT * FROM SUBSCRIPTIONS;
SELECT * FROM DEMO_REQUESTS;
SELECT * FROM CONTACT_MESSAGES;
SELECT * FROM GST_FILINGS;
SELECT * FROM BANK_CONVERSIONS;
SELECT * FROM AUDIT_LOGS;
 
