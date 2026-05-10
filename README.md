# Renault Extended – Custom Integration für Home Assistant

Erweiterte Integration für MyRenault-Fahrzeuge. Holt alle verfügbaren Daten aus der Renault Kamereon API, die die offizielle HA-Integration nicht abdeckt – insbesondere die vollständige **Ladehistorie**.

---

## Features

### Sensoren
| Sensor | Beschreibung | Update |
|--------|-------------|--------|
| Akkustand | Ladestand in % | 5 min |
| Reichweite | Geschätzte Reichweite in km | 5 min |
| Verfügbare Energie | kWh im Akku | 5 min |
| Akkutemperatur | Temperatur des Akkus | 5 min |
| Ladeleistung | Aktuelle Ladeleistung in W | 5 min |
| Restladezeit | Verbleibende Ladezeit in Minuten | 5 min |
| Ladestecker Status | Eingesteckt / Nicht eingesteckt | 5 min |
| Ladestatus | Lädt / Lädt nicht / Fehler | 5 min |
| Kilometerstand | Gesamtkilometerstand | 6 h |
| Letztes Laden: Start | Startzeitpunkt des letzten Ladevorgangs | 6 h |
| Letztes Laden: Ende | Endzeitpunkt des letzten Ladevorgangs | 6 h |
| Letztes Laden: Dauer | Dauer in Minuten | 6 h |
| Letztes Laden: SOC Start | Akkustand zu Ladebeginn in % | 6 h |
| Letztes Laden: SOC Ende | Akkustand nach dem Laden in % | 6 h |
| Letztes Laden: SOC Geladen | Geladene Prozentpunkte | 6 h |
| Letztes Laden: Ladeart | Langsam / Normal / Schnell / DC | 6 h |
| Letztes Laden: Startleistung | Ladeleistung bei Start in W | 6 h |
| Letztes Laden: Status | Erfolgreich / Fehler | 6 h |
| Ladevorgänge gesamt | Anzahl Ladevorgänge im Zeitraum | 6 h |
| Gesamtladezeit | Summe aller Ladezeiten in Stunden | 6 h |
| Ladefehlschläge | Anzahl Fehler im Zeitraum | 6 h |
| Klimaanlage Status | Ein / Aus | 5 min |
| Außentemperatur | Außentemperatur in °C | 5 min |
| Türschloss | Verriegelt / Entriegelt | 5 min |
| Tür Fahrer | Offen / Geschlossen | 5 min |
| Tür Beifahrer | Offen / Geschlossen | 5 min |
| Tür hinten links | Offen / Geschlossen | 5 min |
| Tür hinten rechts | Offen / Geschlossen | 5 min |
| Heckklappe | Offen / Geschlossen | 5 min |
| Reifendruck (4x) | Druck in mbar | 24 h |
| Remote Start Status | RES-Status | 24 h |

### Binary Sensoren
- Ladekabel eingesteckt
- Lädt gerade
- Fahrzeug verriegelt
- Alle 4 Türen offen/geschlossen
- Heckklappe offen/geschlossen
- Klimaanlage aktiv

### Device Tracker
- GPS-Position des Fahrzeugs (erscheint auf der HA-Karte)

### Ladehistorie (Attribut-Sensor)
Der Sensor `renault_extended_ladehistorie` enthält im `extra_state_attributes` die komplette Liste aller Ladevorgänge der letzten 60 Tage als JSON – ideal für Template-Sensoren und Grafana-Auswertungen.

---

## Installation

### Via HACS (empfohlen)

1. HACS öffnen → **Integrationen** → drei Punkte oben rechts → **Custom repositories**
2. URL: `https://github.com/DEINNAME/renault-extended-ha` – Kategorie: **Integration**
3. **Renault Extended** suchen und installieren
4. HA neu starten

### Manuell

```bash
cd /config/custom_components
git clone https://github.com/DEINNAME/renault-extended-ha renault_extended
```

HA neu starten.

---

## Konfiguration

1. **Einstellungen → Integrationen → + Integration hinzufügen → Renault Extended**
2. MyRenault E-Mail und Passwort eingeben
3. Locale setzen (Standard: `de_DE`)
4. Konto und Fahrzeug wählen

### Optionen (nachträglich änderbar)
- **Ladehistorie Tage**: Wie viele Tage zurück abgerufen werden (Standard: 60)
- **Anzahl Einzelsensoren**: Wie viele Ladevorgänge als eigene Sensoren erscheinen (Standard: 20)

---

## Poll-Intervalle

| Gruppe | Endpunkte | Intervall |
|--------|-----------|-----------|
| Echtzeit | Akku, Laden, GPS, Türen, HVAC | 5 Minuten |
| Historie | Ladehistorie, Kilometerstand | 6 Stunden |
| Statisch | Reifendruck, Remote-Start | 24 Stunden |

---

## Verwendete API-Endpunkte

| Endpunkt | Daten |
|----------|-------|
| `/battery-status` | Akkustand, Reichweite, Ladestatus, Ladeleistung |
| `/charges` | Detaillierte Ladehistorie (Start, Ende, SOC, Leistung) |
| `/charge-history` | Tages-Aggregation der Ladevorgänge |
| `/cockpit` | Gesamtkilometerstand |
| `/location` | GPS-Koordinaten |
| `/lock-status` | Schloss, alle Türen, Heckklappe |
| `/hvac-status` | Klimaanlage, Außentemperatur |
| `/pressure` | Reifendruck alle 4 Räder |
| `/res-state` | Remote Engine Start Status |

---

## Voraussetzungen

- Home Assistant 2023.1.0 oder neuer
- Aktives MyRenault-Konto
- Fahrzeug mit Connected Services

---

## Hinweise

- Manche Endpunkte sind nicht bei allen Fahrzeugmodellen verfügbar. Nicht verfügbare Sensoren werden automatisch als `unavailable` markiert.
- Bei neueren Fahrzeugen (z.B. Scenic E-Tech) können abweichende API-Pfade dazu führen, dass einzelne Endpunkte nicht funktionieren.
- Diese Integration ist nicht offiziell von Renault und steht in keiner Verbindung zu Renault.

---

## Lizenz

MIT License – siehe [LICENSE](LICENSE)
