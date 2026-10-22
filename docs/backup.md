# Backup and recovery

The database is PostgreSQL, so backups use its own tools: `pg_dump` for a backup and
`pg_restore` to recover from it.

## Take a backup

```bash
pg_dump -Fc ticketing > ticketing.dump
```

`-Fc` writes the compressed custom format. `database/backup.sh` does the same with a timestamped
file name and keeps only the 14 newest dumps:

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/ticketing ./database/backup.sh
```

## Restore

Into an existing database, replacing what is there:

```bash
pg_restore --clean --if-exists -d ticketing ticketing.dump
```

Into a fresh database (useful for checking a backup actually works):

```bash
createdb ticketing_restored
pg_restore -d ticketing_restored ticketing.dump
psql ticketing_restored -c "SELECT COUNT(*) FROM tickets;"
```

## Scheduling

Linux or macOS, daily at 2 am (`crontab -e`):

```
0 2 * * * DATABASE_URL=postgresql://user:password@localhost:5432/ticketing /path/to/database/backup.sh
```

Windows: Task Scheduler, Create Basic Task, daily, action "Start a program" running
`C:\Program Files\PostgreSQL\16\bin\pg_dump.exe` with arguments
`-Fc -U postgres -f C:\backups\ticketing.dump ticketing`.

On Render the managed PostgreSQL service also keeps its own automatic backups, which can be
restored from the Render dashboard.

## Test the restore

A backup that has never been restored is only a hope. Do the "fresh database" restore above
after the first backup and compare the row counts of a few tables with the original.
