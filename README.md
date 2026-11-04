<p align="center">
  <img src="custom_components/nrjmobile/brand/icon.png" width="140" alt="NRJ Mobile">
</p>

<h1 align="center">NRJ Mobile — intégration Home Assistant</h1>

<p align="center">
  Suivi de consommation et <b>rétablissement du débit data</b> pour
  l'espace client <a href="https://espace-client.nrjmobile.fr">NRJ Mobile</a>.
</p>

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge" alt="HACS Custom"></a>
  <img src="https://img.shields.io/github/v/release/Louis73cr/NRJ-Mobile-integration?style=for-the-badge" alt="Release">
  <img src="https://img.shields.io/github/downloads/Louis73cr/NRJ-Mobile-integration/total?style=for-the-badge&label=installs&color=success" alt="Installs">
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

[![Ouvrir dans HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Louis73cr&repository=NRJ-Mobile-integration&category=integration)

1. Clique le bouton ci‑dessus **ou** : HACS → menu ⋮ (haut‑droite) → **Dépôts personnalisés**
2. URL : `https://github.com/Louis73cr/NRJ-Mobile-integration` — catégorie : **Integration**
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

> ℹ️ **Important** : le rétablissement fonctionne techniquement sur **tous les forfaits**, mais il n'est **gratuit que sur le forfait illimité de NRJ Mobile** (ex. *Série spéciale NRJ Mobile illimitée*), où la remise annule les 12 €. Sur les autres forfaits la remise ne s'applique pas : le coût net reste > 0 € et le bouton **refuse donc de commander** (comportement voulu). Pour rétablir malgré tout un forfait payant, il faut passer par l'espace client NRJ Mobile.

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

## 📊 Adoption

**Nombre d'installations** — deux sources :

- 🔢 Badge **installs** (en haut) : téléchargements cumulés de l'asset `.zip` comptés par GitHub (installations + mises à jour).
- 📈 **HA Analytics** (installs actifs réels) : [analytics.home-assistant.io/custom_integrations](https://analytics.home-assistant.io/custom_integrations/) → cherche le domaine `nrjmobile`. Agrégé depuis les instances ayant activé les statistiques, mis à jour chaque semaine (apparaît dès qu'il y a assez d'installs).

### Intérêt dans le temps (⭐ GitHub)

<p align="center">
  <a href="https://star-history.com/#Louis73cr/NRJ-Mobile-integration&Date">
    <img src="https://api.star-history.com/svg?repos=Louis73cr/NRJ-Mobile-integration&type=Date" width="600" alt="Star History Chart">
  </a>
</p>

> GitHub ne fournit pas de graphique « installs dans le temps » : le graphe ci-dessus suit les ⭐ (indicateur d'intérêt). Les vrais chiffres d'installation sont le badge et HA Analytics ci-dessus.

---

## 🤝 Contribuer

Les contributions sont les bienvenues !

- 🐛 **Bug ou problème** : ouvre une [issue](https://github.com/Louis73cr/NRJ-Mobile-integration/issues) avec ta version de Home Assistant et les logs (`custom_components.nrjmobile`).
- 💡 **Idée de fonctionnalité** : ouvre une issue pour en discuter avant de coder.
- 🔧 **Pull request** : forke le dépôt, crée une branche, puis ouvre une PR vers `main`. Je relis et valide chaque PR avant de l'intégrer.
