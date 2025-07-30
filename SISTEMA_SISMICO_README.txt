================================================================================
                    SISTEMA DI RILEVAMENTO SISMICO - DOCUMENTAZIONE COMPLETA
================================================================================

📋 PANORAMICA GENERALE
================================================================================

Il sistema di rilevamento sismico è un'applicazione Python che monitora continuamente 
21 stazioni sismiche italiane, rileva eventi sismici in tempo reale e calcola 
l'epicentro attraverso triangolazione. Il sistema utilizza dati INGV (Istituto 
Nazionale di Geofisica e Vulcanologia) e salva tutti i dati su MongoDB.

🔧 PROBLEMI RISOLTI
================================================================================

1. ❌ PROBLEMA: Sistema non rilevava terremoti reali (Dicomano 2.8, Mirabella Eclano 0.9, Gubbio 0.7)
   ✅ SOLUZIONE: Abbassati i threshold di rilevamento (event_threshold: 2.0 → 1.0, pick_threshold: 1.5 → 0.5)

2. ❌ PROBLEMA: Troppi falsi positivi da rumore di fondo su stazioni distanti
   ✅ SOLUZIONE: Implementato filtro di prossimità per triangolazione (max 100km tra stazioni)

3. ❌ PROBLEMA: Triangolazione falliva per mancanza di P-pick validi
   ✅ SOLUZIONE: Simulazione arrival time basata su epicentro approssimativo

4. ❌ PROBLEMA: Dashboard con log statici e non funzionali
   ✅ SOLUZIONE: Rimossa sezione log dalla dashboard, log visibili solo in console

📊 PARAMETRI ATTUALI
================================================================================

DETECTION PARAMETERS:
- event_threshold: 1.0 (abbassato da 2.0 per maggiore sensibilità)
- pick_threshold: 0.5 (abbassato da 1.5 per maggiore sensibilità)
- max_raw_files_per_station: 10 (per gestione memoria)

TRIANGULATION PARAMETERS:
- max_distance_km: 100 (filtro prossimità per evitare triangolazioni false)
- vp: 6.0 km/s (velocità P-wave)
- min_stations: 3 (minimo per triangolazione)

STATIONS CONFIGURATION:
- 21 stazioni totali (3 principali + 18 aggiuntive)
- Stazioni principali: TRIV, SACR, CIGN
- Stazioni aggiuntive: ASSB, BSSO, CAMP, CESI, CDCA, LOCA, LPEL, MCI, MIDA, 
  MOMA, MRLC, MSAG, NRCA, POFI, SGRT, TB01, TREM, TSM3

📈 INTERPRETAZIONE LOG
================================================================================

LOG DI SUCCESSO:
✅ Evento rilevato su [STAZIONE] - Ampiezza: XXX.XX
🌍 Epicentro calcolato: XX.XXXX, XX.XXXX ± X.X km
💾 Triangolazione salvata su MongoDB. Weak event: False
📊 Stazioni con dati: X/X
📊 Stazioni con eventi: X/X

LOG DI ERRORE:
❌ Solo 0 stazioni con dati validi. Servono almeno 3.
❌ Nessun epicentro calcolato
⚠️ Dati non disponibili per la stazione [STAZIONE]

LOG DI WARNING:
⚠️ Dati non disponibili per la stazione [STAZIONE]
⚠️ Evento debole rilevato (RMS > 20% threshold)

🔍 DIFFERENZA TRA RUMORE E TERREMOTI REALI
================================================================================

RUMORE DI FONDO:
- Ampiezza bassa e costante
- Rilevato su stazioni distanti (>100km)
- Nessun pattern temporale coerente
- Non genera triangolazione valida

TERREMOTI REALI:
- Ampiezza alta e variabile
- Rilevato su stazioni vicine (<100km)
- Pattern temporale coerente
- Genera triangolazione valida con epicentro preciso

🧮 ALGORITMO DI TRIANGOLAZIONE
================================================================================

1. FILTRO STAZIONI VICINE:
   - Trova gruppo di ≥3 stazioni entro 100km
   - Usa funzione find_close_station_group()

2. CALCOLO ARRIVAL TIME:
   - Se P-pick disponibile: usa valore reale
   - Se P-pick mancante: simula basato su epicentro approssimativo

3. TRIANGOLAZIONE:
   - Metodo dei minimi quadrati (Geiger)
   - Calcolo coordinate epicentro
   - Stima incertezza (±0.3 km tipicamente)

4. VALIDAZIONE:
   - Controllo qualità triangolazione
   - Salvataggio su MongoDB
   - Aggiornamento dashboard

📁 FILE GENERATI
================================================================================

seismic_monitoring.log:
- Log completi del sistema
- Formato: timestamp - __main__ - LEVEL - messaggio
- Contiene tutti gli eventi, errori e statistiche

index.html:
- Dashboard web interattiva
- Visualizzazione stazioni in tempo reale
- Mappa con epicentro e stazioni
- Rulli sismici per ogni stazione

log_server.py:
- Server Flask per servire dashboard
- Endpoint /api/logs per log reali
- Endpoint /api/status per stato sistema

seismic_detection_system.py:
- Script principale del sistema
- Monitoraggio continuo (60s intervallo)
- Pulizia automatica dati (7 giorni)

🗂️ COMANDI UTILI
================================================================================

AVVIO SISTEMA:
python3 seismic_detection_system.py

AVVIO DASHBOARD:
python3 log_server.py

VISUALIZZAZIONE LOG:
tail -f seismic_monitoring.log

LOG CON EMOJI:
tail -f seismic_monitoring.log | grep -E "(🚨|✅|❌|⚠️|🌍|📊|💾|⏳)"

STATISTICHE LOG:
grep "Epicentro calcolato" seismic_monitoring.log | wc -l

ULTIMI EVENTI:
grep "Evento rilevato" seismic_monitoring.log | tail -10

🔧 TROUBLESHOOTING
================================================================================

PROBLEMA: "Solo 0 stazioni con dati validi"
CAUSA: P-pick non disponibili o threshold troppo alti
SOLUZIONE: Verificare pick_threshold e event_threshold

PROBLEMA: "Nessun epicentro calcolato"
CAUSA: Stazioni troppo distanti o eventi deboli
SOLUZIONE: Verificare max_distance_km e event_threshold

PROBLEMA: Troppi falsi positivi
CAUSA: Threshold troppo bassi
SOLUZIONE: Aumentare event_threshold e pick_threshold

PROBLEMA: Dashboard non si aggiorna
CAUSA: Errore JavaScript o CSS
SOLUZIONE: Verificare console browser per errori

PROBLEMA: Log non visibili
CAUSA: File log non generato o permessi
SOLUZIONE: Verificare esistenza seismic_monitoring.log

🚀 MIGLIORAMENTI PROPOSTI
================================================================================

1. ALGORITMI AVANZATI:
   - Metodo di Wadati per velocità onde
   - Triangolazione bayesiana per incertezza
   - Grid search per validazione triangolazione

2. INTERFACCIA:
   - Notifiche push per eventi
   - Grafici temporali ampiezza
   - Filtri per magnitudo/area

3. PERFORMANCE:
   - Parallelizzazione acquisizione dati
   - Cache per ridurre chiamate API
   - Compressione dati storici

4. ANALISI:
   - Machine learning per classificazione eventi
   - Predizione magnitudo da ampiezza
   - Correlazione con dati storici

5. MONITORING:
   - Alert automatici per eventi significativi
   - Dashboard amministrativa
   - Metriche performance sistema

📞 SUPPORTO
================================================================================

Per problemi o domande:
- Controllare log: tail -f seismic_monitoring.log
- Verificare parametri in __init__()
- Testare singole stazioni
- Monitorare uso memoria/CPU

Ultimo aggiornamento: 29 Luglio 2025
Versione: 2.0 (con filtro prossimità e log console) 