#!/usr/bin/env python3
"""
Script de test pour valider la structure du module EBMS Connector
"""

import os
import sys
import ast

def test_module_structure():
    """Test de la structure du module"""
    print("🧪 Test de la structure du module EBMS Connector")
    print("=" * 50)
    
    base_path = "odoo_module"
    required_files = [
        "__manifest__.py",
        "__init__.py",
        "models/__init__.py",
        "models/account_invoice_inherit.py",
        "views/invoice_view.xml",
        "controllers/__init__.py",
        "controllers/main.py",
        "static/description/icon.png",
        "static/description/index.html",
        "data/demo_data.xml"
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = os.path.join(base_path, file_path)
        if os.path.exists(full_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n❌ {len(missing_files)} fichier(s) manquant(s)")
        return False
    else:
        print(f"\n✅ Tous les fichiers requis sont présents!")
        return True

def test_manifest():
    """Test du fichier manifest"""
    print("\n🧪 Test du fichier __manifest__.py")
    print("=" * 35)
    
    try:
        with open("odoo_module/__manifest__.py", 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse le manifest
        manifest = ast.literal_eval(content)
        
        # Tests des champs requis
        required_fields = ['name', 'version', 'depends', 'data']
        for field in required_fields:
            if field in manifest:
                print(f"✅ {field}: {manifest[field]}")
            else:
                print(f"❌ Champ manquant: {field}")
                return False
        
        # Vérifications spécifiques
        if 'account' in manifest['depends']:
            print("✅ Dépendance 'account' présente")
        else:
            print("❌ Dépendance 'account' manquante")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test du manifest: {e}")
        return False

def test_python_syntax():
    """Test de la syntaxe Python"""
    print("\n🧪 Test de la syntaxe Python")
    print("=" * 30)
    
    python_files = [
        "odoo_module/__init__.py",
        "odoo_module/models/__init__.py",
        "odoo_module/models/account_invoice_inherit.py",
        "odoo_module/controllers/__init__.py",
        "odoo_module/controllers/main.py"
    ]
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Compile pour vérifier la syntaxe
            compile(content, file_path, 'exec')
            print(f"✅ {file_path}")
            
        except SyntaxError as e:
            print(f"❌ Erreur de syntaxe dans {file_path}: {e}")
            return False
        except Exception as e:
            print(f"❌ Erreur dans {file_path}: {e}")
            return False
    
    return True

def test_xml_structure():
    """Test basique de la structure XML"""
    print("\n🧪 Test de la structure XML")
    print("=" * 30)
    
    xml_files = [
        "odoo_module/views/invoice_view.xml",
        "odoo_module/data/demo_data.xml"
    ]
    
    for file_path in xml_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Vérifications basiques
            if '<?xml version="1.0"' in content and '<odoo>' in content:
                print(f"✅ {file_path}")
            else:
                print(f"❌ Structure XML invalide dans {file_path}")
                return False
                
        except Exception as e:
            print(f"❌ Erreur dans {file_path}: {e}")
            return False
    
    return True

def main():
    """Fonction principale de test"""
    print("🔗 EBMS Connector - Tests du module")
    print("=" * 40)
    
    tests = [
        test_module_structure,
        test_manifest,
        test_python_syntax,
        test_xml_structure
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Résultats: {passed}/{total} tests réussis")
    
    if passed == total:
        print("🎉 Tous les tests sont passés! Le module est prêt.")
        return 0
    else:
        print("❌ Certains tests ont échoué. Vérifiez les erreurs ci-dessus.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
