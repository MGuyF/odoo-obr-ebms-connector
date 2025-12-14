# Odoo 17 - Connecteur EBMS pour la Conformité Fiscale (OBR Burundi)

## 1. Résumé du Projet

Ce module pour Odoo 17 sert de connecteur entre Odoo et le système de facturation électronique **EBMS (Electronic Billing Machine System)** de l'Office Burundais des Recettes (OBR). Il a été développé pour permettre aux entreprises utilisant Odoo au Burundi de se conformer aux réglementations fiscales en vigueur, en automatisant la déclaration des factures et en garantissant l'intégrité des données via des signatures électroniques.

Ce projet est une démonstration complète de la capacité à étendre les fonctionnalités de base d'Odoo pour répondre à des exigences métier et légales spécifiques, en intégrant une API externe de manière sécurisée et robuste.

---

## 2. Contexte Métier

L'OBR exige que toutes les factures émises par les assujettis à la TVA soient enregistrées en temps réel dans leur système EBMS. Chaque facture validée reçoit en retour une référence unique et une signature électronique qui prouvent son authenticité et sa conformité. Ce processus vise à lutter contre la fraude fiscale et à moderniser la collecte des taxes.

Ce module résout le défi opérationnel pour les utilisateurs d'Odoo en éliminant la double saisie manuelle et les risques d'erreurs associés, tout en fournissant une traçabilité complète directement dans l'interface de facturation.

---

## 3. Fonctionnalités Clés

- **Envoi Automatisé des Factures** : Un bouton "Envoyer à EBMS" sur les factures validées permet de transmettre les données à l'API de l'OBR en un clic.
- **Gestion des Réponses en Temps Réel** : Le module met à jour le statut de la facture dans Odoo en fonction de la réponse de l'API (Succès, Erreur).
- **Stockage des Données de Conformité** : La référence EBMS et la signature électronique renvoyées par l'OBR sont stockées sur la facture Odoo correspondante.
- **Vérification de la Signature Électronique** : Une fonctionnalité permet de vérifier l'intégrité de la signature électronique reçue en utilisant la clé publique de l'OBR, garantissant que la facture n'a pas été altérée.
- **Interface Utilisateur Intégrée** : Des champs et des indicateurs visuels (badges de statut) sont ajoutés de manière non intrusive au formulaire et à la liste des factures pour un suivi facile.
- **Configuration Sécurisée** : Les informations sensibles (URL de l'API, jeton d'authentification) sont stockées de manière sécurisée dans les Paramètres Système d'Odoo, et non en dur dans le code.

---

## 4. Architecture Technique et Concepts Odoo Démontrés

C'est la section la plus importante pour une présentation technique. Ce module illustre la maîtrise des concepts fondamentaux d'Odoo :

#### a. Héritage de Modèle (`_inherit`)
- **Fichier clé** : `models/account_invoice_inherit.py`
- **Concept démontré** : Au lieu de réinventer la roue, le module étend le modèle de base `account.move` d'Odoo. J'ai utilisé l'héritage pour ajouter de nouveaux champs (`ebms_status`, `ebms_reference`, etc.) et de nouvelles méthodes (`action_send_ebms`, etc.) sans modifier une seule ligne du code source d'Odoo. C'est la pierre angulaire du développement modulaire dans Odoo.

#### b. Héritage de Vue (XPath)
- **Fichier clé** : `views/invoice_view.xml`
- **Concept démontré** : J'ai modifié l'interface utilisateur existante en utilisant des expressions XPath. Cela permet d'ajouter des éléments (boutons, champs, badges) à des endroits très précis de la vue formulaire et de la vue liste des factures. Cette technique garantit que les modifications sont compatibles avec d'autres modules et résistantes aux mises à jour d'Odoo.

#### c. Actions de Bouton (`type="object"`)
- **Fichiers clés** : `views/invoice_view.xml` et `models/account_invoice_inherit.py`
- **Concept démontré** : Le lien entre le frontend (XML) et le backend (Python) est réalisé de manière propre. Chaque bouton dans la vue XML avec `type="object"` appelle une méthode Python du même nom sur le modèle. Par exemple, le clic sur le bouton `name="action_send_ebms"` déclenche l'exécution de la méthode `def action_send_ebms(self):`.

#### d. Gestion de la Configuration (`ir.config_parameter`)
- **Concept démontré** : Pour éviter de coder en dur des données sensibles comme les clés d'API, j'ai utilisé le modèle `ir.config_parameter`. Le module lit ces paramètres de manière sécurisée au moment de l'exécution. Cela rend le module configurable et déployable dans différents environnements (test, production) sans modification du code.

#### e. Intégration d'API Externe (`requests`)
- **Fichier clé** : `models/account_invoice_inherit.py` (méthode `_send_to_ebms_api_burundi`)
- **Concept démontré** : Le module communique avec une API REST externe en utilisant la librairie Python `requests`. Il construit une requête HTTP POST avec des en-têtes d'authentification (`Bearer Token`) et un corps de requête en JSON, puis traite la réponse pour mettre à jour Odoo.

#### f. Gestion des Erreurs et Feedback Utilisateur (`UserError`)
- **Concept démontré** : La gestion des erreurs est robuste. Au lieu de provoquer des crashs, le code intercepte les exceptions (erreurs de connexion, réponses invalides de l'API) et lève des `UserError`. Cela arrête la transaction proprement et affiche un message d'erreur clair à l'utilisateur dans une boîte de dialogue, améliorant considérablement l'expérience utilisateur.

---

## 5. Flux de Travail Utilisateur

1.  **Création et Confirmation** : L'utilisateur crée une facture client dans Odoo et la confirme. La facture passe à l'état "Comptabilisé".
2.  **Envoi à EBMS** : L'utilisateur clique sur le bouton "Envoyer à EBMS".
3.  **Communication API** : Le module prépare les données et les envoie à l'API de l'OBR.
4.  **Mise à Jour du Statut** :
    - **Si succès** : Le statut EBMS de la facture passe à "Envoyé", et la référence/signature sont enregistrées.
    - **Si erreur** : Le statut EBMS passe à "Erreur", et le message d'erreur de l'API est affiché.
5.  **(Optionnel) Vérification** : L'utilisateur peut cliquer sur "Vérifier Signature EBMS" pour confirmer l'authenticité de la réponse.

---

## 6. Guide d'Installation et de Configuration

1.  **Installation** : Placer le module `ebms_connector` dans le dossier `custom_addons` d'Odoo.
2.  **Mise à jour de la liste des applications** : Activer le mode développeur, puis aller dans `Apps -> Mettre à jour la liste des applications`.
3.  **Installer le module** : Rechercher "EBMS Connector" et cliquer sur "Installer".
4.  **Configuration** : Aller dans `Configuration -> Technique -> Paramètres Système` et créer les clés suivantes avec les valeurs fournies par l'OBR :
    - `ebms.api_url`
    - `ebms.api_token`
    - `ebms.device_id`
    - `ebms.public_key`
    - `ebms.cancel_url`
    - `ebms.nif_check_url`

Le module est maintenant prêt à être utilisé.
├── controllers/
│   ├── __init__.py
│   └── main.py
└── static/
    └── description/
        ├── icon.png
        └── index.html
```

## 🔧 Développement

### Champs ajoutés au modèle `account.move`

- `ebms_status` : Statut d'envoi EBMS
- `ebms_reference` : Référence retournée par EBMS
- `ebms_sent_date` : Date d'envoi
- `ebms_error_message` : Message d'erreur détaillé

### Méthodes principales

- `action_send_ebms()` : Envoi vers EBMS
- `action_reset_ebms_status()` : Réinitialisation du statut
- `_prepare_ebms_data()` : Préparation des données
- `_send_to_ebms_api()` : Appel API EBMS

## 🐛 Dépannage

### Problèmes courants

1. **Bouton invisible** : Vérifier que la facture est validée et de type client
2. **Erreur d'envoi** : Vérifier la configuration API et la connectivité
3. **Module non visible** : Vérifier l'installation et redémarrer Odoo

### Logs
Les logs EBMS sont disponibles dans les logs Odoo avec le tag `ebms_connector`.

## 📄 Licence

Ce module est distribué sous licence LGPL-3.

## 🔄 Versions

- **v1.0** : Version initiale avec fonctionnalités de base
- Compatible avec **Odoo 17**

---

**Prêt pour démo auprès d'Odoo et partenaires ! 🚀**

---

## Installation locale rapide

```bash
./automate_project_setup.sh
./setup_odoo17.sh
```

- Accédez à http://localhost:8069 et installez le module EBMS Connector via Applications.
