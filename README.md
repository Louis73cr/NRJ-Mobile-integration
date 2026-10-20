<p align="center">
  <img src="custom_components/nrjmobile/brand/icon.png" width="140" alt="NRJ Mobile">
</p>

<h1 align="center">NRJ Mobile — intégration Home Assistant</h1>

<p align="center">
  Suivi de consommation et <b>rétablissement du débit data</b> (seuil 500 Go) pour
  l'espace client <a href="https://espace-client.nrjmobile.fr">NRJ Mobile</a>.<br>
  100 % Python, <b>sans MQTT ni broker</b>.
</p>

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge" alt="HACS Custom"></a>
  <img src="https://img.shields.io/github/v/release/Louis73cr/NRJ-Mobile-HACS-integration?style=for-the-badge" alt="Release">
  <img src="https://img.shields.io/badge/Home%20Assistant-2024.1%2B-049CDB?style=for-the-badge&logo=home-assistant&logoColor=white" alt="HA">
</p>

> ⚠️ **Intégration communautaire non officielle** — aucun lien avec NRJ Mobile / Bouygues Telecom. Usage personnel, pour son propre compte.

---

## ✨ Fonctionnalités

Une fois configurée, l'intégration crée **un appareil par ligne** (numéro) avec :

| Entité | Type | Détail |
| --- | --- | --- |
| Data utilisée | `sensor` (Go) | consommation France du cycle en cours |
| Plafond data | `sensor` (Go) | ex. 200 ou 500 Go |
| Data restante | `sensor` (Go) | plafond − utilisée |
| Hors-forfait | `sensor` (€) | montant hors-forfait |
| Seuil data atteint | `binary_sensor` | `on` quand le débit est bridé (≥ plafond) |
| Rétablir le débit web | `button` | déclenche le `FUP_RESET` **uniquement si c'est gratuit** |

L'attribut du capteur *Data utilisée* contient le forfait, le contrat, le prix mensuel et le roaming UE/DOM.

---

## 📦 Installation

### Via HACS (recommandé)

[![Ouvrir dans HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Louis73cr&repository=NRJ-Mobile-HACS-integration&category=integration)

1. Clique le bouton ci‑dessus **ou** : HACS → menu ⋮ (haut‑droite) → **Dépôts personnalisés**
2. URL : `https://github.com/Louis73cr/NRJ-Mobile-HACS-integration` — catégorie : **Integration**
3. Ouvre **NRJ Mobile** dans la liste → **Télécharger**
4. **Redémarre** Home Assistant

### Manuelle

Copie le dossier `custom_components/nrjmobile/` dans le dossier `config/custom_components/` de ton Home Assistant, puis redémarre.

---

## ⚙️ Configuration

[![Ajouter l'intégration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=nrjmobile)

*Paramètres → Appareils et services → **Ajouter une intégration** → « NRJ Mobile »*, puis saisis **l'identifiant et le mot de passe** de ton espace client.

L'intégration se connecte en OIDC/PKCE (Keycloak), récupère toutes tes lignes et interroge la consommation toutes les **30 minutes**.

---

## 🔒 Rétablissement du débit — garde‑fou gratuit

Le backend chiffre un « Frais de restauration » de 12 € **puis applique une remise équivalente → net 0 €**. Le bouton calcule le **coût net** (brut − remise) et **ne soumet la commande que si le net est 0 €**. Si un jour le net était > 0, le bouton échoue proprement **sans rien commander** : aucun prélèvement accidentel.

---

## 🤖 Automatisation — rétablir dès que bridé

```yaml
automation:
  - alias: NRJ Mobile - rétablir le débit auto
    mode: single
    triggers:
      - trigger: state
        entity_id: binary_sensor.ligne_06XXXXXXXX_seuil_data_atteint
        to: "on"
        for: { minutes: 5 }
    conditions:
      - condition: state
        entity_id: binary_sensor.ligne_06XXXXXXXX_seuil_data_atteint
        state: "on"
    actions:
      - action: button.press
        target:
          entity_id: button.ligne_06XXXXXXXX_retablir_le_debit_web
      - delay: { seconds: 30 }
      - action: notify.whatsapp   # ou notify.mobile_app_xxx
        data:
          title: NRJ Mobile
          message: >-
            ✅ Débit data rétabli (0 €). Data restante :
            {{ states('sensor.ligne_06XXXXXXXX_data_restante') }} Go.
```

> Remplace `06XXXXXXXX` par ton numéro (visible dans l'entity‑id généré).

---

## 🛠️ Notes techniques

- Auth OIDC **PKCE** directe (Keycloak `oauth2.nrjmobile.fr`, realm `nrj`, client `wsc-frontend`) ; token ~5 min → ré‑authentification à chaque cycle.
- Appels espacés de 350 ms (anti‑403 WAF).
- `custom_components/nrjmobile/api.py` est autonome : `python3 api.py` lance un self‑check hors‑ligne.
- Icônes de marque locales servies via la [Brands Proxy API](https://contributors.home-assistant.io/blog/2026/02/24/brands-proxy-api/) (HA 2026.3+).

---

## 🏪 Publier dans le store HACS par défaut (optionnel)

Pour que l'intégration apparaisse **sans ajout de dépôt personnalisé**, il faut la soumettre à [`hacs/default`](https://github.com/hacs/default). Prérequis (déjà remplis ici ✅) :

- ✅ `hacs.json` à la racine
- ✅ `custom_components/<domain>/manifest.json` avec `version`, `documentation`, `issue_tracker`, `codeowners`
- ✅ Description du dépôt et **topics** GitHub renseignés
- ✅ Au moins une **release** publiée (versionnée)
- La validation HACS (GitHub Action [`hacs/action`](https://github.com/hacs/action)) et [`hassfest`](https://developers.home-assistant.io/blog/2020/04/16/hassfest/) doivent passer en CI

Ensuite : fork de `hacs/default`, ajouter la ligne `Louis73cr/NRJ-Mobile-HACS-integration` dans le fichier `integration`, et ouvrir une PR. L'inclusion est manuelle et revue par l'équipe HACS.

---

## 📄 Licence

Usage personnel / interopérabilité avec son propre compte NRJ Mobile.
