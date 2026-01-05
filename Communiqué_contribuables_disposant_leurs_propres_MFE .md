# SPÉCIFICATIONS TECHNIQUES DE L'INTERFAÇAGE AVEC EBMS
## (Electronic Billing Management System)

**Office Burundais des Recettes (OBR)**  
*"Je suis fier de contribuer à la construction du Burundi"*

---

## COMMISSARIAT GÉNÉRAL
**N/Réf:** 540/92/CG/01/JCM/2023

### COMMUNIQUÉ AUX CONTRIBUABLES DISPOSANT DE LEURS PROPRES SYSTÈMES DE FACTURATION ÉLECTRONIQUE

Dans le cadre de la mise en place du système de facturation électronique, l'Office Burundais des Recettes (OBR) porte à la connaissance des contribuables utilisant leurs propres systèmes de facturation qu'il a mis à jour le document des spécifications techniques d'interfaçage avec le système EBMS.

Cette mise à jour concerne principalement une fonctionnalité dont le rôle est d'accuser réception lors de l'ajout d'une facture dans le système EBMS et l'ajout de nouvelles taxes selon la nouvelle loi budgétaire 2023-2024.

Ce document mis à jour est disponible sur le site web de l'OBR (www.obr.bi) et peut être également obtenu auprès des directions ayant la gestion des contribuables dans leurs attributions.

**Un délai de trente (30) jours calendaires est accordé pour terminer les adaptations nécessaires.** Après ce délai, l'ancien lien qui permettait l'ajout des factures dans le système EBMS sans la fonction d'accuser réception ne sera plus disponible.

Bujumbura, le 28/11/2023

Jean Claude MANIRAKIZA  
Commissaire Général

---

## VERSION DU DOCUMENT

| Date | Version | Auteur | Description |
|------|---------|--------|-------------|
| 15/12/2021 | V 0.1 | OBR | Création du document |
| 11/05/2022 | V 0.2 | OBR | Mise à jour du document |
| 24/11/2022 | V 0.3 | OBR | Mise à jour du document |
| 16/03/2023 | V 0.4 | OBR | Mise à jour - Ajout de la fonction d'envoi des mouvements de stock |
| 28/11/2023 | V 0.5 | OBR | Mise à jour:<br>- Ajout d'une réponse pour accuser réception des factures par le système EBMS<br>- Ajout des nouvelles taxes de la loi budgétaire 2023-2024 |

**Note:** Ce document est la propriété intellectuelle de l'Office Burundais des Recettes (OBR). Il est strictement interdit de le modifier, le copier, le reproduire ou le publier à moins d'y avoir été expressément autorisé par l'OBR.

---

## TABLE DES MATIÈRES

I. INTRODUCTION  
II. COMMENT FAIRE L'INTÉGRATION  
III. MÉTHODE D'AUTHENTIFICATION (login)  
IV. MÉTHODE DE VÉRIFICATION DE FACTURE (getInvoice)  
V. MÉTHODE D'AJOUT DE FACTURE (addInvoice)  
VI. MÉTHODE DE VÉRIFICATION DU NIF (CheckTIN)  
VII. MÉTHODE D'ANNULATION DE FACTURE (cancelInvoice)  
VIII. MÉTHODE D'AJOUT DE MOUVEMENTS DE STOCK (AddStockMovement)  
IX. CODES DE STATUTS

---

## ABRÉVIATIONS ET SIGLES

- **API:** Application Programming Interface
- **eBMS:** Electronic Billing Management System
- **FA:** Facture d'avoir
- **FN:** Facture Normale
- **HTTP:** Hypertext Transfer Protocol
- **HTVA:** Hors Taxe sur la Valeur Ajoutée
- **IP:** Internet Protocol
- **JSON:** JavaScript Object Notation
- **NIF:** Numéro d'Identification Fiscal
- **OBR:** Office Burundais des Recettes
- **PFL:** Prélèvement Forfaitaire Libératoire
- **PU:** Prix Unitaire
- **Q:** Quantité
- **RC:** Remboursement de Caution
- **REST:** Representational State Transfer
- **RHF:** Réduction Hors Facturation
- **RSA:** Algorithme de cryptage asymétrique (inventé par Ronald Rivest, Adi Shamir et Leonard Adleman)
- **SHA-256:** Secure Hash Algorithm
- **TC:** Taxe de Consommation
- **TTC:** Toutes Taxes Comprises
- **TVAC:** Taxe sur la Valeur Ajoutée Comprise
- **URL:** Uniform Resource Locator

---

## I. INTRODUCTION

Les dispositions légales, en l'occurrence l'article 47 de la loi n° 1/10 du 16 novembre 2020 portant modification de la loi N° 1/12 du 19 juillet 2013 portant révision de la loi N°1/02 du 17 février 2009 portant institution de la Taxe sur la Valeur Ajoutée « TVA » ; l'article 40 de la loi N°1/14 du 24 décembre 2020 portant modification de la loi N°1/02 du 24 janvier 2013 relative aux impôts sur les revenus ; l'article 112 de la loi n°1/20 du 25 juin 2021 portant fixation du budget général de la République du Burundi pour l'exercice 2021/2022 ainsi que l'Ordonnance du Ministre ayant les finances dans ses attributions n°540/48 du 24/01/2022 portant détermination des conditions d'obtention et d'utilisation de la machine de facturation électronique obligent les contribuables d'utiliser une machine de facturation électronique agréée par l'OBR.

Ce faisant, dans le cadre de mise en application desdites dispositions, il a été demandé aux contribuables possédant leurs propres systèmes de facturation électroniques de procéder aux adaptations nécessaires afin qu'ils puissent permettre le transfert des données en temps réel vers les serveurs de l'OBR.

À cet effet, l'OBR a mis en place un système de gestion de la facturation électronique (eBMS) et des services web (API).

Ce document présente donc les modalités qui définiront les opérations et la structure des données qui seront échangées via l'interface eBMS.

---

## II. COMMENT FAIRE L'INTÉGRATION

Cette interface utilise la technologie des services Web et est implémentée en tant que serveur. Cela signifie que l'autre partie doit être implémentée en tant que client de ce service Web pour l'utiliser.

Les services Web utilisent la technologie REST. Toutes les méthodes présentées dans ce document envoient les informations avec la méthode POST.

L'envoi des factures doit se faire en temps réel. C'est-à-dire, qu'à chaque fois qu'une facture est émise dans le système client (le système du contribuable) pour impression, une copie de la même facture doit être envoyée via les services web à l'administration fiscale. En cas d'échec, pour une raison ou une autre, le système doit l'enregistrer et continuer à essayer de la renvoyer jusqu'à ce que la facture soit bien reçue par l'administration fiscale. Une réponse en cas de succès ou d'échec est retournée au client ainsi qu'un message explicatif. Un identifiant de la facture doit être ajoutée, en clair sur chaque facture avant son impression. Le format de cet identifiant est décrit dans ce document. Cet identifiant est généré par le système du contribuable (système client).

### II.1. FACTURATION

#### II.1.1 TYPE DE FACTURE

Les types de factures ou documents acceptés par le système sont les suivants:

##### a. FACTURE NORMALE (FN)

C'est une facture ordinaire de vente. Les contribuables sont libres de choisir leur propre format de numérotation mais la taille du numéro de facture ne doit pas dépasser 30 caractères.

Lorsqu'une facture est annulée (notamment en cas d'erreur ou de retour des marchandises), une autre facture doit être établie en remplacement de la première et doit avoir la référence de la facture qu'elle remplace.

Notons que la première facture n'est pas à supprimer. Un champ nommé **« cancelled_invoice_ref »** a été ajouté à cet effet.

S'il n'y a pas nécessité de créer une nouvelle facture, vous pouvez juste annuler la facture avec la méthode **« cancelInvoice »**.

##### b. FACTURE D'AVOIR (FA)

La facture d'avoir (note de crédit) peut être utilisée dans différentes situations. Elle peut intervenir notamment:

- **En cas d'erreur sur la facture:** si vous vous êtes trompé sur une facture qui a déjà été envoyée à votre client, il vous faut impérativement en émettre une nouvelle afin de comptabiliser la différence de montant.  
  *Par exemple, si vous avez facturé 550 euros de marchandise au lieu de 500 euros. La facture d'avoir fera mention des 50 euros de trop-perçu.*

- **En cas de retour de marchandise:** si un client n'est pas satisfait de la marchandise reçue, et souhaite la renvoyer, il peut faire une demande d'avoir sur facture. Il faut alors émettre une facture d'avoir pour annuler comptablement le paiement réalisé.

- **En cas de geste commercial:** il peut être utile de faire bénéficier d'une remise à un client (pour le fidéliser ou pour compenser une erreur de votre part), d'un rabais, une ristourne périodique ou un escompte.

- **En cas de réduction hors facture** faite au client c'est-à-dire après que la vente ait lieu, pour constater cette réduction.

Pour chaque cas, l'on doit spécifier quel type de facture d'avoir il s'agit (erreur, retour marchandises, rabais, remise ou ristourne) dans le champ **« cn_motif »** prévu à cet effet. Il faut aussi fournir le numéro de facture qu'elle concerne en référence dans le champ **« invoice_ref »**.

Le montant de la facture d'avoir ne doit pas être supérieur au montant de la facture dont il fait objet.

##### c. REMBOURSEMENT CAUTION (RC)

En cas de remboursement d'une caution sur une facture, un nouveau document est créé pour constater le remboursement. Un champ **« invoice_ref »** a été ajouté pour référencer le numéro de la facture dont le remboursement concerne.

**N.B.:** Un champ **« invoice_type »** permet de distinguer une facture normale de vente normale (FN), une facture d'avoir (FA) ou un document de remboursement de caution (RC). Chaque type de facture ou document doit avoir une numérotation différente des autres types de facture et constituée d'une séquence de chiffre suivant un ordre chronologique, continue et sans rupture.

#### II.1.2 ACCUSÉ DE RÉCEPTION

Lorsqu'une facture arrive dans le système eBMS, ce dernier génère un message de confirmation et une signature électronique. Ces informations sont stockées dans le système eBMS et doivent être stockées en même temps par le système du contribuable comme accusé de réception.

Le processus va se dérouler comme suit:

- Lorsque le système du contribuable envoie une facture, il reçoit en retour une réponse selon que la facture a été ajoutée ou pas dans le système eBMS;

- **En cas d'échec,** il reçoit un code http et un message décrivant la raison de l'échec;

**Exemple:**

```json
Status: 400
{
  "success": false,
  "msg": "Le format de la chaine de caractère JSON est invalide."
}
```

- **En cas de succès,** le système du contribuable reçoit une réponse avec le code http 200 qui veut dire succès de l'opération, la variable **« success »** avec une valeur **« true »**, un message de succès dans le champ **« msg »**, le message de confirmation dans le champ **« result »** ainsi qu'une signature électronique dans le champ **« electronic_signature »**.

- Le champ **« result »** contient les informations suivantes:
  - Le numéro de la facture envoyée;
  - Le numéro de référence attribué à la facture dans la base de données de l'OBR;
  - La date d'enregistrement au format **« AAAA-MM-JJ HH:MM:SS »**;

- La signature électronique, qui est le contenu du champ **« result »** qui est:
  - Haché en utilisant l'algorithme de hachage SHA256;
  - Crypté avec l'algorithme de cryptage RSA avec une clé privée;
  - Encodé en base64 et envoyé dans le champ **« electronic_signature »**;

**Exemple:**

```json
Status: 200
{
  "success": true,
  "msg": "La facture a été ajoutée avec succès!",
  "result": {
    "invoice_number": "0001/2021",
    "invoice_registered_number": "4530253",
    "invoice_registered_date": "2023-05-12 10:04:23"
  },
  "electronic_signature": "9a2a3f27dd833f6f4a069235ce165723be1b7340"
}
```

Les systèmes des contribuables doivent enregistrer automatiquement cette signature électronique cryptée ainsi que le message envoyé par le système eBMS. Cette signature servira de preuve que la facture envoyée a été bien reçue par l'OBR. Lorsque ce numéro n'a pas été reçu, cela veut dire que le message n'a pas été reçue par l'OBR. Il appartient alors au système du contribuable de renvoyer automatiquement la facture, tout comme cela est fait pour tout autre problème d'envoi.

Lorsque cela s'avère nécessaire, la vérification s'effectuera comme suit:
- Décoder avec base64 la chaine de caractère se trouvant dans le champ **« electronic_signature »** pour avoir le message crypté;
- Décrypter le message obtenu avec l'algorithme de cryptage RSA et une clé publique que l'OBR va leur fournir préalablement. Une clé publique générée chaque année ou chaque fois que de besoin sera envoyé à l'adresse email que le contribuable va fournir ou sera téléchargeable sur le site web de l'OBR (www.obr.gov.bi). La période de validité de la clé publique sera spécifiée en précisant la date et l'heure de début et de fin de validité;
- Hacher le message contenu dans le champ **« result »** (tout le contenu sous format json. Exemple: `{"invoice_number": "0001/2021", "invoice_registered_number": "4530253","invoice_registered_date":"2023-05-12 10:04:23"}`) avec l'algorithme de hachage SHA-256;
- Comparer le résultat du décodage et du décryptage du champ **« electronic_signature »** avec le résultat du hachage du champ **« result »**;
- Si les valeurs deux sont identiques, c'est-à-dire que signature et les données sont valides. En d'autres mots, c'est-à-dire que l'OBR a bien reçu la facture et l'a enregistré avec le numéro d'enregistrement et à la date fournie dans le message.

### II.2. STOCK

Les systèmes des contribuables doivent permettre d'envoyer les données de stock relatives aux marchandises destinées à la vente chaque fois qu'il y a une opération d'entrée ou de sortie de stock. Les mouvements de stock peuvent être de types suivants:

**ENTRÉES:**
- **Entrées Normales (EN):** ce sont des entrées qui proviennent des approvisionnements de marchandises;
- **Entrées en cas de Retour de marchandise (ER):** ce sont des entrées provenant des retours de marchandises par les clients de l'entreprise;
- **Entrées d'Inventaire (EI):** il s'agit des quantités réelles de stock constaté lors des inventaires physiques;
- **Entrées d'Ajustement (EAJ):** ce sont des entrées de stock pour faire l'ajustement entre le stock réel et le stock théorique (stock se trouvant dans le système);
- **Entrées Transfert des articles (ET):** il s'agit d'un transfert d'articles entre deux ou plusieurs stocks du même contribuable;
- **Entrées Autres (EAU):** ce sont d'autres entrées qui peuvent survenir et qui ne sont pas citées;

**SORTIES:**
- **Sorties Normales (SN):** ce sont des sorties normales de ventes de marchandises;
- **Sorties Perte (SP):** ce sont des sorties de stock en cas de perte de marchandises (il doit y avoir un document officiel de constatation de perte);
- **Sorties Vol (SV):** ce sont des sorties des articles qui ont été volés (il doit y avoir un document officiel de constatation de vol);
- **Sorties Désuétudes/périmées ou obsolètes (SD):** ce sont des sorties de marchandises qui sont devenues désuète/périmées ou obsolètes;
- **Sorties Casse (SC):** ce sont des sorties de marchandises en cas de casse;
- **Sorties Ajustement (SAJ):** il s'agit des sorties de stock pour faire l'ajustement entre le stock réel et le stock dans le système;
- **Sorties Transfert (ST):** il s'agit d'un transfert d'articles entre deux ou plusieurs stocks du même contribuable;
- **Sortie Autres (SAU):** ce sont d'autres types de sorties qui ne sont pas citées dans ce document.

Pour les entrées et les sorties qui ne sont pas normales (achat/production ou ventes) un champ **« item_movement_description »** a été prévu pour ajouter une description afin de donner d'autres précisions si nécessaire.

En cas de retour marchandise, un champ **« item_movement_invoice_ref »** a été mise en place pour spécifier le numéro de la facture concernée.

### II.3. AUTHENTIFICATION

Pour toute transaction du client vers le serveur, une clé d'authentification valide doit être envoyé en entête. Sinon un message d'erreur sera envoyé. La clé est obtenue via une fonction d'authentification en fournissant un identifiant et un mot de passe fournis par l'administration fiscale. Ces identifiants sont obtenus en adressant une demande à l'email: **facturation.electronique@obr.gov.bi** ou en appelant au numéro **22 28 24 59**.

Les liens qui se trouvent dans ce document sont des liens permettant l'accès sur les serveurs de tests. Les liens vers le serveur de production vous seront communiqué si les tests sont concluants et un autre identifiant et un mot de passe vous seront fournis afin de se connecter sur le serveur de production.

Les données qui sont utilisées dans ce document sont des données d'exemple. Il faut les remplacer par les vôtres lors de l'implémentation.

### II.4. FONCTIONS DISPONIBLES

L'interface eBMS a des fonctions répertoriées dans le tableau ci-dessous:

| Méthode | URL | Usage |
|---------|-----|-------|
| POST | https://ebms.obr.gov.bi:9443/ebms_api/login/ | Génère un jeton pour accéder aux autres fonctions |
| POST | https://ebms.obr.gov.bi:9443/ebms_api/getInvoice/ | Permet d'obtenir les détails d'une facture |
| POST | https://ebms.obr.gov.bi:9443/ebms_api/addInvoice_confirm/ | Permet d'ajouter une facture à la base de données |
|  | **N.B.:** Le nouveau lien ci-haut remplace l'ancien sans accusé de réception en dessous |  |
|  | https://ebms.obr.gov.bi:9443/ebms_api/addInvoice/ |  |
| POST | https://ebms.obr.gov.bi:9443/ebms_api/checkTIN/ | Permet de vérifier si un NIF donné est valide ou non |
| POST | https://ebms.obr.gov.bi:9443/ebms_api/cancelInvoice/ | Permet d'annuler une facture |
| POST | https://ebms.obr.gov.bi:9443/ebms_api/AddStockMovement/ | Permet d'ajouter les mouvements de stock |

---

## PARAMÈTRES JSON

Toutes les demandes et réponses sont au format JSON. Ci-après les détails sur les paramètres JSON:

| Paramètre | Type | Taille | Description |
|-----------|------|--------|-------------|
| username | Chaine de caractères | 30 | Nom d'utilisateur du contribuable |
| password | Chaine de caractères | 30 | Le mot de passe du contribuable |
| success | Booléen | - | Renvoie vrai si l'opération a réussi et faux dans les autres cas |
| msg | Texte | - | Le message de retour |
| result | Texte | - | Contient le résultat de l'opération |
| electronic_signature | Text | - | Champ contenant la signature électronique envoyé au contribuable lors de la réception de la facture |
| invoice_registered_number | Texte | - | Numéro d'enregistrement de la facture dans la base de données eBMS |
| invoice_registered_date | Date heure | - | Date d'enregistrement de la facture dans l'eBMS. Format: "YYYY-MM-DD hh:mm:ss" |
| token | Chaine de caractères | - | Un jeton (clé) à envoyer dans l'en-tête pour d'autres appels d'API |
| invoice_number | Chaine de caractères | 30 | Le numéro de la facture |
| invoice_date | Date heure | - | Date de facturation. Format: "YYYY-MM-DD hh:mm:ss" |
| invoice_type | Chaine de caractères | 5 | Type de facture. La facture peut être:<br>- "FN" Facture normale<br>- "FA" Facture d'Avoir<br>- "RC" Remboursement caution<br>- "RHF" Réduction Hors Facture |
| invoices | Chaine de caractères | - | Un tableau qui contient les factures retournées lors d'une recherche la fonction getInvoice |
| tp_type | Chaine de caractères | 5 | Type de contribuable. Valeur "1" pour personne physique et "2" pour personne morale |
| tp_name | Chaine de caractères | 100 | Nom et prénom pour personne physique ou nom commercial pour personne morale |
| tp_TIN | Chaine de caractères | 30 | NIF du contribuable |
| tp_trade_number | Chaine de caractères | 20 | Le numéro du registre de commerce du contribuable |
| tp_postal_number | Chaine de caractères | 20 | Boite postale du contribuable |
| tp_phone_number | Chaine de caractères | 20 | Numéro de téléphone du contribuable |
| tp_address_province | Chaine de caractères | 50 | Adresse du contribuable: Province |
| tp_address_commune | Chaine de caractères | 50 | Adresse du contribuable: commune |
| tp_address_quartier | Chaine de caractères | 50 | Adresse du contribuable: quartier |
| tp_address_avenue | Chaine de caractères | 50 | Adresse du contribuable: avenue |
| tp_address_rue | Chaine de caractères | 50 | Adresse du contribuable: rue |
| tp_address_number | Chaine de caractères | 10 | Adresse du contribuable: numéro |
| vat_taxpayer | Chaine de caractères | 3 | Assujetti a la TVA. Valeur: "0" pour un non assujetti ou "1" pour un assujetti |
| ct_taxpayer | Chaine de caractères | 3 | Assujetti à la taxe de consommation. Valeur: "0" pour un non assujetti ou "1" pour un assujetti |
| tl_taxpayer | Chaine de caractères | 3 | Assujetti au prélèvement forfaitaire libératoire. Valeur: "0" pour un non assujetti ou "1" pour un assujetti |
| tp_fiscal_center | Chaine de caractères | 20 | Le centre fiscal du contribuable. Compléter par:<br>- "DGC" pour Direction des Grands contribuables;<br>- "DMC" pour Direction des Moyens Contribuables;<br>- "DPMC" pour Direction des Petits et Micro Contribuables. |
| tp_activity_sector | Chaine de caractères | 250 | Le secteur d'activité du contribuable |
| tp_legal_form | Chaine de caractères | 50 | La forme juridique du contribuable |
| payment_type | Chaine de caractères | 4 | Type de paiement de la facture. Valeur:<br>"1" en espèce<br>"2" banque<br>"3" à crédit<br>"4" autres |
| customer_name | Chaine de caractères | 100 | Nom du client |
| customer_TIN | Chaine de caractères | 50 | NIF du client, s'il en a. **N.B.:** Ce champ n'est pas obligatoire dans la fonction addInvoice mais si le NIF est fourni, il doit être valide. La fonction checkTIN permet de faire une vérification de la validité du NIF |
| customer_address | Chaine de caractères | 100 | Adresse du client |
| vat_customer_payer | Chaine de caractères | 3 | Si le client est assujetti à la TVA. Valeur: "0" pour un non assujetti ou "1" pour un assujetti |
| cancelled_invoice_ref | Chaine de caractères | 4 | Numéro de référence de la facture annulée |
| cancelled_invoice | Chaine de caractères | - | Montre qu'une facture est considérée comme annulée ou pas. Il peut avoir les valeurs suivantes:<br>- "N" si la facture n'est pas annulée;<br>- "Y" si la facture a été annulée. |
| invoice_ref | Chaine de caractères | 30 | Numéro de référence de la facture qui fait objet d'une facture d'avoir ou de remboursement caution |
| cn_motif | Chaine de caractères | 500 | Motif de création de la facture d'avoir |
| invoice_identifier | Chaine de caractères | 90 | Identifiant unique de la facture. Format:<br>`<NIF du contribuable>/<Identification du système du contribuable>/<date, heure, minute, seconde de facturation>/<Numéro facture>`<br>Ex: 400020202/ws400000000100001/20220110173045/00001<br>**N.B.:** L'identifiant système est celui fourni avec un mot de passe afin de se connecter au système |
| invoice_currency | Chaine de caractères | 5 | Type de monnaie de facturation. Les choix sont: "BIF", "USD" et "EUR". Le champ n'est pas obligatoire. Si rien n'est envoyé, le système considère par défaut que c'est le "BIF" |
| invoice_items | Chaine de caractères | - | Tableau qui contient l'ensemble des articles sur la facture |
| item_designation | Chaine de caractères | 500 | Désignation de l'article |
| item_quantity | Float | - | Quantité (Q) de l'article |
| item_price | Double | - | Le prix unitaire (PU) de l'article |
| item_ct | Double | - | Taxe de Consommation (TC) |
| item_tl | Double | - | Prélèvement Forfaitaire Libératoire (PFL) |
| item_tsce_tax | Double | - | Taxe spécifique des services à valeur ajoutée dans les consommations électroniques. **N.B.:** Se comporte comme la TC |
| item_ott_tax | Double | - | Over The Top. **N.B.:** Se comporte comme la TC |
| item_price_nvat | Double | - | Prix HTVA = (PU x Q) + TC |
| vat | Double | - | Montant de la TVA = (Prix HTVA x taux de la TVA) |
| item_price_wvat | Double | - | Prix de vente TVAC = (Prix HTVA + Montant TVA) |
| item_total_amount | Double | - | Prix de Vente total (montant TTC) = (TVAC + PFL) |
| taxpayer | Chaine de caractères | - | Tableau contenant les informations du contribuable qui seront retournées avec la méthode checkTIN |
| system_id | Chaine de caractères | 100 | Identification du système du contribuable |
| item_code | Chaine de caractères | 30 | Code de l'article |
| item_measurement_unit | Chaine de caractères | 20 | Unité de mesure de l'article |
| item_cost_price | Double | - | Prix unitaire de revient (coût de revient) lors de l'approvisionnement ou lors de la vente |
| item_cost_price_currency | Chaine de caractères | 5 | Type de monnaie du coût de revient lors de l'approvisionnement ou lors de la vente. Les choix sont: "BIF", "USD" et "EUR". Le champ n'est pas obligatoire. Si rien n'est envoyé, le système considère par défaut que c'est le "BIF" |
| item_movement_type | Chaine de caractères | 5 | Type d'entrée ou de sortie. Les valeurs acceptées sont:<br>- "EN": Entrée Normales<br>- "ER": Entrée Retour marchandises<br>- "EI": Entrée Inventaire<br>- "EAJ": Entrée Ajustement<br>- "ET": Entrée Transfert<br>- "EAU": Entrée Autres<br>- "SN": Sortie Normales<br>- "SP": Sortie Perte<br>- "SV": Sortie Vol<br>- "SD": Sortie Désuétude<br>- "SC": Sortie Casse<br>- "SAJ": Sortie Ajustement<br>- "ST": Sortie Transfert<br>- "SAU": Sortie Autres |
| item_movement_invoice_ref | Chaine de caractères | 30 | Reference de la facture en cas de retour d'article |
| item_movement_description | Chaine de caractères | 500 | Description sur le mouvement de stock pour plus de détails |
| item_movement_date | Date heure | - | La date de génération du mouvement de stock. Format: "YYYY-MM-DD hh:mm:ss" |

**N.B.:** Veuillez ne pas envoyer la valeur null pour tous les champs dans le JSON. Mettez plutôt une chaîne de caractère vide ("").

---

## III. MÉTHODE D'AUTHENTIFICATION (login)

Lorsque le système du contribuable souhaite communiquer avec le système eBMS, il établit une connexion à l'API eBMS en appelant cette méthode et en transmettant les informations d'identification de l'utilisateur. La méthode d'authentification vérifiera les informations d'identification et émettra un **« jeton d'accès »** dans la réponse au format JSON. Ce jeton d'accès sera ensuite utilisé dans les appels de méthodes API suivants à partir du client. Le jeton d'accès aura l'heure d'émission et l'heure d'expiration stockées dans la base de données API (60 secondes). Une fois le jeton expiré, le client doit refournir des informations d'identification utilisateur et obtenir un nouveau jeton. Un utilisateur peut se connecter à partir d'une adresse IP différente en même temps et recevra des jetons différents pour chaque connexion.

### Comment se connecter et obtenir le jeton généré:

**Requête:**

| Type | Valeurs |
|------|---------|
| Protocol HTTP de méthode | POST |
| URL | https://ebms.obr.gov.bi:9443/ebms_api/login/ |
| En-tête | Content-Type: application/json |
| Corps de la requête | `{"username":"<votre nom d'utilisateur système>", "password":"<votre mot de passe>"}` |
| Champs obligatoires | username, password |

**Réponses:**

```json
// Succès (200)
{
  "success": true,
  "msg": "Opération réussie",
  "result": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6InJveSIsImV4cCI6MTYzOTU3MzU4Mn0.wfx51HOOynLszuk3nWmtyZRhIZIZ3DthDSOHW_HohU"
  }
}
```

**Codes d'erreur:**

- **400:** `{"success": false, "msg": "Veuillez fournir un nom d'utilisateur."}`
- **400:** `{"success": false, "msg": "Veuillez fournir un mot de passe."}`
- **400:** `{"success": false, "msg": "Veuillez envoyer les données en utilisant la méthode POST."}`
- **400:** `{"success": false, "msg": "Le format de la chaine de caractère JSON est invalide."}`
- **401:** `{"success": false, "msg": "Nom d'utilisateur ou mot de passe incorrect."}`
- **500:** `{"success": false, "msg": "Quelque chose a mal tourné. Veuillez réessayer plus tard."}`

---

## IV. MÉTHODE DE VÉRIFICATION DE FACTURE (getInvoice)

Cette méthode sera utilisée pour obtenir les informations d'une facture. Le système du contribuable enverra l'identifiant d'une facture à la méthode. En retour, il obtiendra les détails de la facture, s'il existe.

**Requête:**

| Type | Valeurs |
|------|---------|
| Protocol HTTP de méthode | POST |
| URL | https://ebms.obr.gov.bi:9443/ebms_api/getInvoice/ |
| En-tête | Authorization: Bearer `<votre_token>` |
| Corps de la requête | `{"invoice_identifier":"4701354861/ws470135486100027/20220211120214/01929"}` |
| Champs obligatoires | invoice_identifier |

**N.B.:** Pour accéder à la méthode, vous devez envoyer un en-tête avec un jeton valide. Le jeton est envoyé dans la variable nommée **« Authorization »**. La valeur de cette variable est composée par un mot clé **« Bearer »** et le jeton séparé par un espace.

**Réponses:**

```json
// Succès (200)
{
  "success": true,
  "msg": "Opération réussie",
  "result": {
    "invoices": [
      {
        "invoice_number": "01929",
        "invoice_date": "2022-02-11 12:02:14",
        "invoice_type": "FN",
        "tp_type": "1",
        "tp_name": "NDIKUMANA JEAN MARIE",
        "tp_TIN": "4701354861",
        "tp_trade_number": "3333",
        "tp_postal_number": "3256",
        "tp_phone_number": "70959595",
        "tp_address_province": "BUJUMBURA",
        "tp_address_commune": "BUJUMBURA",
        "tp_address_quartier": "GIKUNGU",
        "tp_address_avenue": "MUYINGA",
        "tp_address_rue": "NYAMBUYE",
        "tp_address_number": "",
        "vat_taxpayer": "1",
        "ct_taxpayer": "0",
        "tl_taxpayer": "0",
        "tp_fiscal_center": "DGC",
        "tp_activity_sector": "SERVICE MARCHAND",
        "tp_legal_form": "suprl",
        "payment_type": "1",
        "invoice_currency": "BIF",
        "customer_name": "NGARUKIYINTWARI WAKA",
        "customer_TIN": "4401202020",
        "customer_address": "KIRUNDO",
        "vat_customer_payer": "1",
        "cancelled_invoice_ref": "",
        "invoice_ref": "",
        "cn_motif": "",
        "invoice_identifier": "4701354861/ws470135486100027/20220211120214/01929",
        "invoice_items": [
          {
            "item_designation": "Article 1",
            "item_quantity": "10",
            "item_price": "500",
            "item_ct": "0",
            "item_tl": "0",
            "item_ott_tax": "0",
            "item_tsce_tax": "0",
            "item_price_nvat": "5000",
            "vat": "900",
            "item_price_wvat": "5900",
            "item_total_amount": "5900"
          }
        ]
      }
    ]
  }
}
```

**Codes d'erreur:**

- **403:** `{"success": false, "msg": "La clé API est manquante."}`
- **400:** `{"success": false, "msg": "Le format de la chaine de caractère JSON est invalide."}`
- **400:** `{"success": false, "msg": "Veuillez utiliser la méthode POST pour envoyer les données."}`
- **400:** `{"success": false, "msg": "Veuillez fournir un identifiant de la facture."}`
- **400:** `{"success": false, "msg": "Identifiant de la facture inconnu."}`
- **500:** `{"success": false, "msg": "Quelque chose a mal tourné. Veuillez réessayer plus tard."}`

---

## V. MÉTHODE D'AJOUT DE FACTURE (addInvoice)

Cette méthode sera appelée par les systèmes du contribuable pour ajouter des nouvelles factures dans la base de données eBMS.

**Requête:**

| Type | Valeur |
|------|--------|
| Protocol HTTP de méthode | POST |
| URL | https://ebms.obr.gov.bi:9443/ebms_api/addInvoice_confirm/ |
| En-tête | Authorization: Bearer `<votre_token>` |

**Corps de requête (exemple):**

```json
{
  "invoice_number": "0001/2021",
  "invoice_date": "2021-12-06 07:30:22",
  "invoice_type": "FN",
  "tp_type": "1",
  "tp_name": "NDIKUMANA JEAN MARIE",
  "tp_TIN": "4400773244",
  "tp_trade_number": "3333",
  "tp_postal_number": "3256",
  "tp_phone_number": "70959595",
  "tp_address_province": "BUJUMBURA",
  "tp_address_commune": "BUJUMBURA",
  "tp_address_quartier": "GIKUNGU",
  "tp_address_avenue": "MUYINGA",
  "tp_address_number": "",
  "vat_taxpayer": "1",
  "ct_taxpayer": "0",
  "tl_taxpayer": "0",
  "tp_fiscal_center": "DGC",
  "tp_activity_sector": "SERVICE MARCHAND",
  "tp_legal_form": "suprl",
  "payment_type": "1",
  "invoice_currency": "BIF",
  "customer_name": "NGARUKIYINTWARI WAKA",
  "customer_TIN": "4100022020",
  "customer_address": "KIRUNDO",
  "vat_customer_payer": "1",
  "cancelled_invoice_ref": "",
  "invoice_ref": "",
  "cn_motif": "",
  "invoice_identifier": "4400773244/ws440077324400027/20211206073022/0001/2021",
  "invoice_items": [
    {
      "item_designation": "ARTICLE ONE",
      "item_quantity": "10",
      "item_price": "500",
      "item_ct": "789",
      "item_tl": "123",
      "item_price_nvat": "5789",
      "vat": "1042.02",
      "item_price_wvat": "6831.02",
      "item_total_amount": "6954.02"
    },
    {
      "item_designation": "ARTICLE TWO",
      "item_quantity": "10",
      "item_price": "900",
      "item_ct": "0",
      "item_tl": "0",
      "item_ott_tax": "0",
      "item_tsce_tax": "0",
      "item_price_nvat": "9000",
      "vat": "1620",
      "item_price_wvat": "10620",
      "item_total_amount": "10620"
    }
  ]
}
```

**Champs obligatoires:**
invoice_number, invoice_date, tp_type, tp_name, tp_TIN, tp_trade_number, tp_phone_number, tp_address_commune, tp_address_quartier, vat_taxpayer, ct_taxpayer, tl_taxpayer, tp_fiscal_center, tp_activity_sector, tp_legal_form, payment_type, customer_name, invoice_identifier, invoice_items, item_designation, item_quantity, item_price, item_ct (concerne seulement les assujettis à la taxe de consommation), item_tl (concerne seulement les assujettis au prélèvement forfaitaire), item_ott_tax (concerne seulement les assujettis à la taxe OTT), item_tsce_tax (concerne les assujetis à la taxe spécifique des services à valeur ajoutée dans les communications électroniques), item_price_nvat, vat, item_price_wvat, item_total_amount (concerne les assujettis à la taxe de consommation et au prélèvement forfaitaire)

**N.B.:** Toutes ces mentions doivent figurer sur la facture de vente donnée au client.

**Réponses:**

```json
// Succès (200)
{
  "success": true,
  "msg": "La facture a été ajoutée avec succès!",
  "result": {
    "invoice_number": "0001/2021",
    "invoice_registered_number": "4530253",
    "invoice_registered_date": "2023-05-12 10:04:23"
  },
  "electronic_signature": "9a2a3f27dd833f6f4a069235ce165723be1b7340"
}
```

**Codes d'erreur (exemples):**

- **403:** `{"success": false, "msg": "La clé API est manquante."}`
- **400:** `{"success": false, "msg": "Veuillez fournir tous les champs obligatoires."}`
- **400:** `{"success": false, "msg": "La taille du numéro de la facture excède celle du système (max 30 caractères)"}`
- **400:** `{"success": false, "msg": "Le format de la date de facturation est incorrecte."}`
- **400:** `{"success": false, "msg": "La date de facturation fournie est supérieur à la date actuelle."}`
- **400:** `{"success": false, "msg": "Une facture avec le même numéro de facture existe déjà."}`
- **500:** `{"success": false, "msg": "Quelque chose a mal tourné. Veuillez réessayer plus tard."}`

---

## VI. MÉTHODE DE VÉRIFICATION DU NIF (checkTIN)

Cette méthode vérifie si le NIF (Numéro d'Identification Fiscal) donné dans les paramètres est valide et connu par l'OBR ou non et renvoie le nom du propriétaire du NIF.

**Requête:**

| Type | Valeur |
|------|--------|
| Protocol HTTP de méthode | POST |
| URL | https://ebms.obr.gov.bi:9443/ebms_api/checkTIN/ |
| En-tête | Authorization: Bearer `<votre_token>` |
| Corps de la requête | `{"tp_TIN": "4000202020"}` |
| Champs obligatoires | tp_TIN |

**Réponses:**

```json
// Succès (200)
{
  "success": true,
  "msg": "Opération réussie",
  "result": {
    "taxpayer": [
      {
        "tp_name": "NDIKUMANA Jean Marie"
      }
    ]
  }
}
```

**Codes d'erreur:**

- **403:** `{"success": false, "msg": "La clé API est manquante."}`
- **400:** `{"success": false, "msg": "Veuillez fournir le NIF du contribuable."}`
- **400:** `{"success": false, "msg": "Le format de la chaine de caractère JSON est invalide."}`
- **400:** `{"success": false, "msg": "Veuillez utiliser la méthode POST pour envoyer les données."}`
- **400:** `{"success": false, "msg": "NIF du contribuable inconnu."}`
- **500:** `{"success": false, "msg": "Quelque chose a mal tourné. Veuillez réessayer plus tard."}`

---

## VII. MÉTHODE D'ANNULATION DE FACTURE (cancelInvoice)

Cette méthode sera utilisée pour annuler une facture. Le système du contribuable enverra l'identifiant d'une facture à la méthode. En retour, il obtiendra une réponse disant que l'annulation s'est effectuée avec succès ou pas, avec une explication en message.

### Requête

**Type:** POST  
**URL:** https://ebms.obr.gov.bi:9443/ebms_api/cancelInvoice/

**En-tête:**
```
Authorization: Bearer eyJhbGciOiJIUZI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6InJveSIsImV4cCI6MTU4MjYyMDY10X0.EMTwnkeM5PXV3LEEUveZLcvvi7pQmGUbWMAj2KeR94
```

**Corps de la requête:**
```json
{
  "invoice_identifier": "4701354861/ws470135486100027/20220211120214/01929",
  "cn_motif": "Marchandise non conforme à la commande"
}
```

**Champs obligatoires:**
- invoice_identifier
- cn_motif

### Réponses

**Succès (200):**
```json
{
  "success": true,
  "msg": "La facture avec de l'identifiant 4701354861/ws470135486100027/20220211120214/01929 a été annulée avec succès!"
}
```

**Erreurs:**

**403 - Clé API manquante:**
```json
{
  "success": false,
  "msg": "La clé API est manquante."
}
```

**400 - Format JSON invalide:**
```json
{
  "success": false,
  "msg": "Le format de la chaine de caractère JSON est invalide."
}
```

**400 - Mauvaise méthode:**
```json
{
  "success": false,
  "msg": "Veuillez utiliser la méthode POST pour envoyer les données."
}
```

**400 - Identifiant manquant:**
```json
{
  "success": false,
  "msg": "Veuillez fournir un identifiant de la facture."
}
```

**400 - Identifiant inconnu:**
```json
{
  "success": false,
  "msg": "Identifiant de la facture inconnu."
}
```

**400 - Facture déjà annulée:**
```json
{
  "success": false,
  "msg": "La facture que vous voulez annuler a été déjà annulée..."
}
```

**500 - Erreur serveur:**
```json
{
  "success": false,
  "msg": "Quelque chose a mal tourné. Veuillez réessayer plus tard."
}
```

---

## VIII. MÉTHODE D'AJOUT DE MOUVEMENTS DE STOCK (AddStockMovement)

Cette méthode permet d'ajouter les mouvements de stock, que ce soit des entrées ou des sorties de stock en spécifiant leurs types et une description si nécessaire.

### Requête

**Type:** POST  
**URL:** https://ebms.obr.gov.bi:9443/ebms_api/AddStockMovement/

**En-tête:**
```
Authorization: Bearer eyJhbGciOiJIUZI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6InJveSIsImV4cCI6MTU4MjYyMDY10X0.EMTwnkeM5PXV3LEEUveZLcvvi7pQmGUbWMAj2KeR94
```

**Corps de la requête:**
```json
{
  "system_or_device_id": "ws400000349300131",
  "item_code": "100",
  "item_designation": "Amstel 65cl",
  "item_quantity": "5",
  "item_measurement_unit": "bouteille",
  "item_cost_price": "2000",
  "item_cost_price_currency": "BIF",
  "item_movement_type": "EN",
  "item_movement_invoice_ref": "",
  "item_movement_description": "",
  "item_movement_date": "2022-11-25 08:43:52"
}
```

**Champs obligatoires:**
- device_id
- item_code
- item_designation
- item_quantity
- item_measurement_unit
- item_cost_price
- item_cost_price_currency
- item_movement_type
- item_movement_date

### Réponses

**Succès (200):**
```json
{
  "success": true,
  "msg": "La transaction a été ajoutée avec succès!"
}
```

**Erreurs:**

**403 - Clé API manquante:**
```json
{
  "success": false,
  "msg": "La clé API est manquante.",
  "result": []
}
```

**400 - Champs manquants:**
```json
{
  "success": false,
  "msg": "Veuillez fournir tous les champs obligatoires. Champ(s) manquant(s): ...",
  "result": []
}
```

**400 - Format JSON invalide:**
```json
{
  "success": false,
  "msg": "Le format de la chaine de caractère JSON est invalide.",
  "result": []
}
```

**400 - Mauvaise méthode:**
```json
{
  "success": false,
  "msg": "Veuillez utiliser la méthode POST pour envoyer les données.",
  "result": []
}
```

**400 - Identifiant système incorrect:**
```json
{
  "success": false,
  "msg": "Identifiant système incorrect.",
  "result": []
}
```

**400 - Type de mouvement invalide:**
```json
{
  "success": false,
  "msg": "Veuillez fournir un type de mouvement valide. Le type de mouvement de stock doit être inclu dans les types suivants : EN, ER, EI, EAJ, ET, EAU, SN, SP, SV, SD, SC, SAJ, ST, SAU.",
  "result": []
}
```

**500 - Erreur serveur:**
```json
{
  "success": false,
  "msg": "Quelque chose a mal tourné. Veuillez réessayer plus tard."
}
```

---

## IX. CODES DE STATUTS

Tous les codes d'état sont des codes d'état HTTP standard. Ceux ci-dessous sont utilisés dans cette API.

- **2XX** - Succès d'une sorte ou d'une autre
- **4XX** - Une erreur s'est produite dans la partie du client
- **5XX** - Une erreur s'est produite dans la partie du serveur

### Tableau des codes HTTP

| Code | Statut | Signification |
|------|--------|---------------|
| **200** | OK | Requête traitée avec succès. La réponse dépendra de la méthode de requête utilisée. |
| **201** | Created | Requête traitée avec succès et création d'un document. |
| **202** | Accepted (Request accepted, and queued for execution) | Requête traitée, mais sans garantie de résultat. |
| **400** | Bad request | La requête avait une mauvaise syntaxe ou était impossible à satisfaire. |
| **401** | Authentication failure | Une authentification est nécessaire pour accéder à la ressource. |
| **403** | Forbidden | Le serveur a compris la requête, mais refuse de l'exécuter. Contrairement à l'erreur 401, s'authentifier ne fera aucune différence. Sur les serveurs où l'authentification est requise, cela signifie généralement que l'authentification a été acceptée mais que les droits d'accès ne permettent pas au client d'accéder à la ressource. |
| **404** | Resource not found | Ressource non trouvée. |
| **405** | Method Not Allowed | Méthode de requête non autorisée. |
| **409** | Conflict | La requête ne peut être traitée en l'état actuel. |
| **412** | Precondition Failed | Préconditions envoyées par la requête non vérifiées. |
| **413** | Request Entity Too Large | Traitement abandonné dû à une requête trop importante. |
| **500** | Internal Server Error | Erreur interne du serveur. |
| **501** | Not Implemented | Fonctionnalité réclamée non supportée par le serveur. |
| **503** | Service Unavailable | Service temporairement indisponible ou en maintenance. |

---

**Fait à Bujumbura, le 28/11/2023**

**LE COMMISSAIRE GÉNÉRAL**  
Jean Claude MANIRAKIZA
