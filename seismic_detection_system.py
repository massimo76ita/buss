#!/usr/bin/env python3
"""
Sistema Automatico di Rilevamento e Triangolazione Sismica
Database separato per il sistema di monitoraggio
"""

import logging
from obspy import UTCDateTime
from obspy.clients.fdsn import Client
from obspy.signal.trigger import classic_sta_lta, recursive_sta_lta, plot_trigger, trigger_onset
from obspy.core.stream import Stream
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, timezone
import time
from pymongo import MongoClient
from gridfs import GridFS
import os
import json
import traceback

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('seismic_monitoring.log')
    ]
)
logger = logging.getLogger(__name__)

class SeismicDetectionSystem:
    def __init__(self):
        self.sampling_rate = 100
        self.vp = 6.0
        self.rete = "IV"
        self.canale = "HHZ"
        self.latenza_ingv = 300
        self.acquisition_duration = 600
        self.event_threshold = 0.1  # Abbassato da 0.5 a 0.1
        self.pick_threshold = 0.05  # Abbassato da 0.3 a 0.05
        self.max_days_to_keep = 7
        self.cleanup_interval = 6 * 3600
        self.max_raw_files_per_station = 10
        self.save_raw_data = False
        self.save_aggregated = True
        self.aggregation_interval = 300
        self.last_aggregation = {}
        self.aggregated_data = {}
        self.last_event_time = None
        self.event_in_progress = False

        self.mongo_uri = "mongodb+srv://massimoserafini:QIs0axxmwPcEKS78@monitoring.auhw6a8.mongodb.net/?retryWrites=true&w=majority&appName=monitoring"
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client["monitoring"]
        self.collection = self.db["seismic_monitoring"]
        self.fs = GridFS(self.db)

        self.stations = {
            "TRIV": {"lat": 41.7666, "lon": 14.5502, "name": "Trivento"},
            "SACR": {"lat": 41.3974, "lon": 14.7057, "name": "S. Croce del Sannio"},
            "CIGN": {"lat": 41.65418, "lon": 14.90502, "name": "Sant'Elia a Pianisi"},
            # ... altre stazioni
        }

        self.ingv_client = Client("INGV")

        print("🚀 Sistema di Rilevamento Sismico inizializzato")
        print(f"📡 Stazioni configurate: {len(self.stations)}")
        print(f"️ Database MongoDB: {self.db.name}")
        print(f"️ Collection: {self.collection.name}")
        print(f"️ URI: monitoring.auhw6a8.mongodb.net")

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        R = 6371
        phi1, phi2 = np.radians(lat1), np.radians(lat2)
        dphi = np.radians(lat2 - lat1)
        dlambda = np.radians(lon2 - lon1)
        a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
        return 2*R*np.arcsin(np.sqrt(a))

    def acquire_data(self, station):
        try:
            end = UTCDateTime() - self.latenza_ingv
            start = end - self.acquisition_duration
            st = self.ingv_client.get_waveforms(self.rete, station, "", self.canale, start, end)
            if len(st) > 0:
                tr = st[0]
                tr.detrend("demean")
                tr.filter("bandpass", freqmin=0.5, freqmax=10.0)
                data = tr.data.astype(np.float64)
                data -= np.mean(data)
                return data
        except Exception as e:
            logger.error(f"❌ Errore acquisizione {station}: {e}")
        return None
    def cleanup_old_data(self):
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.max_days_to_keep)
            old_files = list(self.collection.find({
                "timestamp": {"$lt": cutoff_date.isoformat()},
                "type": "seismic_data"
            }))
            for file_meta in old_files:
                try:
                    self.fs.delete(file_meta["file_id"])
                    self.collection.delete_one({"_id": file_meta["_id"]})
                except Exception as e:
                    logger.warning(f"❌ Errore eliminazione file {file_meta.get('filename')}: {e}")

            stations = self.collection.distinct("station")
            for station in stations:
                try:
                    station_files = list(self.collection.find({
                        "station": station,
                        "type": "seismic_data"
                    }).sort("timestamp", -1))
                    if len(station_files) > self.max_raw_files_per_station:
                        for file_meta in station_files[self.max_raw_files_per_station:]:
                            try:
                                self.fs.delete(file_meta["file_id"])
                                self.collection.delete_one({"_id": file_meta["_id"]})
                            except Exception as e:
                                logger.warning(f"❌ Errore eliminazione file {file_meta.get('filename')}: {e}")
                except Exception as e:
                    logger.warning(f"❌ Errore pulizia file stazione {station}: {e}")

            logger.info(f"✅ Pulizia completata. Mantenuti solo gli ultimi {self.max_days_to_keep} giorni di dati.")
            return True
        except Exception as e:
            logger.error(f"❌ Errore durante la pulizia dei dati: {e}")
            return False
    def save_data_to_mongodb(self, station, data, timestamp, event_detected=False):
        logger.debug(f"[DB] Tentativo salvataggio dati per {station} - Evento: {event_detected}")
        if data is None or len(data) == 0:
            logger.warning(f"[DB] Nessun dato valido da salvare per {station}")
            return None
        try:
            current_time = datetime.now(timezone.utc)
            if not hasattr(self, '_last_cleanup') or (current_time - self._last_cleanup).total_seconds() > self.cleanup_interval:
                logger.info("[DB] Esecuzione pulizia periodica del database...")
                self.cleanup_old_data()
                self._last_cleanup = current_time

            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)

            base_metadata = {
                "type": "seismic_data",
                "station": station,
                "timestamp": timestamp.isoformat(),
                "data_available": True,
                "event_detected": event_detected,
                "processing_time": current_time.isoformat()
            }

            if event_detected:
                logger.info(f"🚨 Evento rilevato! Salvataggio dati per la stazione {station}")
                print(f"🚨 Evento rilevato! Salvataggio dati per la stazione {station}")
                self._save_event_data(station, data, timestamp, "event_triggered")
                self.last_event_time = current_time
                self.event_in_progress = True
                base_metadata.update({
                    "event_type": "event_triggered",
                    "max_amplitude": float(np.max(np.abs(data)))
                })
                self.collection.insert_one(base_metadata)
                return True

            if self.event_in_progress:
                time_since_last_event = (current_time - self.last_event_time).total_seconds()
                if time_since_last_event < 300:
                    logger.info(f"📝 Salvataggio dati post-evento per la stazione {station}")
                    self._save_event_data(station, data, timestamp, "post_event")
                    base_metadata.update({
                        "event_type": "post_event",
                        "seconds_since_event": time_since_last_event
                    })
                    self.collection.insert_one(base_metadata)
                    return True
                else:
                    logger.info(f"✅ Fine periodo post-evento per la stazione {station}")
                    self.event_in_progress = False

            if not hasattr(self, f'last_save_{station}') or \
               (current_time - getattr(self, f'last_save_{station}')).total_seconds() > self.aggregation_interval:
                logger.info(f"💾 Salvataggio dati aggregati per la stazione {station}")
                aggregated = self._aggregate_data(station, data, timestamp)
                if aggregated:
                    self._save_aggregated_data(station, aggregated, timestamp)
                    base_metadata.update({
                        "type": "aggregated_data",
                        "data_points": len(aggregated.get('data', [])),
                        "interval_seconds": self.aggregation_interval
                    })
                    self.collection.insert_one(base_metadata)
                    setattr(self, f'last_save_{station}', current_time)
                    return True

            return False

        except Exception as e:
            logger.error(f"❌ Errore salvataggio dati {station}: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    def _save_event_data(self, station, data, timestamp, event_type):
        try:
            metadata = {
                "type": "seismic_event",
                "station": station,
                "timestamp": timestamp.isoformat(),
                "event_type": event_type,
                "sampling_rate": self.sampling_rate,
                "duration": len(data) / self.sampling_rate,
                "max_amplitude": float(np.max(np.abs(data))),
                "rms": float(np.sqrt(np.mean(data**2)))
            }

            if event_type == "event_triggered":
                filename = f"{station}_event_{timestamp.strftime('%Y%m%d_%H%M%S')}.npy"
                file_id = self.fs.put(data.tobytes(), filename=filename, compress='gzip')
                metadata.update({
                    "file_id": file_id,
                    "filename": filename,
                    "compressed_size": len(data.tobytes())
                })

            self.collection.insert_one(metadata)
            logger.info(f"💾 Salvati dati evento {event_type} per {station}")
            print(f"💾 Salvati dati evento {event_type} per {station}")

        except Exception as e:
            logger.error(f"❌ Errore salvataggio evento {station}: {e}")
            logger.error(traceback.format_exc())

    def _aggregate_data(self, station, data, timestamp):
        try:
            current_time = time.time()

            if station not in self.aggregated_data:
                self.aggregated_data[station] = {
                    'count': 0,
                    'sum': 0.0,
                    'sum_sq': 0.0,
                    'min': float('inf'),
                    'max': float('-inf'),
                    'start_time': current_time,
                    'samples': 0
                }

            agg = self.aggregated_data[station]
            agg['count'] += 1
            agg['sum'] += np.sum(data)
            agg['sum_sq'] += np.sum(data**2)
            agg['min'] = min(agg['min'], np.min(data))
            agg['max'] = max(agg['max'], np.max(data))
            agg['samples'] += len(data)

            if current_time - agg['start_time'] >= self.aggregation_interval:
                self._save_aggregated_data(station, agg, timestamp)
                self.aggregated_data[station] = {
                    'count': 0,
                    'sum': 0.0,
                    'sum_sq': 0.0,
                    'min': float('inf'),
                    'max': float('-inf'),
                    'start_time': current_time,
                    'samples': 0
                }

        except Exception as e:
            logger.error(f"❌ Errore aggregazione dati {station}: {e}")
            logger.error(traceback.format_exc())
    def _save_aggregated_data(self, station, aggregated, timestamp):
        try:
            if aggregated['count'] == 0:
                logger.warning(f"[DB] Nessun dato aggregato da salvare per {station}")
                return False

            duration = time.time() - aggregated['start_time']
            mean = aggregated['sum'] / aggregated['samples']
            variance = (aggregated['sum_sq'] / aggregated['samples']) - (mean ** 2)
            std_dev = np.sqrt(variance) if variance > 0 else 0

            metadata = {
                "type": "aggregated_data",
                "station": station,
                "start_time": datetime.fromtimestamp(aggregated['start_time']).isoformat(),
                "end_time": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": duration,
                "sample_count": aggregated['samples'],
                "sampling_rate": self.sampling_rate,
                "min_amplitude": float(aggregated['min']),
                "max_amplitude": float(aggregated['max']),
                "mean_amplitude": float(mean),
                "std_dev_amplitude": float(std_dev),
                "timestamp": timestamp.isoformat()
            }

            result = self.collection.insert_one(metadata)

            if result.inserted_id:
                logger.info(f"[DB] Salvati {aggregated['samples']} campioni per {station} "
                            f"(durata: {duration:.1f}s, ID: {result.inserted_id})")
                return True
            else:
                logger.error(f"[DB] Errore salvataggio aggregati per {station}")
                return False

        except Exception as e:
            logger.error(f"[DB] Errore salvataggio aggregati {station}: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    def detect_event(self, data):
        """Rileva evento sismico nei dati"""
        if data is None or len(data) == 0:
            return None

        window_size = int(5 * self.sampling_rate)
        if len(data) < window_size:
            return None

        window = data[-window_size:]
        rms = np.sqrt(np.mean(window**2))
        max_amplitude = float(np.max(np.abs(window)))
        logger.info(f"[DEBUG] RMS={rms:.3f} (threshold={self.event_threshold})")

        if rms > self.event_threshold:
            return {
                'event_detected': True,
                'rms': float(rms),
                'max_amplitude': max_amplitude,
                'window_start': len(data) - window_size,
                'window_end': len(data),
                'weak_event': False
            }
        elif rms > 0.2 * self.event_threshold:  # Considera "debole" se almeno il 20% della soglia
            return {
                'event_detected': True,
                'rms': float(rms),
                'max_amplitude': max_amplitude,
                'window_start': len(data) - window_size,
                'window_end': len(data),
                'weak_event': True
            }
        return None
    def pick_p_wave(self, data, event_start_sample=None):
        """Picking automatico onda P"""
        if data is None:
            return None

        if event_start_sample is None:
            event = self.detect_event(data)
            if event is None:
                return None
            event_start_sample = event['window_start']

        search_window = int(10 * self.sampling_rate)
        if event_start_sample + search_window > len(data):
            search_window = len(data) - event_start_sample
        if search_window <= 0:
            return None

        search_data = data[event_start_sample:event_start_sample + search_window]
        sta_window = int(0.5 * self.sampling_rate)
        lta_window = int(5 * self.sampling_rate)

        if len(search_data) < lta_window:
            return None

        sta = np.convolve(search_data**2, np.ones(sta_window)/sta_window, mode='same')
        lta = np.convolve(search_data**2, np.ones(lta_window)/lta_window, mode='same')
        ratio = sta / (lta + 1e-10)

        peaks = np.where(ratio > self.pick_threshold)[0]
        if len(peaks) > 0:
            return (event_start_sample + peaks[0]) / self.sampling_rate

        return None

    def analyze_all_stations(self):
        """Analizza tutte le stazioni per rilevare eventi"""
        results = {}
        timestamp = datetime.now(timezone.utc)
        logger.info(f"[ANALISI] Avvio analisi di {len(self.stations)} stazioni")

        for station, coords in self.stations.items():
            logger.info(f"[ANALISI] Stazione {station} - {coords['name']}")
            data = self.acquire_data(station)

            if data is not None:
                event = self.detect_event(data)
                logger.info(f"[DEBUG] Risultato detect_event per {station}: {event}")
                self.save_data_to_mongodb(
                    station,
                    data,
                    timestamp,
                    event_detected=(event is not None)
                )

                if event:
                    p_arrival = self.pick_p_wave(data, event['window_start'])
                    results[station] = {
                        'event_detected': True,
                        'p_arrival_time': p_arrival,
                        'max_amplitude': event['max_amplitude'],
                        'event_time': timestamp.isoformat(),
                        'coordinates': (coords['lat'], coords['lon']),
                        'data_available': True
                    }
                    logger.info(f"✅ Evento rilevato su {station} - Ampiezza: {event['max_amplitude']:.2f}")
                else:
                    results[station] = {
                        'event_detected': False,
                        'p_arrival_time': None,
                        'event_time': None,
                        'coordinates': (coords['lat'], coords['lon']),
                        'data_available': True
                    }
            else:
                logger.warning(f"[DEBUG] Nessun dato acquisito per {station}")
                results[station] = {
                    'event_detected': False,
                    'p_arrival_time': None,
                    'event_time': None,
                    'coordinates': (coords['lat'], coords['lon']),
                    'data_available': False
                }
                logger.warning(f"⚠️ Nessun dato disponibile per {station}")

        return results, timestamp

    def triangulate_epicenter(self, detection_results):
        """Triangola epicentro usando le stazioni con picking valido"""
        valid_stations = {
            name: data for name, data in detection_results.items()
            if data['event_detected'] and data['p_arrival_time'] is not None
        }

        if len(valid_stations) < 3:
            logger.warning(f"❌ Solo {len(valid_stations)} stazioni valide. Servono almeno 3.")
            return None

        reference_station = min(valid_stations.items(), key=lambda x: x[1]['p_arrival_time'])
        ref_name, ref_data = reference_station
        ref_time = ref_data['p_arrival_time']

        time_diffs = {
            name: data['p_arrival_time'] - ref_time
            for name, data in valid_stations.items()
        }

        try:
            epicenter_lat, epicenter_lon, uncertainty_km, stations_used = self.calculate_epicenter(valid_stations, time_diffs)
            logger.info(f"🌍 Epicentro calcolato: {epicenter_lat:.4f}, {epicenter_lon:.4f} ± {uncertainty_km:.1f} km")
            return {
                'epicenter': (epicenter_lat, epicenter_lon),
                'uncertainty_km': uncertainty_km,
                'stations_used': stations_used,
                'time_diffs': time_diffs,
                'valid_stations': valid_stations
            }
        except Exception as e:
            logger.error(f"❌ Errore triangolazione: {e}")
            logger.error(traceback.format_exc())
            return None

    def calculate_epicenter(self, valid_stations, time_diffs):
        """
        Calcolo semplificato dell'epicentro usando medie pesate sui ritardi.
        """
        latitudes = []
        longitudes = []
        weights = []

        for name, data in valid_stations.items():
            lat, lon = data['coordinates']
            delay = abs(time_diffs.get(name, 0)) + 0.01  # evita divisione per zero
            latitudes.append(lat)
            longitudes.append(lon)
            weights.append(1 / delay)

        weighted_lat = np.average(latitudes, weights=weights)
        weighted_lon = np.average(longitudes, weights=weights)
        uncertainty_km = np.std(latitudes) + np.std(longitudes)

        return weighted_lat, weighted_lon, uncertainty_km, list(valid_stations.keys())

    def run_detection_cycle(self):
        """Esegue un ciclo completo di rilevamento e triangolazione"""
        logger.info("🚀 Avvio ciclo di rilevamento sismico")
        detection_results, timestamp = self.analyze_all_stations()

        stations_with_data = sum(1 for d in detection_results.values() if d['data_available'])
        stations_with_events = sum(1 for d in detection_results.values() if d['event_detected'])

        # Log delle statistiche
        logger.info(f"📊 Stazioni con dati: {stations_with_data}/{len(self.stations)}")
        print(f"📊 Stazioni con dati: {stations_with_data}/{len(self.stations)}")
        logger.info(f"📊 Stazioni con eventi: {stations_with_events}/{len(self.stations)}")
        print(f"📊 Stazioni con eventi: {stations_with_events}/{len(self.stations)}")
        
        # 🔧 MODIFICATO: validazione evento se ≥3 stazioni con p_arrival valido
        valid_stations = {
            name: data for name, data in detection_results.items()
            if data['event_detected'] and data['p_arrival_time'] is not None
        }
        
        # Triangolazione se abbiamo abbastanza stazioni
        if len(valid_stations) >= 3:
            epicenter = self.triangulate_epicenter(valid_stations)
            if epicenter:
                lat, lon = epicenter['epicenter']
                uncertainty = epicenter['uncertainty_km']
                logger.info(f"🌍 Epicentro calcolato: {lat}, {lon} ± {uncertainty} km")
                print(f"🌍 Epicentro calcolato: {lat}, {lon} ± {uncertainty} km")
                
                # Salva la triangolazione
                triangulation_data = {
                    'timestamp': datetime.now(),
                    'epicenter': {'lat': lat, 'lon': lon, 'uncertainty': uncertainty},
                    'stations_used': valid_stations,
                    'weak_event': any(event.get('weak_event', False) for event in detection_results.values())
                }
                self.save_triangulation_to_mongodb(
                    epicenter['epicenter'],
                    epicenter['time_diffs'],
                    epicenter['valid_stations'],
                    timestamp,
                    weak_event_confirmed=triangulation_data['weak_event']
                )
                
                logger.info(f"💾 Triangolazione salvata su MongoDB. Weak event: {triangulation_data['weak_event']}")
                print(f"💾 Triangolazione salvata su MongoDB. Weak event: {triangulation_data['weak_event']}")
                
                # Aggiorna la dashboard
                self.update_dashboard_data((lat, lon), epicenter['time_diffs'], epicenter['valid_stations'], timestamp)
                logger.info(f"📊 Dashboard aggiornata con nuovo epicentro: {lat}, {lon}")
                print(f"📊 Dashboard aggiornata con nuovo epicentro: {lat}, {lon}")
                
                logger.info(f"✅ Epicentro rilevato: {lat}, {lon}")
                print(f"✅ Epicentro rilevato: {lat}, {lon}")
            else:
                logger.info("❌ Nessun epicentro calcolato")
                print("❌ Nessun epicentro calcolato")
        else:
            logger.info(f"❌ Solo {len(valid_stations)} stazioni con dati validi. Servono almeno 3.")
            print(f"❌ Solo {len(valid_stations)} stazioni con dati validi. Servono almeno 3.")

        return {
            'success': False,
            'detection_results': detection_results,
            'timestamp': timestamp
        }

    def save_triangulation_to_mongodb(self, epicenter, time_diffs, valid_stations, timestamp, weak_event_confirmed=False):
        """Salva il risultato della triangolazione su MongoDB, includendo se l'evento è stato confermato come weak."""
        try:
            doc = {
                "type": "triangulation_result",
                "epicenter": {
                    "latitude": epicenter[0],
                    "longitude": epicenter[1]
                },
                "timestamp": timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp),
                "valid_stations": list(valid_stations.keys()) if isinstance(valid_stations, dict) else valid_stations,
                "time_differences": time_diffs,
                "weak_event_confirmed": weak_event_confirmed
            }
            self.collection.insert_one(doc)
            logger.info(f"💾 Triangolazione salvata su MongoDB. Weak event: {weak_event_confirmed}")
            
            # Aggiorna automaticamente il file dashboard_data.json
            self.update_dashboard_data(epicenter, time_diffs, valid_stations, timestamp)
            
        except Exception as e:
            logger.error(f"❌ Errore salvataggio triangolazione: {e}")
            logger.error(traceback.format_exc())

    def update_dashboard_data(self, epicenter, time_diffs, valid_stations, timestamp):
        """Aggiorna il file dashboard_data.json con i nuovi dati di triangolazione."""
        try:
            dashboard_data = {
                "timestamp": timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp),
                "lat": epicenter[0],
                "lon": epicenter[1],
                "stations": list(valid_stations.keys()) if isinstance(valid_stations, dict) else valid_stations,
                "time_diffs": time_diffs
            }
            
            with open("dashboard_data.json", "w") as f:
                json.dump(dashboard_data, f, indent=2)
            
            logger.info(f"📊 Dashboard aggiornata con nuovo epicentro: {epicenter[0]:.4f}, {epicenter[1]:.4f}")
            
        except Exception as e:
            logger.error(f"❌ Errore aggiornamento dashboard: {e}")
            logger.error(traceback.format_exc())

    def run_continuous_monitoring(self, interval_seconds=300):
        """Esegue monitoraggio continuo"""
        logger.info(f"🔄 Avvio monitoraggio continuo (intervallo: {interval_seconds}s)")
        self._last_cleanup = datetime.now(timezone.utc)
        cycle = 0

        while True:
            try:
                start_time = time.time()
                cycle += 1
                logger.info(f"🔁 Ciclo #{cycle} - {datetime.now(timezone.utc).isoformat()}")

                result = self.run_detection_cycle()

                if result.get('success'):
                    epicenter = result['epicenter']
                    logger.info(f"✅ Epicentro rilevato: {epicenter[0]:.4f}, {epicenter[1]:.4f}")
                else:
                    logger.info("ℹ️ Nessun epicentro rilevato in questo ciclo")

                elapsed = time.time() - start_time
                wait_time = max(0, interval_seconds - elapsed)

                if (datetime.now(timezone.utc) - self._last_cleanup).total_seconds() > self.cleanup_interval:
                    logger.info("🧹 Pulizia automatica in corso...")
                    self.cleanup_old_data()
                    self._last_cleanup = datetime.now(timezone.utc)

                if wait_time > 0:
                    logger.info(f"⏳ Prossimo ciclo tra {wait_time:.1f} secondi...")
                    print(f"⏳ Prossimo ciclo tra {wait_time:.1f} secondi...")
                    time.sleep(wait_time)

            except KeyboardInterrupt:
                logger.info("⏹ Monitoraggio interrotto manualmente")
                break
            except Exception as e:
                logger.error(f"⚠️ Errore nel ciclo: {e}")
                logger.error(traceback.format_exc())
                time.sleep(interval_seconds)

def main():
    system = SeismicDetectionSystem()
    system.run_continuous_monitoring(interval_seconds=60)

if __name__ == "__main__":
    main()
