-- Optional demo data so the dashboards aren't empty on first run.
-- All demo accounts use the password shown in the README (change them for any real deployment).
-- Passwords are hashed with pgcrypto's bcrypt (crypt/gen_salt('bf')), which the
-- Python bcrypt library can verify.

INSERT INTO users (full_name, email, password_hash, role_id, phone, specialty_category_id, assigned_block)
SELECT v.full_name, v.email, crypt(v.pw, gen_salt('bf', 10)), r.role_id, v.phone,
       (SELECT category_id FROM categories WHERE category_name = v.specialty), v.block
FROM (VALUES
    ('Meera Iyer',     'admin@campus.test',   'Admin@123',   'Admin',      '9840011001', NULL,               NULL),
    ('Ravi Kumar',     'ravi.tech@campus.test',  'Tech@123', 'Technician', '9840011002', 'Electrical',       'Hostel Block A'),
    ('Suresh Babu',    'suresh.tech@campus.test','Tech@123', 'Technician', '9840011003', 'Plumbing',         'Hostel Block B'),
    ('Anita Joseph',   'anita.tech@campus.test', 'Tech@123', 'Technician', '9840011004', 'Wi-Fi / Network',  'Academic Block 1'),
    ('Imran Sheikh',   'imran.tech@campus.test', 'Tech@123', 'Technician', '9840011005', 'Furniture',        'Hostel Block A'),
    ('Divya Nair',     'divya@campus.test',   'Student@123', 'Student',    '9840022001', NULL,               NULL),
    ('Karthik S',      'karthik@campus.test', 'Student@123', 'Student',    '9840022002', NULL,               NULL),
    ('Fatima Rahman',  'fatima@campus.test',  'Student@123', 'Student',    '9840022003', NULL,               NULL)
) AS v(full_name, email, pw, role, phone, specialty, block)
JOIN roles r ON r.role_name = v.role;

-- Helper: tickets are inserted with explicit created_at so aging/escalation can be demonstrated.
INSERT INTO tickets (title, description, user_id, category_id, location_id, priority_id, created_at)
SELECT v.title, v.descr,
       (SELECT user_id FROM users WHERE email = v.reporter),
       (SELECT category_id FROM categories WHERE category_name = v.cat),
       (SELECT location_id FROM locations WHERE block_name = v.blk AND room = v.room),
       (SELECT priority_id FROM priority_levels WHERE priority_name = v.prio),
       CURRENT_TIMESTAMP - v.age
FROM (VALUES
    ('Ceiling fan not working',          'Fan makes a grinding noise and stops after a few minutes.', 'divya@campus.test',   'Electrical',      'Hostel Block A',       'Room 214',                  'Medium', INTERVAL '9 days'),
    ('Tap leaking in washroom',          'Second tap from the left keeps dripping, floor is always wet.', 'karthik@campus.test', 'Plumbing',  'Hostel Block A',       'Common Washroom - Floor 2', 'Medium', INTERVAL '6 days'),
    ('Wi-Fi drops every evening',        'Connection is gone between 7 and 10 pm on the whole floor.', 'fatima@campus.test', 'Wi-Fi / Network','Hostel Block B',       'Room 307',                  'High',   INTERVAL '4 days'),
    ('Projector bulb dead',              'Projector shows a lamp warning and no image.', 'divya@campus.test',   'Electrical',      'Academic Block 1',     'Classroom 204',             'Medium', INTERVAL '3 days'),
    ('Broken study chair',               'One leg of the chair is cracked, unsafe to sit on.', 'karthik@campus.test', 'Furniture',   'Hostel Block B',       'Room 105',                  'Low',    INTERVAL '2 days'),
    ('AC not cooling in lab',            'AC blows warm air, lab gets very hot by afternoon.', 'fatima@campus.test', 'Air Conditioning', 'Computer Lab Complex', 'Lab 2',                   'High',   INTERVAL '3 days'),
    ('Power socket sparking',            'Socket near the study table sparks when a charger is plugged in.', 'divya@campus.test', 'Electrical', 'Hostel Block A', 'Room 101',                    'Critical', INTERVAL '5 hours'),
    ('Window latch broken',              'Window cannot be locked from inside.', 'karthik@campus.test', 'Civil Works', 'Hostel Block B', 'Room 307',                                             'Low',    INTERVAL '1 hour'),
    ('Mess hall drain blocked',          'Water stands near the dish wash area and smells.', 'fatima@campus.test', 'Plumbing',   'Hostel Block B',       'Mess Hall',                 'High',   INTERVAL '12 days'),
    ('Whiteboard marker tray missing',   'Tray fell off the wall and needs re-fixing.', 'divya@campus.test',   'Furniture',       'Academic Block 2',     'Classroom 118',             'Low',    INTERVAL '10 days')
) AS v(title, descr, reporter, cat, blk, room, prio, age);

-- Assign a few tickets to technicians (same shape as the API's assign transaction).
WITH picks AS (
    SELECT t.ticket_id, u.user_id AS tech_id
    FROM tickets t
    JOIN users u ON u.email = CASE t.title
        WHEN 'Ceiling fan not working'        THEN 'ravi.tech@campus.test'
        WHEN 'Tap leaking in washroom'        THEN 'suresh.tech@campus.test'
        WHEN 'Wi-Fi drops every evening'      THEN 'anita.tech@campus.test'
        WHEN 'Projector bulb dead'            THEN 'ravi.tech@campus.test'
        WHEN 'Broken study chair'             THEN 'imran.tech@campus.test'
        WHEN 'Mess hall drain blocked'        THEN 'suresh.tech@campus.test'
        WHEN 'Whiteboard marker tray missing' THEN 'imran.tech@campus.test'
    END
),
ins AS (
    INSERT INTO ticket_assignments (ticket_id, technician_id, assigned_by, assigned_at)
    SELECT ticket_id, tech_id, (SELECT user_id FROM users WHERE email = 'admin@campus.test'),
           (SELECT created_at FROM tickets WHERE ticket_id = picks.ticket_id) + INTERVAL '3 hours'
    FROM picks
    RETURNING ticket_id
)
UPDATE tickets SET status = 'Assigned' WHERE ticket_id IN (SELECT ticket_id FROM ins);

-- Resolve some of them, with resolved_at set explicitly so the analytics have real durations.
UPDATE tickets SET status = 'Resolved', resolved_at = created_at + INTERVAL '30 hours'
WHERE title = 'Ceiling fan not working';
UPDATE tickets SET status = 'Resolved', resolved_at = created_at + INTERVAL '52 hours'
WHERE title = 'Tap leaking in washroom';
UPDATE tickets SET status = 'Resolved', resolved_at = created_at + INTERVAL '20 hours'
WHERE title = 'Whiteboard marker tray missing';

-- Feedback closes a ticket (the API does the same in one transaction).
INSERT INTO feedback (ticket_id, rating, comments)
SELECT ticket_id, v.rating, v.comments
FROM tickets t
JOIN (VALUES
    ('Ceiling fan not working',        5, 'Fixed the same day I was told. Thanks.'),
    ('Tap leaking in washroom',        3, 'Works now but it took two visits.')
) AS v(title, rating, comments) ON v.title = t.title;
UPDATE tickets SET status = 'Closed' WHERE ticket_id IN (SELECT ticket_id FROM feedback);

-- Let the escalation sweep catch whatever is overdue (e.g. the mess hall drain stays Assigned,
-- so it is left alone; unassigned Open tickets older than their threshold get escalated).
SELECT escalate_overdue_tickets();

-- Tidy the history timestamps so they look like a real timeline instead of "all just now".
UPDATE status_history h
SET changed_at = t.created_at
FROM tickets t
WHERE t.ticket_id = h.ticket_id AND h.old_status IS NULL;

UPDATE status_history h
SET changed_at = a.assigned_at
FROM ticket_assignments a
WHERE a.ticket_id = h.ticket_id AND h.new_status = 'Assigned';

UPDATE status_history h
SET changed_at = t.resolved_at
FROM tickets t
WHERE t.ticket_id = h.ticket_id AND h.new_status = 'Resolved' AND t.resolved_at IS NOT NULL;

UPDATE status_history h
SET changed_at = t.resolved_at + INTERVAL '4 hours'
FROM tickets t
WHERE t.ticket_id = h.ticket_id AND h.new_status = 'Closed';

UPDATE feedback f SET submitted_at = t.resolved_at + INTERVAL '4 hours'
FROM tickets t WHERE t.ticket_id = f.ticket_id;
