-- Shows what the index on tickets(status) buys you.
-- Adds 50,000 throw-away tickets, so run this on a scratch copy of the database,
-- not on your real data:  createdb ticketing_perf && load 01, 02, 03, then this file.
--
-- Copy the "Execution Time" lines from the two EXPLAIN outputs into docs/performance.md.

INSERT INTO tickets (title, description, user_id, category_id, location_id, priority_id, status, created_at)
SELECT 'Load test ' || g, 'generated row', 6,
       1 + (g % 7), 1 + (g % 16), 1 + (g % 4),
       CASE WHEN g % 50 = 0 THEN 'Open' ELSE 'Closed' END,      -- about 2% are Open
       CURRENT_TIMESTAMP - (g || ' minutes')::interval
FROM generate_series(1, 50000) AS g;
ANALYZE tickets;

\echo '=== WITH the index idx_tickets_status ==='
EXPLAIN ANALYZE SELECT ticket_id, title FROM tickets WHERE status = 'Open';

DROP INDEX idx_tickets_status;
\echo '=== WITHOUT the index ==='
EXPLAIN ANALYZE SELECT ticket_id, title FROM tickets WHERE status = 'Open';

CREATE INDEX idx_tickets_status ON tickets (status);   -- put it back
ANALYZE tickets;
