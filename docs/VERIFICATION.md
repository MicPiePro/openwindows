# OpenWindows — Vérification manuelle (V1)

À exécuter sur une instance Home Assistant réelle (>= 2024.6). Cocher chaque
étape.

## 1. Installation via HACS (dépôt personnalisé)
- [ ] HACS > menu (⋮) > "Dépôts personnalisés".
- [ ] Ajouter l'URL du dépôt `https://github.com/MicPiePro/openwindows`, catégorie **Integration**.
- [ ] Rechercher "OpenWindows" dans HACS, cliquer **Télécharger**.
- [ ] Redémarrer Home Assistant.
- **Attendu :** `custom_components/openwindows/` présent, aucun message d'erreur au démarrage dans Paramètres > Système > Journaux.

## 2. Ajout de l'intégration
- [ ] Paramètres > Appareils et services > **Ajouter une intégration** > "OpenWindows".
- [ ] Renseigner le formulaire (ConfigFlow) :
  - Météo température : `weather.home`
  - Météo solaire : `weather.maison`
  - Capteurs température zone traversante (Salon, Cuisine, Chambre, Chambre 2)
  - Capteurs humidité zone traversante
  - Capteurs température / humidité chambres (référence quand la clim tourne)
  - Capteur température / humidité Bureau
  - Capteur de puissance de la clim portable
  - Capteur d'ouverture de porte
  - Orientation
- **Attendu :** l'entrée se crée sans erreur, un appareil "OpenWindows" apparaît.

## 3. Entités créées
- [ ] Ouvrir l'appareil "OpenWindows".
- **Attendu :** présence de `sensor.openwindows_verdict`, `sensor.openwindows_next_open`,
  `sensor.openwindows_next_close`, `sensor.openwindows_predicted_indoor`,
  `sensor.openwindows_current_outdoor`, `sensor.openwindows_zone_crossvent`,
  `sensor.openwindows_zone_bureau`, `sensor.openwindows_degrees_saved`,
  `binary_sensor.openwindows_ac_active`, `binary_sensor.openwindows_humidity_gate`.

## 4. Le verdict est peuplé
- [ ] Outils de développement > États > filtrer `sensor.openwindows_verdict`.
- **Attendu :** l'état vaut `open`, `close`, `keep_closed` ou `open_soon`
  (jamais `unknown`/`unavailable` après le premier rafraîchissement), et les
  attributs `reason`, `outdoor_temp`, `indoor_ref_temp`, `reference_zone`,
  `humidity_gate_blocking`, `ac_on` sont présents.

## 5. Tableau de bord
- [ ] Ajouter les cartes du [README — Cartes de tableau de bord](../README.md#cartes-de-tableau-de-bord)
  à un tableau de bord (vue d'ensemble `entities`, résumé `markdown`, détail
  par zone, vue rapide `glance`, jauge `gauge`).
- [ ] Installer `custom:apexcharts-card` via HACS > Frontend, puis ajouter la
  carte de courbe de prévision.
- **Attendu :** toutes les cartes s'affichent sans erreur "Custom element
  doesn't exist" ni "Entity not available" ; la courbe apexcharts trace bien
  trois séries (extérieur, intérieur prévu, confort) sur les prochaines 24h.

## 6. Blueprints auto-copiés
- [ ] Paramètres > Automatisations et scènes > **Blueprints**.
- **Attendu :** "OpenWindows - Notification ouverture/fermeture" et
  "OpenWindows - Contrôle ventilateur" apparaissent (copiés dans
  `config/blueprints/automation/openwindows/`).

## 7. Déclencher une notification
- [ ] Créer une automatisation depuis le blueprint de notification, cible = téléphone (application HA).
- [ ] Outils de développement > États : forcer `sensor.openwindows_verdict` à `open`
  (Définir l'état) pour simuler une bascule.
- **Attendu :** une notification en français arrive sur le téléphone, avec les
  températures et deux boutons **C'est fait** / **Rappel** (texte seul, pas d'image).
- [ ] Rétablir le verdict réel (recharger l'intégration).
