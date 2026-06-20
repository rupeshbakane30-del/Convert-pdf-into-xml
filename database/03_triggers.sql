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
/

-- ── TRIGGER 3: Expire old sessions on new login ────────────
CREATE OR REPLACE TRIGGER TRG_EXPIRE_OLD_SESSIONS
AFTER INSERT ON USER_SESSIONS
FOR EACH ROW
BEGIN
  -- Delete sessions older than 30 days (cleanup)
  DELETE FROM USER_SESSIONS
  WHERE user_id = :NEW.user_id
    AND session_id != :NEW.session_id
    AND created_at < SYSTIMESTAMP - INTERVAL '30' DAY;
END;
/

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
/

-- ── TRIGGER 5: Log demo request inserts ────────────────────
CREATE OR REPLACE TRIGGER TRG_DEMO_REQUEST_LOG
AFTER INSERT ON DEMO_REQUESTS
FOR EACH ROW
BEGIN
  INSERT INTO AUDIT_LOGS (action, table_name, record_id, new_value)
  VALUES ('DEMO_REQUESTED', 'DEMO_REQUESTS', :NEW.demo_id, :NEW.email || ' | ' || :NEW.product_code);
END;
/

PROMPT '✅ Triggers created successfully!';
