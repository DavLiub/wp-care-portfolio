#!/usr/bin/env bash
set -Eeuo pipefail

umask 077

SITE_DIR="${SITE_DIR:-/opt/sites/wp-care-portfolio}"
SITE_NAME="${SITE_NAME:-wp-care-portfolio}"
BACKUP_ROOT="${BACKUP_ROOT:-/opt/sites/backups/${SITE_NAME}}"

DAILY_KEEP="${DAILY_KEEP:-5}"
WEEKLY_KEEP="${WEEKLY_KEEP:-3}"
MONTHLY_KEEP="${MONTHLY_KEEP:-2}"

usage() {
  cat <<USAGE
Usage: $0 [daily|weekly|monthly|auto]

Retention:
  daily:   keep ${DAILY_KEEP}
  weekly:  keep ${WEEKLY_KEEP}
  monthly: keep ${MONTHLY_KEEP}

auto mode creates:
  monthly on day 01
  weekly on Sunday
  daily otherwise
USAGE
}

kind="${1:-daily}"
case "$kind" in
  daily|weekly|monthly) ;;
  auto)
    day="$(date +%d)"
    weekday="$(date +%u)"
    if [ "$day" = "01" ]; then
      kind="monthly"
    elif [ "$weekday" = "7" ]; then
      kind="weekly"
    else
      kind="daily"
    fi
    ;;
  -h|--help)
    usage
    exit 0
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

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

mkdir -p "${BACKUP_ROOT}/daily" "${BACKUP_ROOT}/weekly" "${BACKUP_ROOT}/monthly"

backup_dir="${BACKUP_ROOT}/${kind}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
db_final="${backup_dir}/database-${timestamp}.sql.gz"
db_temp="${db_final}.tmp"
files_final="${backup_dir}/files-${timestamp}.tar.gz"
files_temp="${files_final}.tmp"
checksums_final="${backup_dir}/checksums-${timestamp}.sha256"
checksums_temp="${checksums_final}.tmp"
lockfile="${BACKUP_ROOT}/.backup.lock"

cleanup() {
  rm -f "$db_temp" "$files_temp" "$checksums_temp"
}
trap cleanup EXIT

(
  flock -n 9 || {
    echo "Another backup is already running" >&2
    exit 1
  }

  echo "Creating ${kind} backup for ${SITE_NAME}"

  if [ "$(docker compose ps -q db | wc -l)" -eq 0 ]; then
    echo "ERROR: MariaDB service is not created. Run docker compose up -d first." >&2
    exit 1
  fi

  if [ "$(docker compose ps -q wordpress | wc -l)" -eq 0 ]; then
    echo "ERROR: WordPress service is not created. Run docker compose up -d first." >&2
    exit 1
  fi

  if [ "$(docker compose ps --status running -q db | wc -l)" -eq 0 ]; then
    echo "ERROR: MariaDB service is not running." >&2
    exit 1
  fi

  if [ "$(docker compose ps --status running -q wordpress | wc -l)" -eq 0 ]; then
    echo "ERROR: WordPress service is not running." >&2
    exit 1
  fi

  echo "Creating database dump..."
  docker compose exec -T db mariadb-dump \
    --single-transaction \
    --quick \
    --routines \
    --triggers \
    --lock-tables=false \
    -u"${MYSQL_USER}" \
    -p"${MYSQL_PASSWORD}" \
    "${MYSQL_DATABASE}" | gzip > "$db_temp"

  gzip -t "$db_temp"
  posts_table="${WORDPRESS_TABLE_PREFIX:-wp_}posts"
  if ! zgrep -q "CREATE TABLE \`${posts_table}\`" "$db_temp"; then
    echo "ERROR: ${posts_table} table was not found in database dump." >&2
    exit 1
  fi
  mv "$db_temp" "$db_final"

  echo "Creating website files archive..."
  tar \
    --exclude='./db' \
    --exclude='./.git' \
    --exclude='./scripts' \
    -czf "$files_temp" \
    -C "$SITE_DIR" \
    docker-compose.yml \
    .env \
    .env.example \
    credentials.private.txt \
    wp-content

  tar -tzf "$files_temp" >/dev/null
  mv "$files_temp" "$files_final"

  sha256sum "$db_final" "$files_final" > "$checksums_temp"
  mv "$checksums_temp" "$checksums_final"

  echo "Created:"
  du -h "$db_final" "$files_final" "$checksums_final"

  case "$kind" in
    daily) keep="$DAILY_KEEP" ;;
    weekly) keep="$WEEKLY_KEEP" ;;
    monthly) keep="$MONTHLY_KEEP" ;;
  esac

  find "$backup_dir" -maxdepth 1 -type f -name 'database-*.sql.gz' \
    -printf '%T@ %p\n' | sort -rn | awk -v keep="$keep" 'NR > keep {print $2}' | while read -r old_db; do
      old_stamp="$(basename "$old_db" | sed -E 's/^database-(.*)\.sql\.gz$/\1/')"
      rm -f \
        "${backup_dir}/database-${old_stamp}.sql.gz" \
        "${backup_dir}/files-${old_stamp}.tar.gz" \
        "${backup_dir}/checksums-${old_stamp}.sha256"
    done

  echo "Retention applied: kept latest ${keep} ${kind} backup set(s)"
) 9>"$lockfile"
