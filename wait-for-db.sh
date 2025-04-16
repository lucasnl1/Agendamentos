#!/bin/bash
set -e

host="$DB_HOST"
port="$DB_PORT"
user="$DB_USER"
dbname="$DB_NAME"

echo "⏳ Aguardando PostgreSQL em $host:$port..."

until PGPASSWORD=$DB_PASS psql -h "$host" -U "$user" -d "$dbname" -c '\q' 2>/dev/null; do
  sleep 2
done

echo "✅ Banco de dados está pronto. Iniciando a aplicação..."
exec "$@"
