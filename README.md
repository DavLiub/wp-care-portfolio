# WP Care Portfolio Infrastructure

This repository contains the Docker and operations files for the `WP Care by David` WordPress portfolio site.

The live WordPress content is managed from the WordPress admin UI. This repository is intentionally limited to infrastructure and maintenance scripts.

## Project Layout

```text
/opt/sites/wp-care-portfolio/
├── docker-compose.yml       # WordPress + MariaDB containers
├── .env.example             # Safe example environment file
├── .env                     # Real runtime secrets, not committed
├── credentials.private.txt  # Private admin notes, not committed
├── db/                      # MariaDB data directory, not committed
├── wp-content/              # WordPress themes, plugins, uploads, not committed
└── scripts/
    ├── backup.sh            # Backup script
    └── restore.sh           # Restore script
```

Backups are stored outside the Git repository:

```text
/opt/sites/backups/wp-care-portfolio/
├── daily/
├── weekly/
├── monthly/
└── backup.log
```

## Docker Services

The site runs with Docker Compose from:

```bash
cd /opt/sites/wp-care-portfolio
```

Useful commands:

```bash
docker compose ps
docker compose logs --tail 80
docker compose up -d
docker compose down
```

The current temporary URL is:

```text
http://158.69.220.116:8081
```

A domain and HTTPS reverse proxy can be added later.

## Backup Scheme

Backups are created as separate database and files archives.

Retention policy:

```text
5 daily backup sets
3 weekly backup sets
2 monthly backup sets
```

With the current site size, one files archive is about 101 MB. The approximate retained storage is:

```text
5 daily    ~505 MB
3 weekly   ~303 MB
2 monthly  ~202 MB
Total      ~1 GB plus small database dumps
```

Each backup set contains:

```text
database-YYYYMMDDTHHMMSSZ.sql.gz
files-YYYYMMDDTHHMMSSZ.tar.gz
checksums-YYYYMMDDTHHMMSSZ.sha256
```

The database dump is made with `mariadb-dump` from the MariaDB container using `--single-transaction`. This is safer than copying the live `db/` directory directly.

The files archive contains:

```text
docker-compose.yml
.env
.env.example
credentials.private.txt
wp-content/
```

It excludes:

```text
db/
.git/
scripts/
```

## Manual Backup

Run a daily backup manually:

```bash
cd /opt/sites/wp-care-portfolio
scripts/backup.sh daily
```

Run a weekly backup manually:

```bash
scripts/backup.sh weekly
```

Run a monthly backup manually:

```bash
scripts/backup.sh monthly
```

Run automatic mode manually:

```bash
scripts/backup.sh auto
```

Automatic mode chooses the backup type by date:

```text
monthly on day 01
weekly on Sunday
daily otherwise
```

## Scheduler

The scheduler is a normal user crontab for the `ubuntu` user.

Installed cron entry:

```cron
15 2 * * * cd /opt/sites/wp-care-portfolio && /opt/sites/wp-care-portfolio/scripts/backup.sh auto >> /opt/sites/backups/wp-care-portfolio/backup.log 2>&1
```

This runs every day at 02:15 according to the VPS system timezone. The script decides whether that run should be daily, weekly or monthly.

Check the installed scheduler:

```bash
crontab -l
```

Check backup logs:

```bash
tail -100 /opt/sites/backups/wp-care-portfolio/backup.log
```

## Restore

Restore requires one database archive and the matching files archive from the same timestamp.

Example:

```bash
cd /opt/sites/wp-care-portfolio
scripts/restore.sh \
  /opt/sites/backups/wp-care-portfolio/daily/database-20260830T193157Z.sql.gz \
  /opt/sites/backups/wp-care-portfolio/daily/files-20260830T193157Z.tar.gz
```

The restore script will ask for confirmation. Type:

```text
RESTORE
```

For non-interactive restore:

```bash
scripts/restore.sh database.sql.gz files.tar.gz --yes
```

Restore behavior:

1. Validates the database gzip archive.
2. Extracts the files archive to a temporary directory.
3. Stops the WordPress container.
4. Moves the current `wp-content/` aside to `wp-content.before-restore-TIMESTAMP`.
5. Copies restored `wp-content/` into place.
6. Drops and recreates the configured MariaDB database.
7. Imports the SQL dump.
8. Starts the WordPress container.
9. Fixes `wp-content` ownership inside the WordPress container.

## Verify Backups

List backup files:

```bash
find /opt/sites/backups/wp-care-portfolio -maxdepth 2 -type f -printf '%s %p\n' | sort
```

Verify checksums from a backup directory:

```bash
cd /opt/sites/backups/wp-care-portfolio/daily
sha256sum -c checksums-YYYYMMDDTHHMMSSZ.sha256
```

## Git Safety

The repository should not track live secrets, database files or uploaded WordPress content.

Expected committed files:

```text
README.md
.env.example
.gitignore
docker-compose.yml
scripts/backup.sh
scripts/restore.sh
```

Expected ignored files:

```text
.env
credentials.private.txt
db/
wp-content/
/opt/sites/backups/
```
