#!/bin/sh
set -e

echo "🚀 [GéoFoncier] Démarrage du conteneur en production..."

# Attendre que PostgreSQL / PostGIS réponde si DB_HOST est configuré
if [ -n "$DB_HOST" ]; then
    echo "⏳ [GéoFoncier] Vérification de la connexion à la base de données ($DB_HOST:$DB_PORT)..."
    until python -c "
import socket, sys
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.connect(('$DB_HOST', int('${DB_PORT:-5432}')))
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
"; do
        echo "   ... en attente de la base de données..."
        sleep 2
    done
    echo "✅ [GéoFoncier] Base de données accessible !"
fi

echo "🔄 [GéoFoncier] Exécution des migrations PostGIS..."
python app/manage.py migrate --noinput

echo "🌱 [GéoFoncier] Initialisation / Synchronisation idempotente du RBAC..."
python app/manage.py seed_rbac || true

echo "📦 [GéoFoncier] Collecte des fichiers statiques (WhiteNoise)..."
python app/manage.py collectstatic --noinput --clear || true

echo "✨ [GéoFoncier] Lancement de l'application..."
exec "$@"
