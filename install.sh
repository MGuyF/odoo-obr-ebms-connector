#!/bin/bash

# Script d'installation rapide pour EBMS Connector
# Usage: ./install.sh /chemin/vers/odoo/addons

set -e

ODOO_ADDONS_PATH=${1:-"/opt/odoo/addons"}
MODULE_NAME="ebms_connector"

echo "🔗 Installation du module EBMS Connector"
echo "========================================"

# Vérification du chemin addons
if [ ! -d "$ODOO_ADDONS_PATH" ]; then
    echo "❌ Erreur: Le répertoire addons '$ODOO_ADDONS_PATH' n'existe pas"
    echo "Usage: $0 /chemin/vers/odoo/addons"
    exit 1
fi

# Création du répertoire de destination
DEST_PATH="$ODOO_ADDONS_PATH/$MODULE_NAME"

echo "📁 Copie du module vers: $DEST_PATH"

# Suppression de l'ancienne version si elle existe
if [ -d "$DEST_PATH" ]; then
    echo "🗑️  Suppression de l'ancienne version..."
    rm -rf "$DEST_PATH"
fi

# Copie du module
cp -r "odoo_module" "$DEST_PATH"

echo "✅ Module copié avec succès!"
echo ""
echo "🚀 Prochaines étapes:"
echo "1. Redémarrer Odoo avec: ./odoo-bin -u all -d votre_base"
echo "2. Aller dans Applications > EBMS Connector"
echo "3. Cliquer sur 'Installer'"
echo ""
echo "📖 Voir README.md pour plus de détails"

# Vérification des permissions
chmod -R 755 "$DEST_PATH"

echo "🎉 Installation terminée!"
