#!/usr/bin/env python3
"""
Sistema Automatico di Rilevamento e Triangolazione Sismica
Database separato per il sistema di monitoraggio
"""

import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from obspy import UTCDateTime
from obspy.clients.fdsn import Client
from pymongo import MongoClient
from gridfs import GridFS
import time
import warnings
import json
import os
warnings.filterwarnings('ignore')

class SeismicDetectionSystem:
    def __init__(self):
        # Configurazione sistema
        self.sampling_rate = 100
        self.vp = 6.0  # km/s velocità onde P
        self.rete = "IV"
        self.canale = "HHZ"
        self.latenza_ingv = 300  # secondi (5 minuti)
        self.acquisition_duration = 600  # 10 minuti
        
        # Parametri rilevamento
        self.event_threshold = 1.0  # Aumentato da 0.1 a 1.0
        self.pick_threshold = 0.5   # Aumentato da 0.05 a 0.5
        
        # Configurazione gestione storage - OTTIMIZZATA
        self.max_days_to_keep = 7  # Massimo numero di giorni di dati da mantenere
        self.cleanup_interval = 6 * 3600  # Esegui pulizia ogni 6 ore
        self.max_raw_files_per_station = 10  # Massimo numero di file raw per stazione
        
        # Configurazione salvataggio dati
        self.save_raw_data = False  # Non salvare i dati grezzi di default
        self.save_aggregated = True  # Salva solo dati aggregati
        self.aggregation_interval = 300  # 5 minuti
        self.last_aggregation = {}
        self.aggregated_data = {}
        
        # Stato sistema
        self.last_event_time = None
        self.event_in_progress = False
        
        # MongoDB - Database monitoring con collection seismic_monitoring
        self.mongo_uri = "mongodb+srv://massimoserafini:QIs0axxmwPcEKS78@monitoring.auhw6a8.mongodb.net/?retryWrites=true&w=majority&appName=monitoring"
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client["monitoring"]  # Database monitoring
        self.collection = self.db["seismic_monitoring"]  # Collection seismic_monitoring
        self.fs = GridFS(self.db)
        
        # TUTTE LE 21 STAZIONI
        self.stations = {
            # Stazioni principali (con rulli)
            "TRIV": {"lat": 41.7666, "lon": 14.5502, "name": "Trivento"},
            "SACR": {"lat": 41.3974, "lon": 14.7057, "name": "S. Croce del Sannio"},
            "CIGN": {"lat": 41.65418, "lon": 14.90502, "name": "Sant'Elia a Pianisi"},
            
            # Stazioni aggiuntive
            "ASSB": {"lat": 43.0426, "lon": 12.6587, "name": "Assisi San Benedetto"},
            "BSSO": {"lat": 41.5461, "lon": 14.5938, "name": "Busso"},
            "CAMP": {"lat": 42.53578, "lon": 13.409, "name": "CAMPOTOSTO"},
            "CDCA": {"lat": 43.4584, "lon": 12.2336, "name": "Citta di Castello"},
            "CESI": {"lat": 43.0049, "lon": 12.9046, "name": "Cesi-Serravalle di Chienti"},
            "LOCA": {"lat": 43.30644, "lon": 11.26226, "name": "LOCA"},
            "LPEL": {"lat": 42.0468, "lon": 14.1832, "name": "Lama dei Peligni"},
            "MCI": {"lat": 41.491036, "lon": 13.813008, "name": "Montecassino"},
            "MIDA": {"lat": 41.64188, "lon": 14.25402, "name": "MIRANDA"},
            "MOMA": {"lat": 42.80387, "lon": 12.570071, "name": "Monte Martano"},
            "MRLC": {"lat": 40.7564, "lon": 15.48892, "name": "Muro Lucano"},
            "MSAG": {"lat": 41.712, "lon": 15.9096, "name": "Monte S. Angelo"},
            "NRCA": {"lat": 42.83355, "lon": 13.11427, "name": "NORCIA"},
            "POFI": {"lat": 41.71743, "lon": 13.71202, "name": "Posta Fibreno"},
            "SGRT": {"lat": 41.7546, "lon": 15.7437, "name": "San Giovanni Rotondo"},
            "TB01": {"lat": 43.381567, "lon": 12.435667, "name": "Gubbio"},
            "TSM3": {"lat": 43.38298, "lon": 12.354506, "name": "star site 3 Montone"},
            "TREM": {"lat": 42.123, "lon": 15.51, "name": "ISOLE TREMITI - SAN NICOLA"}
        }
        
        # Inizializza client INGV
        self.ingv_client = Client("INGV")
        
        print("🚀 Sistema di Rilevamento Sismico inizializzato")
        print(f"📡 Stazioni configurate: {len(self.stations)}")
        print(f"️ Database MongoDB: {self.db.name}")
        print(f"️ Collection: {self.collection.name}")
        print(f"️ URI: monitoring.auhw6a8.mongodb.net")
    
    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calcola distanza tra due punti geografici"""
        R = 6371  # raggio terrestre in km
        phi1, phi2 = np.radians(lat1), np.radians(lat2)
        dphi = np.radians(lat2 - lat1)
        dlambda = np.radians(lon2 - lon1)
        a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
        return 2*R*np.arcsin(np.sqrt(a))
    
    def acquire_data(self, station):
        """Acquisisce dati sismici da una stazione"""
        try:
            # Calcola finestra temporale
            end = UTCDateTime() - self.latenza_ingv
            start = end - self.acquisition_duration
            
            # Acquisizione dati
            st = self.ingv_client.get_waveforms(self.rete, station, "", self.canale, start, end)
            if len(st) > 0:
                tr = st[0]
                # Preprocessing
                tr.detrend("demean")
                tr.filter("bandpass", freqmin=0.5, freqmax=10.0)
                data = tr.data.astype(np.float64)
                data -= np.mean(data)
                return data
                
        except Exception as e:
            print(f"❌ Errore acquisizione {station}: {e}")
        
        return None
    
    def cleanup_old_data(self):
        """Elimina i dati più vecchi di max_days_to_keep giorni"""
        try:
            # Calcola la data di cutoff
            cutoff_date = datetime.utcnow() - timedelta(days=self.max_days_to_keep)
            
            # Trova i file da eliminare
            old_files = list(self.collection.find({
                "timestamp": {"$lt": cutoff_date.isoformat()},
                "type": "seismic_data"
            }))
            
            # Elimina i file vecchi
            for file_meta in old_files:
                try:
                    # Elimina il file da GridFS
                    self.fs.delete(file_meta["file_id"])
                    # Elimina il metadato
                    self.collection.delete_one({"_id": file_meta["_id"]})
                except Exception as e:
                    print(f"❌ Errore eliminazione file {file_meta.get('filename')}: {e}")
            
            # Per ogni stazione, mantieni solo gli ultimi N file raw
            stations = self.collection.distinct("station")
            for station in stations:
                try:
                    # Trova tutti i file per questa stazione, ordinati per data (più recenti prima)
                    station_files = list(self.collection.find({
                        "station": station,
                        "type": "seismic_data"
                    }).sort("timestamp", -1))
                    
                    # Se ci sono più file del massimo consentito, elimina i più vecchi
                    if len(station_files) > self.max_raw_files_per_station:
                        for file_meta in station_files[self.max_raw_files_per_station:]:
                            try:
                                self.fs.delete(file_meta["file_id"])
                                self.collection.delete_one({"_id": file_meta["_id"]})
                            except Exception as e:
                                print(f"❌ Errore eliminazione file {file_meta.get('filename')}: {e}")
                except Exception as e:
                    print(f"❌ Errore pulizia file stazione {station}: {e}")
            
            print(f"✅ Pulizia completata. Mantenuti solo gli ultimi {self.max_days_to_keep} giorni di dati.")
            return True
            
        except Exception as e:
            print(f"❌ Errore durante la pulizia dei dati: {e}")
            return False
            
    def save_data_to_mongodb(self, station, data, timestamp, event_detected=False):
        """Salva dati su MongoDB in modo ottimizzato"""
        if data is None:
            return None
            
        try:
            current_time = datetime.utcnow()
            
            # Esegui pulizia periodica
            if not hasattr(self, '_last_cleanup') or (current_time - self._last_cleanup).total_seconds() > self.cleanup_interval:
                self.cleanup_old_data()
                self._last_cleanup = current_time
            
            # Se c'è un evento, salva sempre i dati
            if event_detected:
                self._save_event_data(station, data, timestamp, "event_triggered")
                self.last_event_time = current_time
                self.event_in_progress = True
                return True
                
            # Se siamo in un periodo di post-evento, continua a salvare
            if self.event_in_progress:
                time_since_last_event = (current_time - self.last_event_time).total_seconds()
                if time_since_last_event < 300:  # 5 minuti dopo l'evento
                    self._save_event_data(station, data, timestamp, "post_event")
                    return True
                else:
                    self.event_in_progress = False
            
            # Altrimenti, aggrega i dati
            self._aggregate_data(station, data, timestamp)
            return True
            
        except Exception as e:
            print(f"❌ Errore salvataggio dati {station}: {e}")
            return None
    
    def _save_event_data(self, station, data, timestamp, event_type):
        """Salva i dati relativi a un evento sismico"""
        try:
            # Salva solo i metadati, non i dati grezzi
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
            
            # Se è un evento principale, salva anche i dati grezzi
            if event_type == "event_triggered":
                filename = f"{station}_event_{timestamp.strftime('%Y%m%d_%H%M%S')}.npy"
                file_id = self.fs.put(data.tobytes(), filename=filename, compress='gzip')
                metadata.update({
                    "file_id": file_id,
                    "filename": filename,
                    "compressed_size": len(data.tobytes())
                })
            
            self.collection.insert_one(metadata)
            print(f"💾 Salvati dati evento {event_type} per {station}")
            
        except Exception as e:
            print(f"❌ Errore salvataggio evento {station}: {e}")
    
    def _aggregate_data(self, station, data, timestamp):
        """Aggrega i dati per ridurre lo spazio di archiviazione"""
        try:
            current_time = time.time()
            
            # Inizializza aggregazione per questa stazione
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
            
            # Aggiorna statistiche
            agg = self.aggregated_data[station]
            agg['count'] += 1
            agg['sum'] += np.sum(data)
            agg['sum_sq'] += np.sum(data**2)
            agg['min'] = min(agg['min'], np.min(data))
            agg['max'] = max(agg['max'], np.max(data))
            agg['samples'] += len(data)
            
            # Se è passato abbastanza tempo, salva i dati aggregati
            if current_time - agg['start_time'] >= self.aggregation_interval:
                self._save_aggregated_data(station, agg, timestamp)
                # Resetta l'aggregazione
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
            print(f"❌ Errore aggregazione dati {station}: {e}")
    
    def _save_aggregated_data(self, station, aggregated, timestamp):
        """Salva i dati aggregati su MongoDB"""
        try:
            if aggregated['count'] == 0:
                return
                
            # Calcola statistiche
            duration = (time.time() - aggregated['start_time'])
            mean = aggregated['sum'] / aggregated['samples']
            variance = (aggregated['sum_sq'] / aggregated['samples']) - (mean ** 2)
            std_dev = np.sqrt(variance) if variance > 0 else 0
            
            metadata = {
                "type": "aggregated_data",
                "station": station,
                "start_time": datetime.fromtimestamp(aggregated['start_time']).isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "duration_seconds": duration,
                "sample_count": aggregated['samples'],
                "sampling_rate": self.sampling_rate,
                "min_amplitude": float(aggregated['min']),
                "max_amplitude": float(aggregated['max']),
                "mean_amplitude": float(mean),
                "std_dev_amplitude": float(std_dev),
                "timestamp": timestamp.isoformat()
            }
            
            self.collection.insert_one(metadata)
            print(f"📊 Salvati dati aggregati per {station} (durata: {duration:.1f}s)")
            
        except Exception as e:
            print(f"❌ Errore salvataggio aggregati {station}: {e}")
    
    def detect_event(self, data):
        """Rileva evento sismico nei dati"""
        if data is None or len(data) == 0:
            return None
            
        window_size = int(5 * self.sampling_rate)  # 5 secondi
        if len(data) < window_size:
            return None
            
        # Calcola RMS in modo efficiente
        window = data[-window_size:]  # Prendi solo l'ultima finestra
        rms = np.sqrt(np.mean(window**2))
        max_amplitude = float(np.max(np.abs(window)))
        
        # Controlla se supera la soglia principale
        if rms > self.event_threshold:
            return {
                'event_detected': True,
                'rms': float(rms),
                'max_amplitude': max_amplitude,
                'window_start': len(data) - window_size,
                'window_end': len(data),
                'event_strength': 'strong'
            }
        
        # Controlla se supera la soglia per eventi deboli (20% della soglia principale)
        weak_threshold = 0.2 * self.event_threshold
        if rms > weak_threshold:
            return {
                'event_detected': True,
                'rms': float(rms),
                'max_amplitude': max_amplitude,
                'window_start': len(data) - window_size,
                'window_end': len(data),
                'event_strength': 'weak'
            }
            
        return None
        
    def pick_p_wave(self, data, event_start_time=None):
        """Picking automatico onda P"""
        if data is None:
            return None
            
        if event_start_time is None:
            event_start_time = self.detect_event(data)
        
        if event_start_time is None:
            return None
        
        start_sample = int(event_start_time * self.sampling_rate)
        search_window = int(10 * self.sampling_rate)  # 10 secondi
        
        if start_sample + search_window > len(data):
            search_window = len(data) - start_sample
            
        if search_window <= 0:
            return None
            
        search_data = data[start_sample:start_sample + search_window]
        
        # Algoritmo STA/LTA
        sta_window = int(0.5 * self.sampling_rate)
        lta_window = int(5 * self.sampling_rate)
        
        if len(search_data) < lta_window:
            return None
        
        sta = np.convolve(search_data**2, np.ones(sta_window)/sta_window, mode='same')
        lta = np.convolve(search_data**2, np.ones(lta_window)/lta_window, mode='same')
        
        ratio = sta / (lta + 1e-10)
        
        # Trova primo picco sopra soglia
        peaks = np.where(ratio > self.pick_threshold)[0]
        
        if len(peaks) > 0:
            p_arrival_time = event_start_time + (peaks[0] / self.sampling_rate)
            return p_arrival_time
        
        return None
    
    def save_detection_results_to_mongodb(self, results, timestamp):
        """Salva risultati rilevamento su MongoDB"""
        try:
            detection_doc = {
                "type": "detection_result",
                "timestamp": timestamp.isoformat(),
                "day_key": timestamp.strftime("%Y-%m-%d"),
                "stations_analyzed": len(results),
                "results": {}
            }
            
            for station, data in results.items():
                detection_doc["results"][station] = {
                    "event_detected": data['event_detected'],
                    "p_arrival_time": data['p_arrival_time'],
                    "event_time": data['event_time'],
                    "data_available": data['data_available'],
                    "coordinates": data['coordinates']
                }
            
            self.collection.insert_one(detection_doc)
            return True
            
        except Exception as e:
            print(f"❌ Errore salvataggio risultati: {e}")
            return False
    
    def save_triangulation_to_mongodb(self, epicenter, time_diffs, valid_stations, timestamp):
        """Salva risultati triangolazione su MongoDB"""
        try:
            triangulation_doc = {
                "type": "triangulation_result",
                "timestamp": timestamp.isoformat(),
                "day_key": timestamp.strftime("%Y-%m-%d"),
                "epicenter": {
                    "latitude": epicenter[0],
                    "longitude": epicenter[1]
                },
                "time_differences": time_diffs,
                "valid_stations": list(valid_stations.keys()),
                "stations_used": len(valid_stations),
                "vp_velocity": self.vp
            }
            
            self.collection.insert_one(triangulation_doc)
            return True
            
        except Exception as e:
            print(f"❌ Errore salvataggio triangolazione: {e}")
            return False
    
    def analyze_all_stations(self):
        """Analizza tutte le stazioni per rilevare eventi"""
        results = {}
        timestamp = datetime.utcnow()
        
        for station, coords in self.stations.items():
            print(f"\n🔍 Analisi stazione {station} - {coords['name']}...")
            
            # Acquisisci i dati della stazione
            data = self.acquire_data(station)
            
            if data is not None:
                # Rileva eventi
                event = self.detect_event(data)
                
                # Salva i dati (solo se c'è un evento o per aggregazione)
                self.save_data_to_mongodb(
                    station, 
                    data, 
                    timestamp,
                    event_detected=(event is not None)
                )
                
                if event is not None:
                    # Se c'è un evento, fai il picking dell'onda P
                    p_arrival = self.pick_p_wave(data, event.get('window_start'))
                    
                    results[station] = {
                        'event_detected': True,
                        'p_arrival_time': p_arrival,
                        'max_amplitude': event['max_amplitude'],
                        'event_time': timestamp.isoformat(),
                        'coordinates': (coords['lat'], coords['lon']),
                        'data_available': True
                    }
                    print(f"✅ Evento rilevato! Ampiezza massima: {event['max_amplitude']:.2f}")
                else:
                    results[station] = {
                        'event_detected': False,
                        'p_arrival_time': None,
                        'event_time': None,
                        'coordinates': (coords['lat'], coords['lon']),
                        'data_available': True
                    }
                    print(f"❌ Nessun evento rilevato")
            else:
                results[station] = {
                    'event_detected': False,
                    'p_arrival_time': None,
                    'event_time': None,
                    'coordinates': (coords['lat'], coords['lon']),
                    'data_available': False
                }
                print(f"⚠️ Dati non disponibili per la stazione {station}")
        
        # Salva i risultati su MongoDB
        self.save_detection_results_to_mongodb(results, timestamp)
        
        return results, timestamp
    
    def find_close_station_group(self, event_stations, max_distance_km=100):
        """Restituisce la lista di almeno 3 stazioni tutte entro max_distance_km tra loro, oppure None."""
        from itertools import combinations
        if len(event_stations) < 3:
            return None
        # Crea tutte le terne possibili
        for group in combinations(event_stations, 3):
            coords = [self.stations[name]['lat'], self.stations[name]['lon']] if isinstance(self.stations[name], dict) else self.stations[name] for name in group
            d1 = self.haversine_distance(coords[0][0], coords[0][1], coords[1][0], coords[1][1])
            d2 = self.haversine_distance(coords[0][0], coords[0][1], coords[2][0], coords[2][1])
            d3 = self.haversine_distance(coords[1][0], coords[1][1], coords[2][0], coords[2][1])
            if d1 <= max_distance_km and d2 <= max_distance_km and d3 <= max_distance_km:
                return list(group)
        return None

    def triangulate_epicenter(self, detection_results):
        """Triangolazione solo se almeno 3 stazioni vicine rilevano evento."""
        # Filtra stazioni con eventi rilevati
        valid_stations = {name: data for name, data in detection_results.items() if data['event_detected']}
        if len(valid_stations) < 3:
            print(f"\n❌ Solo {len(valid_stations)} stazioni con eventi. Servono almeno 3.")
            return None
        # Trova gruppo di almeno 3 stazioni vicine
        close_group = self.find_close_station_group(list(valid_stations.keys()), max_distance_km=100)
        if not close_group:
            print("❌ Nessun gruppo di almeno 3 stazioni vicine (<100km) con evento. Nessuna triangolazione.")
            return None
        print(f"\n🔍 Triangolazione con stazioni vicine: {close_group}")
        group_data = {name: valid_stations[name] for name in close_group}
        # Procedi come prima, stimando i tempi se necessario
        if not any(data.get('p_arrival_time') for data in group_data.values()):
            print("📊 Stimando tempi di arrivo basati su epicentro approssimativo...")
            lats = [data['coordinates'][0] for data in group_data.values()]
            lons = [data['coordinates'][1] for data in group_data.values()]
            approx_epicenter_lat = np.mean(lats)
            approx_epicenter_lon = np.mean(lons)
            simulated_times = {}
            for name, data in group_data.items():
                station_lat, station_lon = data['coordinates']
                distance = self.haversine_distance(approx_epicenter_lat, approx_epicenter_lon, station_lat, station_lon)
                arrival_time = distance / self.vp
                simulated_times[name] = arrival_time
                print(f"  {name}: Tempo simulato = {arrival_time:.2f}s (distanza: {distance:.1f}km)")
            time_diffs = {}
            min_time = min(simulated_times.values())
            for name, time in simulated_times.items():
                time_diffs[name] = time - min_time
            epicenter = self.calculate_epicenter(group_data, time_diffs)
            return epicenter, time_diffs, group_data
        else:
            precise_stations = {name: data for name, data in group_data.items() if data.get('p_arrival_time') is not None}
            if len(precise_stations) >= 3:
                print(f"🎯 Usando {len(precise_stations)} stazioni con picking preciso")
                reference_station = min(precise_stations.items(), key=lambda x: x[1]['p_arrival_time'])
                print(f"🎯 Stazione di riferimento: {reference_station[0]}")
                time_diffs = {}
                for name, data in precise_stations.items():
                    time_diff = data['p_arrival_time'] - reference_station[1]['p_arrival_time']
                    time_diffs[name] = time_diff
                epicenter = self.calculate_epicenter(precise_stations, time_diffs)
                return epicenter, time_diffs, precise_stations
            else:
                print(f"⚠️ Solo {len(precise_stations)} stazioni con picking preciso, usando approccio misto")
                return self.triangulate_epicenter(group_data)
    
    def calculate_epicenter(self, stations, time_diffs):
        """Calcola epicentro usando triangolazione"""
        # Implementazione semplificata - in produzione usa algoritmi più sofisticati
        
        # Calcola epicentro approssimativo
        lats = [data['coordinates'][0] for data in stations.values()]
        lons = [data['coordinates'][1] for data in stations.values()]
        
        # Epicentro approssimativo (centroide delle stazioni)
        epicenter_lat = np.mean(lats)
        epicenter_lon = np.mean(lons)
        
        return epicenter_lat, epicenter_lon
    
    def run_detection_cycle(self):
        """Esegue un ciclo completo di rilevamento e triangolazione"""
        print("🚀 AVVIO CICLO DI RILEVAMENTO SISMICO")
        print("=" * 60)
        print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # 1. Analisi tutte le stazioni
        detection_results, timestamp = self.analyze_all_stations()
        
        # 2. Statistiche
        stations_with_data = sum(1 for data in detection_results.values() if data['data_available'])
        stations_with_events = sum(1 for data in detection_results.values() if data['event_detected'])
        
        print(f"\n📊 STATISTICHE:")
        print(f"   Stazioni con dati: {stations_with_data}/{len(self.stations)}")
        print(f"   Stazioni con eventi: {stations_with_events}/{len(self.stations)}")
        
        # 3. Triangolazione se ci sono abbastanza eventi
        if stations_with_events >= 3:
            triangulation_result = self.triangulate_epicenter(detection_results)
            
            if triangulation_result is not None:
                epicenter, time_diffs, valid_stations = triangulation_result
                
                print(f"\n RISULTATO TRIANGOLAZIONE:")
                print(f"   Latitudine: {epicenter[0]:.4f}°")
                print(f"   Longitudine: {epicenter[1]:.4f}°")
                print(f"   Stazioni utilizzate: {len(valid_stations)}")
                
                # Salva triangolazione su MongoDB
                self.save_triangulation_to_mongodb(epicenter, time_diffs, valid_stations, timestamp)

                # Aggiorna anche il file dashboard_data.json
                dashboard_data = {
                    "timestamp": timestamp.isoformat(),
                    "lat": epicenter[0],
                    "lon": epicenter[1],
                    "stations": list(valid_stations.keys()),
                    "time_diffs": time_diffs
                }
                try:
                    with open("dashboard_data.json", "w") as f:
                        import json
                        json.dump(dashboard_data, f, indent=2)
                    print("[DASHBOARD] File dashboard_data.json aggiornato!")
                except Exception as e:
                    print(f"[DASHBOARD] Errore aggiornamento dashboard_data.json: {e}")

                # Genera anche index.html statico SOLO per CIGN, TRIV, SACR
                try:
                    # Estrai dati delle tre stazioni principali
                    main_stations = ['CIGN', 'TRIV', 'SACR']
                    station_cards = ''
                    for st in main_stations:
                        res = detection_results.get(st, {})
                        stato = 'OK' if res.get('data_available') else 'NO DATA'
                        stato_class = 'status-ok' if stato == 'OK' else 'status-error'
                        event = 'SI' if res.get('event_detected') else 'NO'
                        event_class = 'status-ok' if event == 'SI' else ''
                        p_pick = f"{res.get('p_arrival_time'):.2f}s" if res.get('p_arrival_time') is not None else '-'
                        
                        station_cards += f'''
                        <div class="station-card">
                            <div class="station-header">
                                <h3>{st} <span class="station-name">{self.stations.get(st, {{}}).get('name', '')}</span></h3>
                                <div class="status-indicator {stato_class}"></div>
                            </div>
                            <div class="station-details">
                                <div class="detail">
                                    <span class="label">Stato:</span>
                                    <span class="value {stato_class}">{stato}</span>
                                </div>
                                <div class="detail">
                                    <span class="label">Evento:</span>
                                    <span class="value {event_class}">{event}</span>
                                </div>
                                <div class="detail">
                                    <span class="label">P-pick:</span>
                                    <span class="value">{p_pick}</span>
                                </div>
                            </div>
                            <div class="station-actions">
                                <button class="btn-view" onclick="showRullo('{st}')">Visualizza Rullo</button>
                            </div>
                        </div>'''

                    # Se c'è epicentro, mostralo
                    epicentro_html = ''
                    if epicenter:
                        epicentro_html = f'''
                        <div class="epicentro">
                            <h3>Ultimo Epicentro Calcolato</h3>
                            <div class="epicenter-details">
                                <div class="detail">
                                    <span class="label">Data/Ora:</span>
                                    <span class="value">{dashboard_data['timestamp']}</span>
                                </div>
                                <div class="detail">
                                    <span class="label">Coordinate:</span>
                                    <span class="value">{dashboard_data['lat']}° N, {dashboard_data['lon']}° E</span>
                                </div>
                                <div class="detail">
                                    <span class="label">Stazioni usate:</span>
                                    <span class="value">{', '.join(dashboard_data['stations'])}</span>
                                </div>
                            </div>
                        </div>'''

                    html = f'''<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitoraggio Sismico in Tempo Reale</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #3498db;
            --success: #2ecc71;
            --warning: #f39c12;
            --danger: #e74c3c;
            --light: #ecf0f1;
            --dark: #2c3e50;
            --gray: #95a5a6;
            --card-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{ 
            font-family: 'Roboto', sans-serif;
            background-color: #f5f7fa;
            color: #333;
            line-height: 1.6;
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 15px;
        }}

        header {{
            text-align: center;
            margin-bottom: 30px;
            padding: 20px 0;
            border-bottom: 1px solid #e0e0e0;
        }}

        h1 {{
            color: var(--dark);
            font-size: 2.2rem;
            margin-bottom: 10px;
        }}

        .subtitle {{
            color: var(--gray);
            font-weight: 300;
        }}

        .stations-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}

        .station-card {{
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: var(--card-shadow);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}

        .station-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
        }}

        .station-header {{
            background: var(--dark);
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .station-header h3 {{
            margin: 0;
            font-size: 1.3rem;
        }}

        .station-name {{
            font-weight: 300;
            font-size: 0.9rem;
            opacity: 0.8;
        }}

        .status-indicator {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: var(--gray);
        }}

        .status-ok .status-indicator {{
            background: var(--success);
            box-shadow: 0 0 10px var(--success);
        }}

        .status-error .status-indicator {{
            background: var(--danger);
            box-shadow: 0 0 10px var(--danger);
        }}

        .station-details {{
            padding: 20px;
        }}

        .detail {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            padding-bottom: 10px;
            border-bottom: 1px solid #eee;
        }}

        .detail:last-child {{
            border-bottom: none;
            margin-bottom: 0;
            padding-bottom: 0;
        }}

        .label {{
            color: var(--gray);
            font-weight: 500;
        }}

        .value {{
            font-weight: 500;
        }}

        .status-ok .value {{
            color: var(--success);
        }}

        .status-error .value {{
            color: var(--danger);
        }}

        .station-actions {{
            padding: 0 20px 20px;
            text-align: center;
        }}

        .btn-view {{
            background: var(--primary);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.9rem;
            transition: background 0.3s ease;
            width: 100%;
        }}

        .btn-view:hover {{
            background: #2980b9;
        }}

        .epicentro {{
            background: white;
            border-radius: 10px;
            padding: 25px;
            margin: 30px 0;
            box-shadow: var(--card-shadow);
            border-left: 5px solid var(--primary);
        }}

        .epicenter-details {{
            margin-top: 15px;
        }}

        .map-container {{
            background: white;
            border-radius: 10px;
            height: 400px;
            margin: 30px 0;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: var(--card-shadow);
            background-color: #f8f9fa;
            border: 1px dashed #ccc;
        }}

        .last-update {{
            text-align: center;
            color: var(--gray);
            font-size: 0.85rem;
            margin-top: 40px;
        }}

        @media (max-width: 768px) {{
            .stations-grid {{
                grid-template-columns: 1fr;
            }}
            
            .container {{
                padding: 0 10px;
            }}
            
            h1 {{
                font-size: 1.8rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Monitoraggio Sismico in Tempo Reale</h1>
            <p class="subtitle">Stato aggiornato in tempo reale delle stazioni sismiche</p>
        </header>
        
        <div class="stations-grid">
            {station_cards}
        </div>
        
        {epicentro_html}
        
        <div class="map-container">
            <p>Mappa delle stazioni sismiche (in sviluppo)</p>
        </div>
        
        <div class="last-update">
            Ultimo aggiornamento: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>'''
                    
                    with open("index.html", "w") as f:
                        f.write(html)
                    print("[DASHBOARD] index.html aggiornato con design moderno!")
                except Exception as e:
                    print(f"[DASHBOARD] Errore aggiornamento index.html: {e}")

                return {
                    'success': True,
                    'epicenter': epicenter,
                    'time_diffs': time_diffs,
                    'valid_stations': valid_stations,
                    'detection_results': detection_results,
                    'timestamp': timestamp
                }
        else:
            print(f"\n❌ Eventi insufficienti per triangolazione ({stations_with_events}/3)")
        
        return {
            'success': False,
            'detection_results': detection_results,
            'timestamp': timestamp
        }
    
    def run_continuous_monitoring(self, interval_seconds=300):
        """Esegue monitoraggio continuo"""
        print(f"🚀 Avvio monitoraggio continuo (intervallo: {interval_seconds}s)")
        print(f"🔄 Pulizia automatica ogni {self.cleanup_interval/3600} ore")
        print(f"📅 Mantenimento massimo: {self.max_days_to_keep} giorni di dati")
        
        # Inizializza l'ultima pulizia
        self._last_cleanup = datetime.utcnow()
        
        # Esegui subito una pulizia iniziale
        self.cleanup_old_data()
        
        cycle = 0
        while True:
            try:
                start_time = time.time()
                
                # Esegui ciclo di rilevamento
                result = self.run_detection_cycle()
                
                if result['success']:
                    print(f"✅ Epicentro calcolato: {result['epicenter'][0]:.4f}, {result['epicenter'][1]:.4f}")
                else:
                    print("❌ Nessun epicentro calcolato")
                
                # Calcola tempo di attesa
                elapsed = time.time() - start_time
                wait_time = max(0, interval_seconds - elapsed)
                
                # Esegui pulizia se necessario
                if (datetime.utcnow() - self._last_cleanup).total_seconds() > self.cleanup_interval:
                    self.cleanup_old_data()
                    self._last_cleanup = datetime.utcnow()
                
                if wait_time > 0:
                    print(f"⏳ Prossimo ciclo tra {wait_time:.1f} secondi...")
                    time.sleep(wait_time)
                    
            except KeyboardInterrupt:
                print("\n⏹  Arresto richiesto dall'utente")
                break
                
            except Exception as e:
                print(f"⚠️  Errore nel ciclo di monitoraggio: {e}")
                print(f"Riprendo tra {interval_seconds} secondi...")
                time.sleep(interval_seconds)

# Funzione principale
def main():
    """Funzione principale"""
    system = SeismicDetectionSystem()
    
    # Monitoraggio continuo automatico senza input
    interval = 60  # Imposta qui l'intervallo desiderato in secondi (1 minuto)
    system.run_continuous_monitoring(interval)

if __name__ == "__main__":
    main()