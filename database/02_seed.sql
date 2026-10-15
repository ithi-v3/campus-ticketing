-- Reference data the app needs before anyone can sign up.

INSERT INTO roles (role_name) VALUES ('Student'), ('Technician'), ('Admin');

INSERT INTO priority_levels (priority_name, rank, escalation_days) VALUES
    ('Low',      1, 5),
    ('Medium',   2, 3),
    ('High',     3, 2),
    ('Critical', 4, 1);

INSERT INTO categories (category_name, description) VALUES
    ('Electrical',       'Lights, fans, sockets, wiring, power cuts'),
    ('Plumbing',         'Leaks, blocked drains, taps, water supply'),
    ('Furniture',        'Beds, desks, chairs, cupboards, doors'),
    ('Wi-Fi / Network',  'Wi-Fi outages, LAN ports, slow connection'),
    ('Air Conditioning', 'AC and ventilation faults'),
    ('Civil Works',      'Walls, ceilings, windows, flooring'),
    ('Housekeeping',     'Cleaning, pest control, waste collection');

INSERT INTO locations (block_name, room, location_type) VALUES
    ('Hostel Block A', 'Room 101', 'Hostel'),
    ('Hostel Block A', 'Room 214', 'Hostel'),
    ('Hostel Block A', 'Common Washroom - Floor 2', 'Hostel'),
    ('Hostel Block B', 'Room 105', 'Hostel'),
    ('Hostel Block B', 'Room 307', 'Hostel'),
    ('Hostel Block B', 'Mess Hall', 'Common'),
    ('Academic Block 1', 'Classroom 204', 'Academic'),
    ('Academic Block 1', 'Classroom 310', 'Academic'),
    ('Academic Block 1', 'Faculty Corridor', 'Academic'),
    ('Academic Block 2', 'Seminar Hall', 'Academic'),
    ('Academic Block 2', 'Classroom 118', 'Academic'),
    ('Computer Lab Complex', 'Lab 1', 'Lab'),
    ('Computer Lab Complex', 'Lab 2', 'Lab'),
    ('Electronics Lab Block', 'Lab 4', 'Lab'),
    ('Central Library', 'Reading Hall', 'Common'),
    ('Sports Complex', 'Gym', 'Common');
