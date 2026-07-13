# OpenWindows

Intégration personnalisée Home Assistant qui indique **quand ouvrir ou fermer
les fenêtres** pour rafraîchir naturellement le logement, à partir de deux
prévisions météo (température + solaire) et des capteurs de température /
humidité de vos pièces. V1 = logique de croisement extérieur/intérieur avec
hystérésis, filtre point de rosée (humidité), référence intérieure = la pièce
la plus chaude du cœur traversant, et notifications texte (blueprints
auto-copiés). Pas de dépendance lourde (pas de numpy / matplotlib en V1).

## Qu'est-ce que OpenWindows ?

L'intégration interroge à intervalle régulier (15 min par défaut, réglable)
la prévision horaire de deux entités météo :

- une entité **température** (ex. Météo-France) qui pilote le calcul ;
- une entité **solaire / horizon long** (ex. Open-Meteo) dont la couverture
  nuageuse et l'ensoleillement sont fusionnés dans la même série horaire
  (réservé aux évolutions futures du modèle).

Elle combine ça avec vos capteurs de température/humidité (cœur traversant,
bureau) et l'état de la porte de balcon pour produire un **verdict** (`open`,
`close`, `keep_closed`, `open_soon`), une **prochaine ouverture/fermeture**
prévue, et une prévision d'intérieur. La référence intérieure globale est la
température de la pièce la plus chaude parmi les capteurs du cœur traversant.
Deux blueprints d'automatisation (notification + ventilateur) sont copiés
automatiquement dans votre configuration au premier démarrage.

## Installation via HACS (dépôt personnalisé)

OpenWindows n'est pas (encore) dans le dépôt par défaut de HACS : ajoutez-le
comme dépôt personnalisé.

1. Ouvrez **HACS**, puis le menu (⋮) en haut à droite > **Dépôts personnalisés**.
2. Ajoutez l'URL `https://github.com/MicPiePro/openwindows`, catégorie
   **Intégration**.
3. Recherchez "OpenWindows" dans HACS et cliquez sur **Télécharger**.
4. **Redémarrez Home Assistant.**

Vous pouvez aussi installer manuellement : copiez le dossier
`custom_components/openwindows` dans le dossier `custom_components` de votre
configuration Home Assistant, puis redémarrez.

## Ajout de l'intégration

**Paramètres > Appareils et services > Ajouter une intégration >
"OpenWindows"**, puis renseignez le formulaire :

| Champ | Description |
| --- | --- |
| Entité météo — température | Entité `weather.*` qui fournit la prévision horaire de température/humidité utilisée pour le calcul (ex. Météo-France). Sélectionnez **une seule entité**. |
| Entité météo — solaire / horizon long | Entité `weather.*` dont la couverture nuageuse et l'ensoleillement horaires sont fusionnés (ex. Open-Meteo). Sélectionnez **une seule entité**. |
| Capteurs de température — cœur traversant | Capteurs `sensor.*` (device_class température) des pièces traversantes (salon, cuisine, chambres). La référence intérieure retenue est la température **la plus chaude** parmi ces capteurs. |
| Capteurs d'humidité — cœur traversant | Capteurs `sensor.*` (device_class humidité) associés (moyenne, informatif). |
| Capteur de température — bureau | Un seul capteur `sensor.*` (device_class température). |
| Capteur d'humidité — bureau | Un seul capteur `sensor.*` (device_class humidité). |
| Capteur d'ouverture de porte | `binary_sensor.*` de porte/fenêtre. |
| Orientation des fenêtres principales | Point cardinal (N, NE, E, SE, S, SW, W, NW). |

> Les deux champs météo sont en **sélection unique** (une entité par champ).
> Les réglages *orientation*, *inertie des murs* et *ventilation* sont
> enregistrés pour le **modèle thermique de la V2** et n'ont pas encore
> d'effet sur le verdict en V1.

L'entrée se crée sans étape supplémentaire ; un appareil **OpenWindows**
apparaît avec toutes les entités ci-dessous.

### Réglages (options)

Depuis la carte de l'intégration, cliquez sur **Configurer** pour ajuster les
seuils de décision sans recréer l'intégration : température de confort cible,
marge d'ouverture, marge de fermeture (hystérésis), température intérieure
minimale, activation du filtre d'humidité (point de rosée) et sa marge,
inertie des murs, niveau de ventilation, et intervalle de mise à jour. Ces
réglages ne sont pas exposés comme entités
Home Assistant en V1 (pas de carte Lovelace dédiée possible) — modifiez-les
via **Paramètres > Appareils et services > OpenWindows > Configurer**.

## Entités exposées

Toutes les entités partagent l'appareil **OpenWindows** et sont préfixées
`openwindows_`.

| Entité | Type | Description | Attributs |
| --- | --- | --- | --- |
| `sensor.openwindows_verdict` | sensor | Verdict global : `open`, `close`, `keep_closed` ou `open_soon`. | `reason`, `outdoor_temp`, `indoor_ref_temp`, `humidity_gate_blocking` |
| `sensor.openwindows_next_open` | sensor (timestamp) | Horodatage de la prochaine ouverture conseillée. | — |
| `sensor.openwindows_next_close` | sensor (timestamp) | Horodatage de la prochaine fermeture conseillée. | — |
| `sensor.openwindows_predicted_indoor` | sensor (°C) | Pic d'intérieur prévu sur l'horizon de prévision. | `forecast` : liste `{time_iso, outdoor, indoor_pred, comfort}` |
| `sensor.openwindows_current_outdoor` | sensor (°C) | Température extérieure courante utilisée pour la décision. | `dew_point` |
| `sensor.openwindows_zone_crossvent` | sensor | Verdict de la zone "cœur traversant" (référence = pièce la plus chaude). | `indoor_temp`, `indoor_dew_point`, `humidity_gate_blocking` |
| `sensor.openwindows_zone_bureau` | sensor | Verdict de la zone "bureau". | `indoor_temp`, `indoor_dew_point`, `humidity_gate_blocking` |
| `sensor.openwindows_degrees_saved` | sensor (°C) | Degrés de chauffe intérieure évités en suivant le conseil. | — |
| `binary_sensor.openwindows_humidity_gate` | binary_sensor | Allumé quand le filtre d'humidité (point de rosée) bloque une ouverture. | — |

> L'attribut `forecast` de `sensor.openwindows_predicted_indoor` est une liste
> de points `{time_iso, outdoor, indoor_pred, comfort}`. En V1, `indoor_pred`
> maintient la température de référence actuelle (pas de modèle RC — voir
> Roadmap V2).

## Blueprints (copiés automatiquement)

Au premier démarrage (et à chaque mise à jour), OpenWindows copie deux
blueprints d'automatisation dans
`config/blueprints/automation/openwindows/` :

- **OpenWindows - Notification ouverture/fermeture** : notification texte en
  français (sans image) quand `sensor.openwindows_verdict` passe à `open` ou
  `close`, avec les températures et deux boutons d'action **C'est fait** /
  **Rappel**.
- **OpenWindows - Contrôle ventilateur** : allume un ventilateur quand le
  verdict passe à `open`, l'éteint quand il passe à `close`.

Créez vos automatisations depuis **Paramètres > Automatisations et scènes >
Blueprints**.

## Cartes de tableau de bord

OpenWindows n'embarque aucun composant web personnalisé en V1. Utilisez les
cartes natives ci-dessous, plus une carte `custom:apexcharts-card`
(installable via HACS > Frontend) pour tracer la prévision.

### Vue d'ensemble (carte native `entities`)

```yaml
type: entities
title: OpenWindows
entities:
  - entity: sensor.openwindows_verdict
    name: Verdict
  - entity: sensor.openwindows_next_open
    name: Prochaine ouverture
  - entity: sensor.openwindows_next_close
    name: Prochaine fermeture
  - entity: sensor.openwindows_current_outdoor
    name: Extérieur
  - entity: sensor.openwindows_predicted_indoor
    name: Intérieur prévu (pic)
  - entity: sensor.openwindows_degrees_saved
    name: Degrés économisés
  - entity: sensor.openwindows_zone_crossvent
    name: Zone traversante
  - entity: sensor.openwindows_zone_bureau
    name: Bureau
  - entity: binary_sensor.openwindows_humidity_gate
    name: Blocage humidité (point de rosée)
```

### Résumé et prochaine bascule (carte native `markdown`)

```yaml
type: markdown
title: OpenWindows — Résumé
content: >-
  **Verdict : {{ states('sensor.openwindows_verdict') }}** —
  {{ state_attr('sensor.openwindows_verdict', 'reason') }}


  Extérieur : {{ state_attr('sensor.openwindows_verdict', 'outdoor_temp') }} °C
  · Intérieur (pièce la plus chaude) :
  {{ state_attr('sensor.openwindows_verdict', 'indoor_ref_temp') }} °C


  Prochaine ouverture : {{ states('sensor.openwindows_next_open') }}

  Prochaine fermeture : {{ states('sensor.openwindows_next_close') }}
```

### Détail par zone (carte native `entities` avec lignes `attribute`)

```yaml
type: entities
title: OpenWindows — Zones
entities:
  - entity: sensor.openwindows_zone_crossvent
    name: Cœur traversant
  - type: attribute
    entity: sensor.openwindows_zone_crossvent
    attribute: indoor_temp
    name: Température (traversant)
    suffix: " °C"
  - type: attribute
    entity: sensor.openwindows_zone_crossvent
    attribute: humidity_gate_blocking
    name: Humidité bloquante (traversant)
  - entity: sensor.openwindows_zone_bureau
    name: Bureau
  - type: attribute
    entity: sensor.openwindows_zone_bureau
    attribute: indoor_temp
    name: Température (bureau)
    suffix: " °C"
  - type: attribute
    entity: sensor.openwindows_zone_bureau
    attribute: humidity_gate_blocking
    name: Humidité bloquante (bureau)
```

### Vue rapide (carte native `glance`)

```yaml
type: glance
title: OpenWindows — Vue rapide
entities:
  - entity: sensor.openwindows_verdict
    name: Verdict
  - entity: binary_sensor.openwindows_humidity_gate
    name: Humidité
  - entity: sensor.openwindows_degrees_saved
    name: Économisés
```

### Jauge intérieur prévu (carte native `gauge`)

```yaml
type: gauge
entity: sensor.openwindows_predicted_indoor
name: Intérieur prévu (pic)
unit: "°C"
min: 18
max: 40
needle: true
severity:
  green: 18
  yellow: 25
  red: 28
```

### Courbe de prévision (`custom:apexcharts-card`)

Trace l'attribut `forecast` de `sensor.openwindows_predicted_indoor`
(extérieur vs intérieur prévu vs cible de confort).

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: OpenWindows — Prévision intérieure
  show_states: true
  colorize_states: true
graph_span: 24h
span:
  start: hour
apex_config:
  chart:
    height: 260
  legend:
    show: true
  xaxis:
    type: datetime
series:
  - entity: sensor.openwindows_predicted_indoor
    name: Extérieur
    type: line
    stroke_width: 2
    data_generator: |
      return (entity.attributes.forecast || []).map(p => {
        return [new Date(p.time_iso).getTime(), p.outdoor];
      });
  - entity: sensor.openwindows_predicted_indoor
    name: Intérieur (prévu)
    type: line
    stroke_width: 2
    data_generator: |
      return (entity.attributes.forecast || []).map(p => {
        return [new Date(p.time_iso).getTime(), p.indoor_pred];
      });
  - entity: sensor.openwindows_predicted_indoor
    name: Confort
    type: line
    curve: stepline
    stroke_width: 1
    data_generator: |
      return (entity.attributes.forecast || []).map(p => {
        return [new Date(p.time_iso).getTime(), p.comfort];
      });
```

> L'attribut `forecast` est une liste de points `{time_iso, outdoor, indoor_pred, comfort}`.
> En V1 `indoor_pred` maintient la température de référence actuelle (pas de modèle RC).

## Vérification manuelle

Une checklist pas-à-pas pour valider une installation sur une instance Home
Assistant réelle (installation HACS, ajout de l'intégration, entités,
verdict peuplé, blueprints, notification) est disponible dans
[`docs/VERIFICATION.md`](docs/VERIFICATION.md).

## Roadmap V2 (plan séparé)

Non implémenté en V1, prévu dans un plan dédié : modèle thermique RC à
2 nœuds (numpy) pour une vraie prévision `indoor_pred`, PNG matplotlib inséré
dans la notification, auto-calibration de τ à partir de l'historique du
recorder, terme solaire via Open-Meteo, et carte Lovelace "hero" empaquetée
en option.
