#!/usr/bin/env bash
set -Eeuo pipefail

SITE_DIR="${SITE_DIR:-/opt/sites/wp-care-portfolio}"

usage() {
  cat <<USAGE
Usage: $0 /path/to/database-TIMESTAMP.sql.gz /path/to/files-TIMESTAMP.tar.gz [--yes]

Restores:
  database dump into the configured MariaDB database
  wp-content/ from the files archive

The current wp-content directory is moved aside before restore.
The current database is dropped and recreated.
USAGE
}

db_archive="${1:-}"
files_archive="${2:-}"
confirm="${3:-}"

if [ -z "$db_archive" ] || [ "$db_archive" = "-h" ] || [ "$db_archive" = "--help" ]; then
  usage
  exit 0
fi

if [ -z "$files_archive" ]; then
  usage >&2
  exit 2
fi

if [ ! -f "$db_archive" ]; then
  echo "Database archive not found: $db_archive" >&2
  exit 1
fi

if [ ! -f "$files_archive" ]; then
  echo "Files archive not found: $files_archive" >&2
  exit 1
fi

cd "$SITE_DIR"

if [ ! -f .env ]; then
  echo "Missing ${SITE_DIR}/.env" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
. ./.env
set +a

: "${MYSQL_DATABASE:?MYSQL_DATABASE is required in .env}"
: "${MYSQL_USER:?MYSQL_USER is required in .env}"
: "${MYSQL_PASSWORD:?MYSQL_PASSWORD is required in .env}"
: "${MYSQL_ROOT_PASSWORD:?MYSQL_ROOT_PASSWORD is required in .env}"

if [ "$confirm" != "--yes" ]; then
  echo "This will restore into: $SITE_DIR"
  echo "Database archive: $db_archive"
  echo "Files archive: $files_archive"
  echo
  echo "Current wp-content will be moved aside."
  echo "Current database '${MYSQL_DATABASE}' will be dropped and recreated."
  echo
  read -r -p "Type RESTORE to continue: " answer
  if [ "$answer" != "RESTORE" ]; then
    echo "Restore cancelled"
    exit 1
  fi
fi

workdir="$(mktemp -d)"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
lockfile="${SITE_DIR}/.restore.lock"

cleanup() {
  rm -rf "$workdir"
}
trap cleanup EXIT

(
  flock -n 9 || {
    echo "Another restore is already running" >&2
    exit 1
  }

  gzip -t "$db_archive"
  tar -xzf "$files_archive" -C "$workdir"

  if [ ! -d "${workdir}/wp-content" ]; then
    echo "Archive does not contain wp-content/" >&2
    exit 1
  fi

  echo "Stopping WordPress container..."
  docker compose stop wordpress >/dev/null

  if [ -d wp-content ]; then
    mv wp-content "wp-content.before-restore-${timestamp}"
  fi

  cp -a "${workdir}/wp-content" ./wp-content

  echo "Restoring database..."
  docker compose up -d db >/dev/null
  docker compose exec -T db mariadb -uroot -p"${MYSQL_ROOT_PASSWORD}" <<SQL
DROP DATABASE IF EXISTS \`${MYSQL_DATABASE}\`;
CREATE DATABASE \`${MYSQL_DATABASE}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON \`${MYSQL_DATABASE}\`.* TO '${MYSQL_USER}'@'%';
FLUSH PRIVILEGES;
SQL

  gzip -dc "$db_archive" | docker compose exec -T db mariadb \
    -u"${MYSQL_USER}" \
    -p"${MYSQL_PASSWORD}" \
    "${MYSQL_DATABASE}"

  echo "Starting WordPress container..."
  docker compose up -d wordpress >/dev/null

  docker compose exec -T wordpress chown -R www-data:www-data /var/www/html/wp-content >/dev/null

  echo "Restore complete"
  echo "Previous wp-content backup, if present: ${SITE_DIR}/wp-content.before-restore-${timestamp}"
) 9>"$lockfile"
