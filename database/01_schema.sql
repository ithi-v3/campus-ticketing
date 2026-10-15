-- Campus Complaint & Maintenance Ticketing System
-- PostgreSQL schema: tables, indexes, view, function, triggers
-- Run order: 01_schema.sql -> 02_seed.sql -> 03_demo_data.sql (optional)

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------
-- Lookup tables
-- ---------------------------------------------------------------

CREATE TABLE roles (
    role_id    SERIAL PRIMARY KEY,
    role_name  VARCHAR(20) NOT NULL UNIQUE
);

CREATE TABLE categories (
    category_id    SERIAL PRIMARY KEY,
    category_name  VARCHAR(50) NOT NULL UNIQUE,
    description    VARCHAR(200)
);

CREATE TABLE locations (
    location_id    SERIAL PRIMARY KEY,
    block_name     VARCHAR(60) NOT NULL,
    room           VARCHAR(30) NOT NULL,
    location_type  VARCHAR(20) NOT NULL
        CHECK (location_type IN ('Hostel', 'Academic', 'Lab', 'Common')),
    UNIQUE (block_name, room)
);

-- escalation_days: how long an Open ticket may sit before it is escalated.
-- rank: 1 = lowest. Escalation bumps a ticket to the next rank.
CREATE TABLE priority_levels (
    priority_id      SERIAL PRIMARY KEY,
    priority_name    VARCHAR(20) NOT NULL UNIQUE,
    rank             INT NOT NULL UNIQUE,
    escalation_days  INT NOT NULL DEFAULT 3 CHECK (escalation_days > 0)
);

-- ---------------------------------------------------------------
-- Users (single table for all three roles)
-- ---------------------------------------------------------------

-- specialty_category_id / assigned_block are only filled for technicians
-- and are used to suggest who a ticket should be routed to.
CREATE TABLE users (
    user_id               SERIAL PRIMARY KEY,
    full_name             VARCHAR(100) NOT NULL,
    email                 VARCHAR(120) NOT NULL UNIQUE,
    password_hash         VARCHAR(255) NOT NULL,
    role_id               INT NOT NULL REFERENCES roles (role_id),
    phone                 VARCHAR(20),
    specialty_category_id INT REFERENCES categories (category_id),
    assigned_block        VARCHAR(60),
    is_active             BOOLEAN NOT NULL DEFAULT TRUE,
    created_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------
-- Tickets and everything hanging off them
-- ---------------------------------------------------------------

CREATE TABLE tickets (
    ticket_id    SERIAL PRIMARY KEY,
    title        VARCHAR(150) NOT NULL,
    description  TEXT NOT NULL,
    user_id      INT NOT NULL REFERENCES users (user_id),
    category_id  INT NOT NULL REFERENCES categories (category_id),
    location_id  INT NOT NULL REFERENCES locations (location_id),
    priority_id  INT NOT NULL REFERENCES priority_levels (priority_id),
    status       VARCHAR(20) NOT NULL DEFAULT 'Open'
        CHECK (status IN ('Open', 'Assigned', 'Escalated', 'Resolved', 'Closed')),
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at  TIMESTAMP
);

-- A ticket can be reassigned, so assignments are kept as history.
-- Exactly one row per ticket may have is_current = TRUE (see index below).
CREATE TABLE ticket_assignments (
    assignment_id  SERIAL PRIMARY KEY,
    ticket_id      INT NOT NULL REFERENCES tickets (ticket_id) ON DELETE CASCADE,
    technician_id  INT NOT NULL REFERENCES users (user_id),
    assigned_by    INT REFERENCES users (user_id),
    assigned_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_current     BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE status_history (
    history_id  SERIAL PRIMARY KEY,
    ticket_id   INT NOT NULL REFERENCES tickets (ticket_id) ON DELETE CASCADE,
    old_status  VARCHAR(20),
    new_status  VARCHAR(20) NOT NULL,
    changed_by  INT REFERENCES users (user_id),   -- NULL = system (auto-escalation)
    changed_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    remarks     VARCHAR(255)
);

CREATE TABLE feedback (
    feedback_id   SERIAL PRIMARY KEY,
    ticket_id     INT NOT NULL UNIQUE REFERENCES tickets (ticket_id) ON DELETE CASCADE,
    rating        INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comments      VARCHAR(500),
    submitted_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE notifications (
    notification_id  SERIAL PRIMARY KEY,
    user_id          INT NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    ticket_id        INT REFERENCES tickets (ticket_id) ON DELETE CASCADE,
    message          VARCHAR(255) NOT NULL,
    is_read          BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------

CREATE INDEX idx_tickets_status      ON tickets (status);
CREATE INDEX idx_tickets_category    ON tickets (category_id);
CREATE INDEX idx_tickets_location    ON tickets (location_id);
CREATE INDEX idx_tickets_user        ON tickets (user_id);
CREATE INDEX idx_assign_tech_ticket  ON ticket_assignments (technician_id, ticket_id);
CREATE UNIQUE INDEX uq_one_current_assignment
    ON ticket_assignments (ticket_id) WHERE is_current;
CREATE INDEX idx_history_ticket      ON status_history (ticket_id, changed_at);
CREATE INDEX idx_notif_user_unread   ON notifications (user_id, is_read);

-- ---------------------------------------------------------------
-- View used by every dashboard
-- ---------------------------------------------------------------

CREATE VIEW vw_ticket_summary AS
SELECT
    t.ticket_id,
    t.title,
    t.description,
    t.status,
    t.created_at,
    t.updated_at,
    t.resolved_at,
    ROUND(EXTRACT(EPOCH FROM (COALESCE(t.resolved_at, CURRENT_TIMESTAMP) - t.created_at)) / 3600.0, 1)
        AS age_hours,
    p.priority_id,
    p.priority_name,
    p.rank AS priority_rank,
    c.category_id,
    c.category_name,
    l.location_id,
    l.block_name,
    l.room,
    l.block_name || ' / ' || l.room AS location_label,
    u.user_id  AS reporter_id,
    u.full_name AS reporter_name,
    tech.user_id   AS technician_id,
    tech.full_name AS technician_name,
    lh.changed_at  AS last_status_change,
    f.rating
FROM tickets t
JOIN users u            ON u.user_id = t.user_id
JOIN categories c       ON c.category_id = t.category_id
JOIN locations l        ON l.location_id = t.location_id
JOIN priority_levels p  ON p.priority_id = t.priority_id
LEFT JOIN ticket_assignments ta ON ta.ticket_id = t.ticket_id AND ta.is_current
LEFT JOIN users tech    ON tech.user_id = ta.technician_id
LEFT JOIN feedback f    ON f.ticket_id = t.ticket_id
LEFT JOIN LATERAL (
    SELECT h.changed_at
    FROM status_history h
    WHERE h.ticket_id = t.ticket_id
    ORDER BY h.changed_at DESC, h.history_id DESC
    LIMIT 1
) lh ON TRUE;

-- ---------------------------------------------------------------
-- Stored routine: resolution report
-- Pass a technician id for one person, or NULL for everyone.
-- (Postgres PROCEDUREs can't return rows, so this is a function.)
-- ---------------------------------------------------------------

CREATE OR REPLACE FUNCTION sp_resolution_report(p_technician_id INT DEFAULT NULL)
RETURNS TABLE (
    technician_id        INT,
    technician_name      VARCHAR,
    tickets_assigned     BIGINT,
    tickets_resolved     BIGINT,
    open_load            BIGINT,
    avg_resolution_hours NUMERIC,
    avg_rating           NUMERIC
)
LANGUAGE sql STABLE AS $$
    SELECT
        u.user_id,
        u.full_name,
        COUNT(t.ticket_id),
        COUNT(t.ticket_id) FILTER (WHERE t.status IN ('Resolved', 'Closed')),
        COUNT(t.ticket_id) FILTER (WHERE t.status IN ('Assigned', 'Escalated')),
        ROUND(AVG(EXTRACT(EPOCH FROM (t.resolved_at - t.created_at)) / 3600.0)
              FILTER (WHERE t.resolved_at IS NOT NULL), 1),
        ROUND(AVG(f.rating), 2)
    FROM users u
    JOIN roles r ON r.role_id = u.role_id AND r.role_name = 'Technician'
    LEFT JOIN ticket_assignments ta ON ta.technician_id = u.user_id AND ta.is_current
    LEFT JOIN tickets t ON t.ticket_id = ta.ticket_id
    LEFT JOIN feedback f ON f.ticket_id = t.ticket_id
    WHERE p_technician_id IS NULL OR u.user_id = p_technician_id
    GROUP BY u.user_id, u.full_name
    ORDER BY u.full_name;
$$;

-- ---------------------------------------------------------------
-- Triggers
-- ---------------------------------------------------------------

-- 1. Keep updated_at / resolved_at honest.
CREATE OR REPLACE FUNCTION fn_ticket_timestamps() RETURNS trigger AS $$
BEGIN
    NEW.updated_at := CURRENT_TIMESTAMP;
    IF NEW.status = 'Resolved' AND OLD.status <> 'Resolved' AND NEW.resolved_at IS NULL THEN
        NEW.resolved_at := CURRENT_TIMESTAMP;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_ticket_timestamps
    BEFORE UPDATE ON tickets
    FOR EACH ROW EXECUTE FUNCTION fn_ticket_timestamps();

-- 2. Write a status_history row whenever a ticket is created or its status
--    changes. The API tells us who is acting by setting app.user_id for the
--    transaction (SET LOCAL); when it is not set the change is "system".
CREATE OR REPLACE FUNCTION fn_log_status() RETURNS trigger AS $$
DECLARE
    actor INT := NULLIF(current_setting('app.user_id', TRUE), '')::INT;
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO status_history (ticket_id, old_status, new_status, changed_by, remarks)
        VALUES (NEW.ticket_id, NULL, NEW.status, NEW.user_id, 'Ticket raised');
    ELSIF NEW.status IS DISTINCT FROM OLD.status THEN
        INSERT INTO status_history (ticket_id, old_status, new_status, changed_by)
        VALUES (NEW.ticket_id, OLD.status, NEW.status, actor);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_log_status
    AFTER INSERT OR UPDATE OF status ON tickets
    FOR EACH ROW EXECUTE FUNCTION fn_log_status();

-- 3. Auto-escalation. When a ticket flips to 'Escalated' tell the reporter,
--    the current technician (if any) and every admin.
CREATE OR REPLACE FUNCTION fn_notify_escalation() RETURNS trigger AS $$
BEGIN
    INSERT INTO notifications (user_id, ticket_id, message)
    SELECT DISTINCT recipient, NEW.ticket_id,
           'Ticket #' || NEW.ticket_id || ' "' || LEFT(NEW.title, 60) || '" has been escalated'
    FROM (
        SELECT NEW.user_id AS recipient
        UNION
        SELECT ta.technician_id FROM ticket_assignments ta
            WHERE ta.ticket_id = NEW.ticket_id AND ta.is_current
        UNION
        SELECT u.user_id FROM users u JOIN roles r ON r.role_id = u.role_id
            WHERE r.role_name = 'Admin' AND u.is_active
    ) x;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_auto_escalate
    AFTER UPDATE OF status ON tickets
    FOR EACH ROW
    WHEN (NEW.status = 'Escalated' AND OLD.status IS DISTINCT FROM 'Escalated')
    EXECUTE FUNCTION fn_notify_escalation();

-- The sweep that actually finds overdue tickets. A trigger only fires when a
-- row changes, so something has to flip the status once a ticket gets old;
-- the Flask app calls this every few minutes (and admins can run it by hand).
-- Returns how many tickets were escalated.
CREATE OR REPLACE FUNCTION escalate_overdue_tickets() RETURNS INT AS $$
DECLARE
    n INT;
BEGIN
    UPDATE tickets t
    SET status = 'Escalated',
        priority_id = COALESCE(
            (SELECT p2.priority_id FROM priority_levels p2
              WHERE p2.rank = (SELECT p1.rank + 1 FROM priority_levels p1
                                WHERE p1.priority_id = t.priority_id)),
            t.priority_id)
    FROM priority_levels p
    WHERE p.priority_id = t.priority_id
      AND t.status = 'Open'
      AND t.created_at < CURRENT_TIMESTAMP - (p.escalation_days * INTERVAL '1 day');
    GET DIAGNOSTICS n = ROW_COUNT;
    RETURN n;
END;
$$ LANGUAGE plpgsql;
