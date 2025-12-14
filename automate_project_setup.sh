#!/bin/bash
set -e

# 1. Renommer le dossier du module si besoin
if [ -d "odoo_module" ]; then
    echo "Renommage de 'odoo_module' en 'ebms_connector'..."
    mv odoo_module ebms_connector
fi

# 2. Créer le dossier tests si besoin et déplacer le script de test
if [ -f "test_module.py" ]; then
    mkdir -p tests
    mv test_module.py tests/
fi

# 3. Créer le script d'installation local pour Odoo 17
cat > setup_odoo17.sh <<'EOF'
#!/bin/bash
set -e

ODOO_VERSION="17.0"
ODOO_USER="odoo17"
ODOO_DB="odoo17"
ODOO_PATH="$HOME/Documents/Manguy/odoo-17"
ODOO_CUSTOM_ADDONS="$ODOO_PATH/custom_addons"
EBMS_MODULE_SRC="$HOME/Documents/Manguy/EBMS_Connector/ebms_connector"
EBMS_MODULE_DEST="$ODOO_CUSTOM_ADDONS/ebms_connector"

sudo apt update
sudo apt install -y git python3 python3-pip build-essential wget node-less libldap2-dev libsasl2-dev python3-dev libxml2-dev libxslt1-dev libjpeg-dev libpq-dev libjpeg8-dev liblcms2-dev libblas-dev libatlas-base-dev
sudo apt install -y postgresql
sudo service postgresql start

sudo -u postgres psql -c "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '$ODOO_USER') THEN CREATE USER $ODOO_USER WITH CREATEDB; END IF; END $$;"
sudo -u postgres psql -c "SELECT 1 FROM pg_database WHERE datname = '$ODOO_DB'" | grep -q 1 || sudo -u postgres createdb --owner=$ODOO_USER $ODOO_DB

mkdir -p "$ODOO_PATH"
cd "$ODOO_PATH"
if [ ! -d "odoo" ]; then
    git clone https://github.com/odoo/odoo --branch $ODOO_VERSION --depth 1 odoo
fi
cd odoo
python3 -m venv ../venv
source ../venv/bin/activate
pip install wheel
pip install -r requirements.txt

mkdir -p "$ODOO_CUSTOM_ADDONS"
rm -rf "$EBMS_MODULE_DEST"
cp -r "$EBMS_MODULE_SRC" "$EBMS_MODULE_DEST"

cd "$ODOO_PATH/odoo"
source ../venv/bin/activate
./odoo-bin -d $ODOO_DB --addons-path=addons,$ODOO_CUSTOM_ADDONS --dev=all
EOF
chmod +x setup_odoo17.sh

# 4. Mise à jour du README (ajout instructions setup local)
if [ -f "README.md" ]; then
    echo -e '\n---\n\n## Installation locale rapide\n\n```bash\n./automate_project_setup.sh\n./setup_odoo17.sh\n```\n\n- Accédez à http://localhost:8069 et installez le module EBMS Connector via Applications.' >> README.md
fi

echo "\n✅ Structure du projet réorganisée et scripts générés avec succès !"
echo "\n1. Lancez ./automate_project_setup.sh pour préparer le projet.\n2. Ensuite, lancez ./setup_odoo17.sh pour installer et démarrer Odoo 17 en local avec votre module.\n"
