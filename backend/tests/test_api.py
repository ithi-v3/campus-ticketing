def new_ticket(client, headers, **overrides):
    body = {"title": "Light flickering", "description": "Tube light flickers all night.",
            "category_id": 1, "location_id": 1, "priority_id": 2}
    body.update(overrides)
    return client.post("/api/tickets", json=body, headers=headers)


# ---- auth ---------------------------------------------------------------

def test_login_wrong_password(client):
    res = client.post("/api/auth/login", json={"email": "admin@campus.test", "password": "nope"})
    assert res.status_code == 401


def test_protected_route_needs_token(client):
    assert client.get("/api/tickets/mine").status_code == 401


def test_signup_ignores_requested_role(client):
    res = client.post("/api/auth/signup", json={
        "full_name": "Sneaky", "email": "sneaky@campus.test",
        "password": "Passw0rd!!", "role": "Admin"})
    assert res.status_code == 201
    assert res.get_json()["user"]["role"] == "Student"


def test_me_returns_current_user(client, admin):
    res = client.get("/api/auth/me", headers=admin)
    assert res.get_json()["user"]["email"] == "admin@campus.test"


# ---- role checks --------------------------------------------------------

def test_student_cannot_list_all_tickets(client, student):
    assert client.get("/api/tickets", headers=student).status_code == 403


def test_technician_cannot_create_ticket(client, technician):
    assert new_ticket(client, technician).status_code == 403


def test_student_cannot_see_someone_elses_ticket(client, student, other_student):
    ticket_id = new_ticket(client, student).get_json()["ticket"]["ticket_id"]
    assert client.get(f"/api/tickets/{ticket_id}", headers=other_student).status_code == 404


def test_student_cannot_pick_critical(client, student):
    assert new_ticket(client, student, priority_id=4).status_code == 400


# ---- ticket lifecycle ---------------------------------------------------

def test_full_lifecycle(client, student, technician, admin):
    ticket_id = new_ticket(client, student).get_json()["ticket"]["ticket_id"]

    mine = client.get("/api/tickets/mine?q=flickering", headers=student).get_json()
    assert any(t["ticket_id"] == ticket_id for t in mine["items"])

    techs = client.get(f"/api/technicians?ticket_id={ticket_id}", headers=admin).get_json()["items"]
    ravi = next(t for t in techs if t["full_name"] == "Ravi Kumar")
    assert ravi["matches_category"]  # Electrical ticket, Electrical technician

    res = client.post(f"/api/tickets/{ticket_id}/assign", json={"technician_id": ravi["user_id"]},
                      headers=admin)
    assert res.status_code == 200
    assert res.get_json()["ticket"]["status"] == "Assigned"

    queue = client.get("/api/tickets/assigned", headers=technician).get_json()
    assert any(t["ticket_id"] == ticket_id for t in queue["items"])

    assert client.patch(f"/api/tickets/{ticket_id}", json={"status": "Resolved"},
                        headers=technician).status_code == 200

    res = client.post(f"/api/tickets/{ticket_id}/feedback", json={"rating": 4, "comments": "ok"},
                      headers=student)
    assert res.status_code == 201
    assert res.get_json()["ticket"]["status"] == "Closed"

    detail = client.get(f"/api/tickets/{ticket_id}", headers=student).get_json()
    assert [h["new_status"] for h in detail["history"]] == ["Open", "Assigned", "Resolved", "Closed"]
    assert detail["feedback"]["rating"] == 4

    # one feedback per ticket, and closed tickets don't take more
    assert client.post(f"/api/tickets/{ticket_id}/feedback", json={"rating": 5},
                       headers=student).status_code == 409


def test_feedback_rating_range(client, student, technician, admin):
    ticket_id = new_ticket(client, student).get_json()["ticket"]["ticket_id"]
    tech_id = client.get("/api/auth/me", headers=technician).get_json()["user"]["user_id"]
    client.post(f"/api/tickets/{ticket_id}/assign", json={"technician_id": tech_id}, headers=admin)
    client.patch(f"/api/tickets/{ticket_id}", json={"status": "Resolved"}, headers=technician)
    assert client.post(f"/api/tickets/{ticket_id}/feedback", json={"rating": 9},
                       headers=student).status_code == 400


# ---- escalation / reports ----------------------------------------------

def test_escalation_sweep_and_notifications(client, admin):
    res = client.post("/api/reports/escalate", headers=admin)
    assert res.status_code == 200
    # the demo data has an overdue unassigned ticket, which the seed already escalated
    tickets = client.get("/api/tickets?status=Escalated", headers=admin).get_json()
    assert tickets["total"] >= 1
    assert client.get("/api/notifications", headers=admin).get_json()["unread"] >= 1


def test_technician_report(client, admin):
    items = client.get("/api/reports/technicians", headers=admin).get_json()["items"]
    assert {"technician_name", "avg_resolution_hours", "open_load"} <= set(items[0])


def test_summary_requires_admin(client, student, admin):
    assert client.get("/api/reports/summary", headers=student).status_code == 403
    assert client.get("/api/reports/summary", headers=admin).status_code == 200


def test_pagination(client, admin):
    res = client.get("/api/tickets?per_page=3&page=2", headers=admin).get_json()
    assert res["per_page"] == 3 and len(res["items"]) <= 3
