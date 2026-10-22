-- Sample queries for demonstrating the schema.
-- Run after 01_schema.sql, 02_seed.sql and 03_demo_data.sql:
--   psql ticketing -f database/04_sample_queries.sql
-- Everything that changes data is wrapped in a transaction and rolled back,
-- so this file can be run repeatedly without altering the demo data.

\echo '--- 1. CRUD: create, read, update, delete (soft delete = Closed) ---'
BEGIN;
INSERT INTO tickets (title, description, user_id, category_id, location_id, priority_id)
VALUES ('Demo: flickering tube light', 'Flickers every night', 6, 1, 1, 2)
RETURNING ticket_id, title, status;

SELECT ticket_id, title, status FROM tickets WHERE title LIKE 'Demo:%';

UPDATE tickets SET priority_id = 3 WHERE title LIKE 'Demo:%'
RETURNING ticket_id, priority_id;

UPDATE tickets SET status = 'Closed' WHERE title LIKE 'Demo:%'   -- "delete" is a soft delete
RETURNING ticket_id, status;
ROLLBACK;

\echo '--- 2. Join: dashboard row with reporter, category, location, priority ---'
SELECT t.ticket_id, t.title, u.full_name AS reporter, c.category_name,
       l.block_name || ' / ' || l.room AS location, p.priority_name, t.status
FROM tickets t
JOIN users u           ON u.user_id = t.user_id
JOIN categories c      ON c.category_id = t.category_id
JOIN locations l       ON l.location_id = t.location_id
JOIN priority_levels p ON p.priority_id = t.priority_id
ORDER BY p.rank DESC, t.created_at;

\echo '--- 3. Left join: tickets with their current technician (NULL if unassigned) ---'
SELECT t.ticket_id, t.title, tech.full_name AS technician
FROM tickets t
LEFT JOIN ticket_assignments a ON a.ticket_id = t.ticket_id AND a.is_current
LEFT JOIN users tech           ON tech.user_id = a.technician_id
ORDER BY t.ticket_id;

\echo '--- 4. Aggregate: tickets per category ---'
SELECT c.category_name, COUNT(t.ticket_id) AS tickets
FROM categories c
LEFT JOIN tickets t ON t.category_id = c.category_id
GROUP BY c.category_name
ORDER BY tickets DESC, c.category_name;

\echo '--- 5. Aggregate: average resolution time (hours) per technician, with HAVING ---'
SELECT u.full_name,
       COUNT(*) AS resolved,
       ROUND(AVG(EXTRACT(EPOCH FROM (t.resolved_at - t.created_at)) / 3600.0), 1) AS avg_hours
FROM ticket_assignments a
JOIN users u   ON u.user_id = a.technician_id
JOIN tickets t ON t.ticket_id = a.ticket_id AND a.is_current
WHERE t.resolved_at IS NOT NULL
GROUP BY u.full_name
HAVING COUNT(*) >= 1
ORDER BY avg_hours;

\echo '--- 6. Aggregate: average rating per technician ---'
SELECT u.full_name, ROUND(AVG(f.rating), 2) AS avg_rating, COUNT(f.feedback_id) AS ratings
FROM feedback f
JOIN ticket_assignments a ON a.ticket_id = f.ticket_id AND a.is_current
JOIN users u              ON u.user_id = a.technician_id
GROUP BY u.full_name;

\echo '--- 7. Subquery: tickets older than the average age of open tickets ---'
SELECT ticket_id, title, status
FROM vw_ticket_summary
WHERE status IN ('Open', 'Escalated')
  AND age_hours > (SELECT AVG(age_hours) FROM vw_ticket_summary WHERE status IN ('Open', 'Escalated'));

\echo '--- 8. View: what the dashboards read ---'
SELECT ticket_id, title, status, priority_name, technician_name, age_hours
FROM vw_ticket_summary
ORDER BY priority_rank DESC, age_hours DESC;

\echo '--- 9. Stored routine: resolution report for all technicians, then one ---'
SELECT * FROM sp_resolution_report(NULL);
SELECT * FROM sp_resolution_report(7);

\echo '--- 10. Transaction: assign a ticket (all three steps succeed or none do) ---'
BEGIN;
SELECT set_config('app.user_id', '1', true);   -- admin is the actor, recorded by the trigger
INSERT INTO ticket_assignments (ticket_id, technician_id, assigned_by)
VALUES (6, 7, 1);
UPDATE tickets SET status = 'Assigned' WHERE ticket_id = 6;
INSERT INTO notifications (user_id, ticket_id, message)
VALUES (7, 6, 'Ticket #6 was assigned to you');
SELECT ticket_id, status FROM tickets WHERE ticket_id = 6;
ROLLBACK;                                       -- change to COMMIT to keep it

\echo '--- 11. Trigger: a status change is written to status_history automatically ---'
BEGIN;
SELECT set_config('app.user_id', '1', true);
UPDATE tickets SET status = 'Closed' WHERE ticket_id = 7;
SELECT old_status, new_status, changed_by FROM status_history
WHERE ticket_id = 7 ORDER BY history_id;
ROLLBACK;

\echo '--- 12. Trigger + function: auto-escalation of overdue Open tickets ---'
BEGIN;
UPDATE tickets SET created_at = CURRENT_TIMESTAMP - INTERVAL '10 days' WHERE ticket_id = 8;
SELECT escalate_overdue_tickets() AS escalated;
SELECT ticket_id, status, priority_id FROM tickets WHERE ticket_id = 8;
SELECT user_id, message FROM notifications WHERE ticket_id = 8;
ROLLBACK;

\echo '--- 13. Constraints reject bad data (each statement is expected to fail) ---'
\set ON_ERROR_STOP off
INSERT INTO feedback (ticket_id, rating) VALUES (10, 9);                 -- CHECK: rating 1-5
UPDATE tickets SET status = 'Bogus' WHERE ticket_id = 3;                 -- CHECK: valid status
INSERT INTO users (full_name, email, password_hash, role_id)
VALUES ('Dup', 'admin@campus.test', 'x', 1);                             -- UNIQUE: email
