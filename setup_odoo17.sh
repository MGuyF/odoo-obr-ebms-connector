#!/bin/bash
set -e

# --- Configuration ---
ODOO_VERSION="17.0"
ODOO_USER="odoo17"
ODOO_PASS="odoo17" # Mot de passe pour l'utilisateur PostgreSQL
ODOO_DB="odoo17"
ODOO_PATH="$HOME/Documents/Manguy/odoo-17"
ODOO_REPO_URL="https://github.com/odoo/odoo"
ODOO_CUSTOM_ADDONS="$ODOO_PATH/custom_addons"
EBMS_MODULE_SRC="$HOME/Documents/Manguy/EBMS_Connector/ebms_connector"
EBMS_MODULE_DEST="$ODOO_CUSTOM_ADDONS/ebms_connector"
PG_VERSION="16" # Adapte si ta version de PostgreSQL est différente

# echo "=== 1. Installation des dépendances système (Odoo, PostgreSQL, PDF) ==="
# sudo apt update
# sudo apt install -y git python3 python3-pip python3.12-venv build-essential wget node-less libldap2-dev libsasl2-dev python3-dev libxml2-dev libxslt1-dev libjpeg-dev libpq-dev libjpeg8-dev liblcms2-dev libblas-dev libatlas-base-dev postgresql wkhtmltopdf

echo "=== 2. Configuration de PostgreSQL ==="
sudo service postgresql start

# Vérifie si l'utilisateur PostgreSQL existe
if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$ODOO_USER'" | grep -q 1; then
    echo "Utilisateur PostgreSQL '$ODOO_USER' déjà existant, création sautée."
else
    echo "Création de l'utilisateur PostgreSQL '$ODOO_USER'..."
    sudo -u postgres createuser --createdb "$ODOO_USER"
fi

echo "Configuration du mot de passe pour '$ODOO_USER'..."
sudo -u postgres psql -c "ALTER USER $ODOO_USER WITH PASSWORD '$ODOO_PASS';"

# Vérifie si pg_hba.conf est déjà configuré
if sudo grep -Eq '^local\s+all\s+all\s+md5' "/etc/postgresql/$PG_VERSION/main/pg_hba.conf"; then
    echo "pg_hba.conf déjà configuré pour md5, modification sautée."
else
    echo "Configuration de l'authentification PostgreSQL (md5)..."
    sudo sed -i "s/local\s*all\s*all\s*peer/local   all             all                                     md5/" "/etc/postgresql/$PG_VERSION/main/pg_hba.conf"
    sudo service postgresql restart
fi

# Crée la base de données si elle n'existe pas
if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$ODOO_DB"; then
    echo "Base de données '$ODOO_DB' déjà existante, création sautée."
else
    echo "Création de la base de données '$ODOO_DB'..."
    sudo -u postgres createdb --owner="$ODOO_USER" "$ODOO_DB"
fi

echo "=== 3. Préparation du code source d'Odoo ==="
mkdir -p "$ODOO_PATH"
if [ ! -d "$ODOO_PATH/odoo" ]; then
    echo "Clonage d'Odoo 17.0..."
    git clone "$ODOO_REPO_URL" --branch "$ODOO_VERSION" --depth 1 "$ODOO_PATH/odoo" || {
        echo "Le clonage a échoué. Télécharge le ZIP depuis $ODOO_REPO_URL, décompresse-le et place le contenu dans '$ODOO_PATH/odoo'."
        exit 1
    }
fi

echo "=== 4. Installation des dépendances Python dans un venv ==="
cd "$ODOO_PATH/odoo"
if [ ! -d "../venv" ]; then
    python3 -m venv ../venv
fi
source ../venv/bin/activate
pip install wheel setuptools
pip install -r requirements.txt

echo "=== 5. Copie du module EBMS Connector ==="
mkdir -p "$ODOO_CUSTOM_ADDONS"
rm -rf "$EBMS_MODULE_DEST"
cp -r "$EBMS_MODULE_SRC" "$EBMS_MODULE_DEST"
echo "Module EBMS Connector copié dans $EBMS_MODULE_DEST"

echo "=== 6. Lancement d'Odoo ==="
# Vérifie si la base est initialisée, sinon ajoute '-i base'
DB_INITIALIZED=$(sudo -u postgres psql -d "$ODOO_DB" -tAc "SELECT 1 FROM information_schema.tables WHERE table_name = 'ir_module_module'")
LAUNCH_PARAMS="-d $ODOO_DB --db_user=$ODOO_USER --db_password=$ODOO_PASS --addons-path=addons,$ODOO_CUSTOM_ADDONS --dev=all"

if [ "$DB_INITIALIZED" != "1" ]; then
    echo "La base de données n'est pas initialisée. Installation du module 'base'..."
    LAUNCH_PARAMS="$LAUNCH_PARAMS -i base"
fi

echo ""
echo "Odoo est prêt. Commande de lancement :"
echo "./odoo-bin --config=/home/gy/Documents/Manguy/odoo-17/odoo/debian/odoo.conf $LAUNCH_PARAMS"
echo "Lancement dans 3 secondes..."
sleep 3

cd "$ODOO_PATH/odoo"
source ../venv/bin/activate
./odoo-bin --config=/home/gy/Documents/Manguy/odoo-17/odoo/debian/odoo.conf $LAUNCH_PARAMS
