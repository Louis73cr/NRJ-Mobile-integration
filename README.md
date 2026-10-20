# NRJ Mobile — intégration Home Assistant (HACS)

Suivi de consommation et rétablissement du débit data (seuil 500 Go) pour
l'espace client **NRJ Mobile** (`espace-client.nrjmobile.fr`), 100 % en Python,
**sans MQTT ni broker**.

## Ce que ça expose (par ligne / numéro)

| Entité | Type | Détail |
| --- | --- | --- |
| Data utilisée | `sensor` (Go) | conso France du cycle en cours |
| Plafond data | `sensor` (Go) | ex. 200 ou 500 Go |
| Data restante | `sensor` (Go) | plafond − utilisée |
| Hors-forfait | `sensor` (€) | montant hors-forfait |
| Seuil data atteint | `binary_sensor` | `on` quand le débit est bridé (≥ plafond) |
| Rétablir le débit web | `button` | déclenche le `FUP_RESET` **strict gratuit** |

Attributs du capteur « Data utilisée » : forfait, contrat, prix mensuel, roaming UE/DOM.

## Installation (HACS)

1. HACS → ⋮ → *Dépôts personnalisés* → URL de ce repo, catégorie **Integration**.
2. Installer « NRJ Mobile », redémarrer Home Assistant.
3. *Paramètres → Appareils et services → Ajouter → NRJ Mobile*, saisir identifiant + mot de passe.

## Sécurité du bouton de rétablissement

Le backend chiffre un « Frais de restauration » de 12 € **puis applique une remise
équivalente → net 0 €**. Le bouton calcule le **coût net** (brut − remise) et
**ne soumet la commande que si le net est 0 €**. Si un jour le net est > 0, le
bouton échoue proprement sans rien commander (aucun prélèvement accidentel).

## Automatisation type (réactiver dès que bridé)

```yaml
automation:
  - alias: NRJ - rétablir le débit auto
    trigger:
      - platform: state
        entity_id: binary_sensor.ligne_06XXXXXXXX_seuil_data_atteint
        to: "on"
    action:
      - service: button.press
        target:
          entity_id: button.ligne_06XXXXXXXX_retablir_le_debit_web
      - service: notify.persistent_notification
        data:
          message: "Débit NRJ Mobile rétabli (0 €)."
```

## Notes techniques

- Auth OIDC **PKCE** directe (Keycloak `oauth2.nrjmobile.fr`, realm `nrj`,
  client `wsc-frontend`), token ~5 min → ré-authentification à chaque cycle.
- Polling toutes les 30 min, appels espacés de 350 ms (anti-403 WAF).
- `api.py` est autonome : `python3 api.py` lance un self-check hors-ligne.

> Usage personnel / interopérabilité avec son propre compte.
