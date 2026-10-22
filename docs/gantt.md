# Project timeline

Five-week plan for the Campus Maintenance Desk.

| Task | Wk 1 | Wk 2 | Wk 3 | Wk 4 | Wk 5 |
|---|:-:|:-:|:-:|:-:|:-:|
| Requirements and ER design | ██ | | | | |
| Schema and database implementation | ██ | ██ | | | |
| Backend API, ORM and authentication | | ██ | ██ | | |
| Frontend and role-based UI | | | ██ | ██ | |
| Triggers, views and stored routines | | | ██ | | |
| Testing and security hardening | | | | ██ | |
| CI/CD, Docker, deployment and documentation | | | | | ██ |

The same plan as a Mermaid Gantt chart (GitHub renders it on this page):

```mermaid
gantt
    title Campus Maintenance Desk
    dateFormat  YYYY-MM-DD
    axisFormat  Week %W
    section Design
    Requirements and ER design             :a1, 2026-09-14, 7d
    section Database
    Schema and implementation              :a2, 2026-09-14, 14d
    Triggers, views and routines           :a3, 2026-09-28, 7d
    section Application
    Backend API, ORM and auth              :a4, 2026-09-21, 14d
    Frontend and role-based UI             :a5, 2026-09-28, 14d
    section Quality and release
    Testing and security hardening         :a6, 2026-10-05, 7d
    CI/CD, Docker, deployment, docs        :a7, 2026-10-12, 7d
```
