# ER diagram

Paste the block below into https://mermaid.live (or any Mermaid viewer) to get the picture;
GitHub also renders it directly on this page.

```mermaid
erDiagram
    ROLES ||--o{ USERS : "has"
    CATEGORIES ||--o{ USERS : "technician specialty"
    USERS ||--o{ TICKETS : "raises"
    CATEGORIES ||--o{ TICKETS : "classifies"
    LOCATIONS ||--o{ TICKETS : "occurs at"
    PRIORITY_LEVELS ||--o{ TICKETS : "ranks"
    TICKETS ||--o{ TICKET_ASSIGNMENTS : "is assigned via"
    USERS ||--o{ TICKET_ASSIGNMENTS : "works on (technician)"
    TICKETS ||--o{ STATUS_HISTORY : "logs"
    USERS ||--o{ STATUS_HISTORY : "changed by"
    TICKETS ||--o| FEEDBACK : "receives"
    USERS ||--o{ NOTIFICATIONS : "receives"
    TICKETS ||--o{ NOTIFICATIONS : "about"

    ROLES { int role_id PK  string role_name UK }
    USERS { int user_id PK  string email UK  string password_hash  int role_id FK  int specialty_category_id FK  string assigned_block  bool is_active }
    CATEGORIES { int category_id PK  string category_name UK }
    LOCATIONS { int location_id PK  string block_name  string room  string location_type }
    PRIORITY_LEVELS { int priority_id PK  string priority_name UK  int rank UK  int escalation_days }
    TICKETS { int ticket_id PK  string title  text description  int user_id FK  int category_id FK  int location_id FK  int priority_id FK  string status  timestamp created_at  timestamp resolved_at }
    TICKET_ASSIGNMENTS { int assignment_id PK  int ticket_id FK  int technician_id FK  int assigned_by FK  bool is_current }
    STATUS_HISTORY { int history_id PK  int ticket_id FK  string old_status  string new_status  int changed_by FK  timestamp changed_at }
    FEEDBACK { int feedback_id PK  int ticket_id FK,UK  int rating  string comments }
    NOTIFICATIONS { int notification_id PK  int user_id FK  int ticket_id FK  string message  bool is_read }
```

The many-to-many between tickets and technicians is `ticket_assignments`. Only one row per
ticket can have `is_current = true` (partial unique index), the rest are the reassignment history.
