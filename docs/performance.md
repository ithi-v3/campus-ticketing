# Performance notes: index on `tickets(status)`

The dashboards filter tickets by status all the time ("show Open tickets"), so `tickets(status)`
is indexed. To check that the index earns its place, `database/05_performance_test.sql` loads
50,000 generated tickets into a scratch database (about 2% of them Open) and runs the same
`EXPLAIN ANALYZE` query with and without the index.

## How to reproduce

```bash
createdb ticketing_perf
psql ticketing_perf -f database/01_schema.sql -f database/02_seed.sql -f database/03_demo_data.sql
psql ticketing_perf -f database/05_performance_test.sql
```

## Results

Paste the two `Execution Time` lines your run printed:

| Plan | Execution time |
|---|---|
| With `idx_tickets_status` | _ms (paste yours) |
| Without the index | _ms (paste yours) |

On the machine this was written on, the indexed query used an Index Scan and the unindexed one fell
back to a Seq Scan over the whole table, and the indexed query was several times faster. Your
absolute numbers will differ with hardware; the shape (Index Scan vs Seq Scan) is what to look for.

## Other indexes

| Index | Why |
|---|---|
| `tickets(category_id)`, `tickets(location_id)`, `tickets(user_id)` | filters and joins on the dashboards |
| `ticket_assignments(technician_id, ticket_id)` | a technician's workload and queue |
| partial unique index on `ticket_assignments(ticket_id) WHERE is_current` | enforces one current assignment per ticket, and makes the "current technician" lookup cheap |
| `status_history(ticket_id, changed_at)` | the history timeline on the ticket page |
| `notifications(user_id, is_read)` | the unread counter in the header |
