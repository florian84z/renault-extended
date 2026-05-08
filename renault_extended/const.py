"""Constants für Renault Extended Integration."""

DOMAIN = "renault_extended"

CONF_LOCALE = "locale"
CONF_ACCOUNT_ID = "account_id"
CONF_VIN = "vin"

# Update-Intervalle in Sekunden
SCAN_INTERVAL_REALTIME = 300       # 5 min – Akku, Laden, Location, Lock, HVAC
SCAN_INTERVAL_HISTORY  = 21600     # 6 h  – Ladehistorie, Kilometerstand
SCAN_INTERVAL_STATIC   = 86400     # 24 h – Reifendruck, Res-State

# Ladehistorie
HISTORY_DAYS   = 60
LAST_N_CHARGES = 20

# Charge Power Labels
CHARGE_POWER_LABELS = {
    "slow":         "Langsam (≤3,7 kW)",
    "normal":       "Normal (≤7,4 kW)",
    "fast":         "Schnell (≤22 kW)",
    "accelerated":  "Beschleunigt (DC)",
}

# Lock Status
LOCK_STATUS_LABELS = {
    "locked":   "Verriegelt",
    "unlocked": "Entriegelt",
}

# Door Status
DOOR_STATUS_LABELS = {
    "open":   "Offen",
    "closed": "Geschlossen",
}
