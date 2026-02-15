# dragon_bot_ml.py - CON AUTO-RECONEXIÓN Y ESTADÍSTICAS
import asyncio
import asyncpg
import json
import os
import logging
from datetime import datetime
from playwright.async_api import async_playwright
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import cross_val_score
from collections import deque
from baccarat_strategies import BaccaratStrategies
from telegram_notifier import TelegramNotifier
from road_analyzer import RoadAnalyzer
from src.lightning_tracker import LightningTracker
from src.bankroll_manager import BankrollManager
from src.config import LIGHTNING_FEE, BANKER_COMMISSION, INITIAL_BANKROLL, KELLY_FRACTION, MIN_EV_TO_BET, MULTIPLIER_HISTORY_SIZE

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MLPredictor:
    def __init__(self):
        self.model = XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=3,
            reg_alpha=0.1,
            reg_lambda=1.0,
            eval_metric='mlogloss',
            random_state=42
        )
        self.le = LabelEncoder()
        self.le.fit(['Banker', 'Player', 'Tie'])
        self.history = deque(maxlen=50)
        self.score_history = deque(maxlen=50)  # (player_score, banker_score)
        self.is_trained = False
        self.cv_accuracy = 0.0
        
    def add_round(self, winner, player_score=None, banker_score=None):
        self.history.append(winner)
        self.score_history.append((
            player_score if player_score is not None else 0,
            banker_score if banker_score is not None else 0
        ))
        
    def prepare_features(self, history_list, scores_list=None):
        """Features avanzadas: 30+ indicadores"""
        if len(history_list) < 10:
            return None
            
        features = []
        
        # === 1. ÚLTIMOS 5 RESULTADOS (encoded) [5 features] ===
        last_5 = history_list[-5:]
        for winner in last_5:
            features.append(self.le.transform([winner])[0])
        
        # === 2. CONTEOS EN VENTANAS [9 features] ===
        for window in [5, 10, 20]:
            recent = history_list[-window:] if len(history_list) >= window else history_list
            total = len(recent)
            features.append(recent.count('Banker') / total)
            features.append(recent.count('Player') / total)
            features.append(recent.count('Tie') / total)
        
        # === 3. RACHA ACTUAL [2 features] ===
        current_streak = 1
        last = history_list[-1]
        for i in range(len(history_list)-2, -1, -1):
            if history_list[i] == last:
                current_streak += 1
            else:
                break
        features.append(current_streak)
        features.append(self.le.transform([last])[0])  # dirección racha
        
        # === 4. ALTERNACIONES [2 features] ===
        last_10 = history_list[-10:]
        alternations = sum(
            1 for i in range(len(last_10)-1) if last_10[i] != last_10[i+1]
        )
        features.append(alternations / max(len(last_10)-1, 1))
        
        last_5_alt = history_list[-5:]
        alt_5 = sum(
            1 for i in range(len(last_5_alt)-1) if last_5_alt[i] != last_5_alt[i+1]
        )
        features.append(alt_5 / max(len(last_5_alt)-1, 1))
        
        # === 5. PATRONES DE MEMORIA (como Memory-3) [3 features] ===
        # Buscar cuántas veces el patrón de últimas 3 rondas ha aparecido
        # y qué siguió después
        if len(history_list) >= 4:
            pattern_3 = tuple(history_list[-3:])
            follow_b, follow_p, follow_count = 0, 0, 0
            for i in range(3, len(history_list) - 1):
                if tuple(history_list[i-3:i]) == pattern_3:
                    follow_count += 1
                    if history_list[i] == 'Banker':
                        follow_b += 1
                    elif history_list[i] == 'Player':
                        follow_p += 1
            if follow_count > 0:
                features.append(follow_b / follow_count)
                features.append(follow_p / follow_count)
                features.append(follow_count)
            else:
                features.append(0.5)
                features.append(0.5)
                features.append(0)
        else:
            features.append(0.5)
            features.append(0.5)
            features.append(0)
        
        # === 6. RACHAS HISTÓRICAS [2 features] ===
        # Promedio y máximo de longitud de rachas
        streaks = []
        s_len = 1
        for i in range(1, len(history_list)):
            if history_list[i] == history_list[i-1]:
                s_len += 1
            else:
                streaks.append(s_len)
                s_len = 1
        streaks.append(s_len)
        features.append(np.mean(streaks) if streaks else 1)
        features.append(max(streaks) if streaks else 1)
        
        # === 7. SCORES ESTADÍSTICOS [6 features] ===
        if scores_list and len(scores_list) >= 5:
            recent_scores = scores_list[-10:] if len(scores_list) >= 10 else scores_list
            p_scores = [s[0] for s in recent_scores]
            b_scores = [s[1] for s in recent_scores]
            features.append(np.mean(p_scores))
            features.append(np.mean(b_scores))
            features.append(np.std(p_scores) if len(p_scores) > 1 else 0)
            features.append(np.std(b_scores) if len(b_scores) > 1 else 0)
            # Score diff promedio
            features.append(np.mean([s[0] - s[1] for s in recent_scores]))
            # Naturales recientes (score >= 8)
            naturals = sum(1 for s in recent_scores if max(s) >= 8)
            features.append(naturals / len(recent_scores))
        else:
            features.extend([4.5, 4.5, 2.0, 2.0, 0.0, 0.3])
        
        # === 8. MOMENTUM [2 features] ===
        if len(history_list) >= 10:
            first_half = history_list[-10:-5]
            second_half = history_list[-5:]
            b_momentum = (second_half.count('Banker') / 5) - (first_half.count('Banker') / 5)
            p_momentum = (second_half.count('Player') / 5) - (first_half.count('Player') / 5)
            features.append(b_momentum)
            features.append(p_momentum)
        else:
            features.append(0)
            features.append(0)
        
        # Total: 5 + 9 + 2 + 2 + 3 + 2 + 6 + 2 = 31 features
        return features
    
    def train(self, rounds_df):
        if len(rounds_df) < 30:
            logger.warning("Necesito mínimo 30 rondas para entrenar")
            return False
        
        X, y = [], []
        history_list = rounds_df['winner'].tolist()
        
        # Construir lista de scores
        scores_list = []
        if 'player_score' in rounds_df.columns and 'banker_score' in rounds_df.columns:
            for _, row in rounds_df.iterrows():
                ps = row.get('player_score', 0) or 0
                bs = row.get('banker_score', 0) or 0
                scores_list.append((ps, bs))
        
        for i in range(10, len(history_list)):
            sc = scores_list[:i] if scores_list else None
            features = self.prepare_features(history_list[:i], sc)
            if features:
                X.append(features)
                y.append(self.le.transform([history_list[i]])[0])
        
        if len(X) < 20:
            return False
        
        X = np.array(X)
        y = np.array(y)
        
        # Entrenar con validación cruzada para medir accuracy real
        try:
            scores = cross_val_score(self.model, X, y, cv=5, scoring='accuracy')
            self.cv_accuracy = scores.mean() * 100
            logger.info(f"🤖 CV Accuracy: {self.cv_accuracy:.1f}% (+/- {scores.std()*100:.1f}%)")
        except Exception:
            self.cv_accuracy = 0
        
        self.model.fit(X, y)
        self.is_trained = True
        
        train_accuracy = np.mean(self.model.predict(X) == y) * 100
        logger.info(f"🤖 Modelo XGBoost entrenado - Train: {train_accuracy:.1f}% | CV: {self.cv_accuracy:.1f}%")
        return True
    
    def predict_next(self):
        if not self.is_trained or len(self.history) < 10:
            return None, None
        
        scores = list(self.score_history) if self.score_history else None
        features = self.prepare_features(list(self.history), scores)
        if not features:
            return None, None
        
        pred_encoded = self.model.predict([features])[0]
        probabilities = self.model.predict_proba([features])[0]
        
        predicted_winner = self.le.inverse_transform([pred_encoded])[0]
        confidence = probabilities[pred_encoded] * 100
        
        # Si la confianza es muy baja (< 40%), no vale la pena
        if confidence < 40:
            return None, None
        
        return predicted_winner, confidence
    
    def get_recommendation(self):
        predicted, confidence = self.predict_next()
        
        if not predicted:
            return "⏳ Esperando más datos..."
        
        streak_warning = ""
        if len(self.history) >= 5:
            last_5 = list(self.history)[-5:]
            if last_5.count('Banker') >= 4:
                streak_warning = "⚠️ Racha larga Banker"
            elif last_5.count('Player') >= 4:
                streak_warning = "⚠️ Racha larga Player"
        
        return f"""
╔════════════════════════════════════════╗
║       🎯 PREDICCIÓN ML                 ║
╠════════════════════════════════════════╣
║ Próxima ronda: {predicted:^23}║
║ Confianza: {confidence:>6.2f}%{' '*20}║
║ {streak_warning:<39}║
╚════════════════════════════════════════╝
        """

class DragonBotDB:
    def __init__(self, dsn):
        self.dsn = dsn
        self.pool = None
    
    async def init(self):
        self.pool = await asyncpg.create_pool(self.dsn, min_size=2, max_size=10)
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS baccarat_rounds (
                    id SERIAL PRIMARY KEY,
                    game_id VARCHAR(100) UNIQUE,
                    game_number VARCHAR(50),
                    timestamp TIMESTAMP DEFAULT NOW(),
                    winner VARCHAR(20),
                    player_score INT,
                    banker_score INT,
                    player_pair BOOLEAN,
                    banker_pair BOOLEAN,
                    is_natural BOOLEAN,
                    player_cards JSONB,
                    banker_cards JSONB,
                    lightning_multipliers JSONB,
                    winning_spots JSONB,
                    with_lightning BOOLEAN,
                    shoe_cards_out INT,
                    total_winners INT,
                    total_amount NUMERIC,
                    captured_at TIMESTAMP DEFAULT NOW()
                );
                
                CREATE TABLE IF NOT EXISTS ml_predictions (
                    id SERIAL PRIMARY KEY,
                    game_id VARCHAR(100),
                    predicted_winner VARCHAR(20),
                    confidence NUMERIC,
                    actual_winner VARCHAR(20),
                    was_correct BOOLEAN,
                    timestamp TIMESTAMP DEFAULT NOW()
                );
                
                CREATE TABLE IF NOT EXISTS baccarat_roads (
                    id SERIAL PRIMARY KEY,
                    game_id VARCHAR(100) UNIQUE,
                    timestamp TIMESTAMP DEFAULT NOW(),
                    big_road JSONB,
                    big_eye_road JSONB,
                    small_road JSONB,
                    cockroach_road JSONB,
                    bead_plate JSONB
                );
                
                CREATE TABLE IF NOT EXISTS strategy_votes (
                    id SERIAL PRIMARY KEY,
                    game_id VARCHAR(100) NOT NULL,
                    strategy_name VARCHAR(80) NOT NULL,
                    predicted_winner VARCHAR(20) NOT NULL,
                    actual_winner VARCHAR(20),
                    was_correct BOOLEAN,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_strategy_votes_game_id ON strategy_votes(game_id);
                CREATE INDEX IF NOT EXISTS idx_strategy_votes_name ON strategy_votes(strategy_name);
                
                CREATE INDEX IF NOT EXISTS idx_game_id ON baccarat_rounds(game_id);
                CREATE INDEX IF NOT EXISTS idx_timestamp ON baccarat_rounds(timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_roads_game_id ON baccarat_roads(game_id);
            ''')
        logger.info("✓ Database initialized")
    
    async def save_round(self, data):
        if not data.get('game_id') or not data.get('winner'):
            return
            
        async with self.pool.acquire() as conn:
            try:
                await conn.execute('''
                    INSERT INTO baccarat_rounds 
                    (game_id, game_number, winner, player_score, banker_score,
                     player_pair, banker_pair, is_natural, player_cards, banker_cards,
                     lightning_multipliers, winning_spots, with_lightning, 
                     shoe_cards_out, total_winners, total_amount)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                    ON CONFLICT (game_id) DO NOTHING
                ''',
                    str(data['game_id']),
                    str(data.get('game_number', '')),
                    str(data['winner']),
                    data.get('player_score'),
                    data.get('banker_score'),
                    data.get('player_pair', False),
                    data.get('banker_pair', False),
                    data.get('is_natural', False),
                    json.dumps(data.get('player_cards', [])),
                    json.dumps(data.get('banker_cards', [])),
                    json.dumps(data.get('lightning_multipliers', {})), 
                    json.dumps(data.get('winning_spots', [])),
                    data.get('with_lightning', False),
                    data.get('shoe_cards_out'),
                    data.get('total_winners'),
                    data.get('total_amount')
                )
                logger.info(f"✅ Guardada ronda {data.get('game_number')}: {data.get('winner')} ({data.get('banker_score')}-{data.get('player_score')})")
            except Exception as e:
                pass
    
    async def save_roads(self, game_id, roads_data):
        async with self.pool.acquire() as conn:
            try:
                await conn.execute('''
                    INSERT INTO baccarat_roads 
                    (game_id, big_road, big_eye_road, small_road, cockroach_road, bead_plate)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (game_id) DO UPDATE SET
                        big_road = EXCLUDED.big_road,
                        big_eye_road = EXCLUDED.big_eye_road,
                        small_road = EXCLUDED.small_road,
                        cockroach_road = EXCLUDED.cockroach_road,
                        bead_plate = EXCLUDED.bead_plate
                ''',
                    str(game_id),
                    json.dumps(roads_data.get('bigRoad', [])),
                    json.dumps(roads_data.get('bigEyeRoad', [])),
                    json.dumps(roads_data.get('smallRoad', [])),
                    json.dumps(roads_data.get('cockroachRoad', [])),
                    json.dumps(roads_data.get('beadPlate', []))
                )
                logger.info(f"📊 Roads guardados para game {game_id}")
            except Exception as e:
                pass
    
    async def save_prediction(self, game_id, predicted, confidence):
        if not game_id or not predicted:
            return
            
        async with self.pool.acquire() as conn:
            try:
                await conn.execute('''
                    INSERT INTO ml_predictions (game_id, predicted_winner, confidence)
                    VALUES ($1, $2, $3)
                ''', str(game_id), str(predicted), float(confidence))
            except Exception as e:
                pass
    
    async def update_prediction_result(self, game_id, actual_winner):
        if not game_id or not actual_winner:
            return 0
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute('''
                    UPDATE ml_predictions
                    SET actual_winner = $2::varchar,
                        was_correct = (predicted_winner = $2::varchar)
                    WHERE game_id = $1::varchar AND actual_winner IS NULL
                ''', str(game_id), str(actual_winner))
                count = int(result.split()[-1]) if result else 0
                return count
        except Exception as e:
            logger.warning(f"Error update_prediction_result: {e}")
            return 0

    async def save_strategy_votes(self, game_id, strategies_list):
        """Registrar voto de cada estrategia para esta mano (para precisión por estrategia)."""
        if not game_id or not strategies_list:
            return
        async with self.pool.acquire() as conn:
            try:
                for s in strategies_list:
                    name = s.get('strategy') or s.get('type') or 'unknown'
                    pred = s.get('predicted') or s.get('prediction')
                    if not name or not pred:
                        continue
                    await conn.execute('''
                        INSERT INTO strategy_votes (game_id, strategy_name, predicted_winner)
                        VALUES ($1, $2, $3)
                    ''', str(game_id), str(name), str(pred))
            except Exception as e:
                logger.debug(f"save_strategy_votes: {e}")

    async def update_strategy_votes_result(self, game_id, actual_winner):
        """Marcar acierto/fallo de cada voto cuando se resuelve la ronda."""
        if not game_id or not actual_winner:
            return 0
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute('''
                    UPDATE strategy_votes
                    SET actual_winner = $2::varchar, was_correct = (predicted_winner = $2::varchar)
                    WHERE game_id = $1::varchar AND actual_winner IS NULL
                ''', str(game_id), str(actual_winner))
                count = int(result.split()[-1]) if result else 0
                if count > 0:
                    logger.info(f"📊 Actualizado {count} votos de estrategia para {game_id[:12]}")
                return count
        except Exception as e:
            logger.warning(f"Error update_strategy_votes: {e}")
            return 0

    async def get_strategy_accuracy(self, min_votes=5):
        """Precisión por estrategia (solo con actual_winner ya rellenado)."""
        async with self.pool.acquire() as conn:
            try:
                rows = await conn.fetch('''
                    SELECT strategy_name,
                           COUNT(*) AS total,
                           SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) AS correct
                    FROM strategy_votes
                    WHERE actual_winner IS NOT NULL
                    GROUP BY strategy_name
                    HAVING COUNT(*) >= $1
                    ORDER BY (SUM(CASE WHEN was_correct THEN 1 ELSE 0 END)::numeric / NULLIF(COUNT(*), 0)) DESC
                ''', min_votes)
                return [
                    {
                        'strategy': r['strategy_name'],
                        'total': r['total'],
                        'correct': r['correct'],
                        'accuracy': round((r['correct'] / r['total'] * 100), 2) if r['total'] else 0,
                    }
                    for r in rows
                ]
            except Exception as e:
                logger.debug(f"get_strategy_accuracy: {e}")
                return []
    
    async def get_global_accuracy(self):
        """Obtener precisión global de predicciones"""
        async with self.pool.acquire() as conn:
            try:
                row = await conn.fetchrow('''
                    SELECT 
                        COUNT(*) AS total,
                        SUM(CASE WHEN predicted = actual_winner THEN 1 ELSE 0 END) AS correct
                    FROM predictions
                    WHERE actual_winner IS NOT NULL
                ''')
                return {
                    'correct': row['correct'] or 0,
                    'total': row['total'] or 0
                }
            except Exception as e:
                logger.debug(f"get_global_accuracy: {e}")
                return {'correct': 0, 'total': 0}
    
    async def get_recent_rounds(self, limit=100):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT winner, player_score, banker_score, is_natural, timestamp
                FROM baccarat_rounds
                ORDER BY timestamp DESC
                LIMIT $1
            ''', limit)
            return pd.DataFrame(rows, columns=['winner', 'player_score', 'banker_score', 'is_natural', 'timestamp'])
    
    async def get_recent_stats(self, limit=81):
        """Obtener estadísticas de las últimas N rondas"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT winner
                FROM baccarat_rounds
                ORDER BY timestamp DESC
                LIMIT $1
            ''', limit)
            
            stats = {'player': 0, 'banker': 0, 'tie': 0}
            for row in rows:
                winner = row['winner'].lower()
                if winner in stats:
                    stats[winner] += 1
            
            return stats
    
    async def get_total_prediction_stats(self):
        """Obtener estadísticas totales de predicciones"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE was_correct = true) as correct
                FROM ml_predictions
                WHERE actual_winner IS NOT NULL
            ''')
            
            return {
                'total': row['total'] if row else 0,
                'correct': row['correct'] if row else 0
            }

class DragonBot:
    def __init__(self, db, target_url, user_data_dir='./browser_data'):
        self.db = db
        self.target_url = target_url
        self.user_data_dir = user_data_dir
        self.current_game_data = {}
        self.predictor = MLPredictor()
        self.strategies = BaccaratStrategies(db=self.db)
        self.road_analyzer = RoadAnalyzer()
        self.last_prediction = None
        self.reconnect_attempts = 0
        self.max_reconnects = 999
        self._strategy_report_count = 0
        self.websocket_alive = False
        self.last_message_time = datetime.now()
        self._last_shoe_game_count = 0
        self._shoe_synced = False
        # Stats reales del zapato actual de Evolution Gaming
        self.shoe_stats = {
            'player': 0, 'banker': 0, 'tie': 0,
            'player_pairs': 0, 'banker_pairs': 0
        }
        
        # Lightning Tracker y Bankroll Manager
        self.lightning_tracker = LightningTracker(history_size=MULTIPLIER_HISTORY_SIZE)
        self.bankroll_manager = BankrollManager(
            initial_bankroll=INITIAL_BANKROLL,
            lightning_fee=LIGHTNING_FEE,
            banker_commission=BANKER_COMMISSION,
            kelly_fraction=KELLY_FRACTION,
            min_ev=MIN_EV_TO_BET
        )
        
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.telegram = TelegramNotifier(telegram_token, telegram_chat_id)
        # Solo enviar señal a Telegram si confianza >= este umbral (default 50%)
        self.min_confidence_to_send = float(os.getenv("MIN_CONFIDENCE_TO_SEND", "50"))
        
    async def initialize_ml(self):
        logger.info("🤖 Inicializando ML Predictor...")
        
        # ML: cargar TODOS los datos para mejor entrenamiento
        df_ml = await self.db.get_recent_rounds(500)
        # Estrategias: solo últimas 20 del shoe
        df = await self.db.get_recent_rounds(20)
        
        if len(df_ml) > 0:
            # ML entrena con todos los datos históricos
            for _, row in df_ml.iterrows():
                self.predictor.add_round(
                    row['winner'],
                    row.get('player_score', 0) or 0,
                    row.get('banker_score', 0) or 0
                )
            self.predictor.train(df_ml)
            
            # Estrategias usan solo las últimas 20 rondas
            for _, row in df.iterrows():
                self.strategies.add_round(
                    row['winner'],
                    row.get('player_score', 0) or 0,
                    row.get('banker_score', 0) or 0,
                    row.get('player_pair', False),
                    row.get('banker_pair', False)
                )
            logger.info(f"🤖 ML entrenado y estrategias inicializadas con {len(df)} rondas")
        else:
            logger.info("⏳ No hay datos históricos, esperando rondas...")
    
    async def check_websocket_health(self):
        """Monitorear salud del WebSocket"""
        while True:
            await asyncio.sleep(45)  # Check cada 45 segundos
            
            time_since_last_msg = (datetime.now() - self.last_message_time).seconds
            
            if time_since_last_msg > 180:  # 3 minutos sin mensajes
                logger.warning(
                    f"⚠️ WebSocket inactivo por {time_since_last_msg}s, "
                    "iniciando reconexión..."
                )
                self.websocket_alive = False
                return
    
    async def run(self):
        """Ejecutar con auto-reconexión"""
        await self.initialize_ml()
        
        while True:
            try:
                logger.info(
                    f"🔄 Intento de conexión #{self.reconnect_attempts + 1}"
                )
                await self._run_bot()
            except KeyboardInterrupt:
                logger.info("⛔ Bot detenido por usuario")
                break
            except Exception as e:
                self.reconnect_attempts += 1
                logger.error(f"❌ Error: {e}", exc_info=True)
                
                wait_time = min(10 + (self.reconnect_attempts * 2), 60)
                logger.info(
                    f"⏳ Esperando {wait_time}s antes de reconectar..."
                )
                
                if self.reconnect_attempts % 5 == 0:
                    await self.telegram.send_message(
                        f"⚠️ <b>Bot reconectando</b>\n\n"
                        f"Intento #{self.reconnect_attempts}\n"
                        f"Último error: {str(e)[:100]}"
                    )
                
                await asyncio.sleep(wait_time)
    
    async def _run_bot(self):
        """Ejecutar una sesión del bot"""
        async with async_playwright() as p:
            os.makedirs(self.user_data_dir, exist_ok=True)
            
            context = await p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=False,
                channel='chrome',
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-blink-features=AutomationControlled'
                ],
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = context.pages[0] if context.pages else await context.new_page()
            
            self.websocket_alive = False
            self._shoe_synced = False  # Resetear sincronización en cada conexión
            
            def handle_websocket(ws):
                logger.info(f"✅ WebSocket connected")
                self.websocket_alive = True
                self.reconnect_attempts = 0
                
                def on_frame(payload):
                    self.last_message_time = datetime.now()
                    asyncio.create_task(self.process_message(payload))
                
                def on_close():
                    logger.warning("⚠️ WebSocket cerrado")
                    self.websocket_alive = False
                
                ws.on('framereceived', on_frame)
                ws.on('close', on_close)
            
            page.on('websocket', handle_websocket)
            
            logger.info(f"🚀 Navegando a {self.target_url}")
            await page.goto(self.target_url, timeout=60000)
            
            # Esperar a que cargue la página
            try:
                await page.wait_for_load_state('domcontentloaded', timeout=15000)
                logger.info("✅ Página cargada correctamente")
            except:
                logger.warning("⚠️ Página cargando...")
            
            # Esperar a que el WebSocket se conecte (máximo 45 segundos)
            logger.info("⏳ Esperando conexión WebSocket...")
            ws_timeout = 45
            while not self.websocket_alive and ws_timeout > 0:
                await asyncio.sleep(1)
                ws_timeout -= 1
            
            if self.websocket_alive:
                logger.info("✅ WebSocket conectado, iniciando...")
            else:
                logger.warning(
                    "⚠️ WebSocket no conectado tras 45s, continuando..."
                )
                await asyncio.sleep(5)
            
            # Mantener página activa
            async def keep_page_alive():
                while self.websocket_alive:
                    try:
                        await asyncio.sleep(45)
                        # Movimiento sutil del mouse para mantener sesión
                        await page.mouse.move(100, 100)
                    except Exception as e:
                        logger.debug(f"Keep alive error: {e}")
                        break
            
            health_check = asyncio.create_task(self.check_websocket_health())
            keep_alive = asyncio.create_task(keep_page_alive())
            
            try:
                while self.websocket_alive:
                    await asyncio.sleep(5)
                
                logger.warning("⚠️ Conexión perdida, reiniciando...")
                health_check.cancel()
                keep_alive.cancel()
                
            except KeyboardInterrupt:
                logger.info("⛔ Bot detenido manualmente")
                health_check.cancel()
                keep_alive.cancel()
                raise
            except Exception as e:
                logger.error(f"Error en bot loop: {e}", exc_info=True)
                health_check.cancel()
                keep_alive.cancel()
                raise
            finally:
                try:
                    await context.close()
                except Exception as e:
                    logger.debug(f"Error cerrando contexto: {e}")
    
    async def process_message(self, payload):
        if not isinstance(payload, str):
            return
        
        try:
            data = json.loads(payload)
            msg_type = data.get('type')
            
            if msg_type == 'baccarat.newGame':
                args = data.get('args', {})
                self.current_game_data = {
                    'game_id': args.get('gameId'),
                    'game_number': args.get('gameNumber'),
                    'shoe_cards_out': args.get('shoeCardsOut')
                }
                
                predicted_ml, confidence_ml = self.predictor.predict_next()
                advanced = self.strategies.get_advanced_prediction()
                consensus = advanced.get('consensus') if advanced else None
                predicted_st = consensus['predicted'] if consensus else None
                confidence_st = consensus['confidence'] if consensus else 0
                
                # Debug: qué predice cada componente
                strats_detail = ""
                if consensus and consensus.get('strategies'):
                    strats_detail = " | ".join([f"{s['strategy']}={s['predicted']}({s['confidence']:.0f}%)" for s in consensus['strategies']])
                ml_str = f"{predicted_ml}({confidence_ml:.1f}%)" if predicted_ml else "None"
                st_str = f"{predicted_st}({confidence_st:.1f}%)" if predicted_st else "None"
                logger.info(f"🔍 ML={ml_str} | Estrategias={st_str} [{strats_detail}]")
                
                if consensus and consensus.get('unanimous'):
                    confidence_st = min(confidence_st + 5, 95)  # bonus consenso unánime
                
                # Fusión ML + Estrategias: usar la mejor señal para no perder predicciones
                if predicted_ml and predicted_st:
                    if predicted_ml == predicted_st:
                        predicted = predicted_ml
                        confidence = max(confidence_ml, confidence_st)
                        if confidence > confidence_ml:
                            logger.info(f"📈 Boost consenso: ML {confidence_ml:.1f}% + estrategias {confidence_st:.1f}% → {confidence:.1f}%")
                    else:
                        if confidence_st >= confidence_ml:
                            predicted, confidence = predicted_st, confidence_st
                            logger.info(f"🔄 Usando estrategias ({confidence:.1f}%) > ML ({confidence_ml:.1f}%)")
                        else:
                            predicted, confidence = predicted_ml, confidence_ml
                elif predicted_st:
                    predicted, confidence = predicted_st, confidence_st
                elif predicted_ml:
                    predicted, confidence = predicted_ml, confidence_ml
                else:
                    predicted, confidence = None, 0
                
                if predicted and self.current_game_data.get('game_id'):
                    self.last_prediction = (predicted, confidence)
                    gid = self.current_game_data['game_id']
                    await self.db.save_prediction(gid, predicted, confidence)
                    if consensus and consensus.get('strategies'):
                        await self.db.save_strategy_votes(gid, consensus['strategies'])
                    print(self.predictor.get_recommendation())
                    
                    if confidence >= self.min_confidence_to_send:
                        deep_analysis = self.strategies.get_deep_analysis()
                        all_strategies = self.strategies.get_all_strategies_status()
                        viz_data = self.strategies.get_visualization_data()
                        
                        game_name = self.current_game_data.get('game_name', 'Baccarat')
                        # Usar stats del zapato de Evolution
                        recent_stats = self.shoe_stats
                        global_stats = await self.db.get_global_accuracy()
                        
                        player_pairs = self.shoe_stats.get(
                            'player_pairs', 0
                        )
                        banker_pairs = self.shoe_stats.get(
                            'banker_pairs', 0
                        )
                        
                        # Check if we have Lightning data
                        lightning_stats = self.lightning_tracker.get_stats()
                        has_lightning_data = lightning_stats['total_rounds'] > 0
                        
                        if has_lightning_data:
                            # Use Lightning prediction with EV calculations
                            avg_multiplier = self.lightning_tracker.get_ev_multiplier()
                            confidence_decimal = confidence / 100.0
                            
                            # Get EV signal from bankroll manager
                            ev_data = self.bankroll_manager.get_signal(
                                predicted,
                                confidence_decimal,
                                avg_multiplier
                            )
                            
                            # Format strategies detail
                            strategies_detail = ""
                            if consensus and consensus.get('strategies'):
                                for s in consensus['strategies']:
                                    strat_name = s.get('strategy', 'Unknown')
                                    strat_pred = s.get('predicted', '?')
                                    strat_conf = s.get('confidence', 0)
                                    strategies_detail += f"  • {strat_name}: {strat_pred} ({strat_conf:.0f}%)\n"
                            else:
                                strategies_detail = "  • Sin estrategias activas\n"
                            
                            # Format road display
                            road_display = viz_data.get('big_road', 'Sin datos')
                            
                            # Prepare game stats for Lightning message
                            game_stats_lightning = {
                                'recent_stats': recent_stats,
                                'total_stats': global_stats,
                                'table_name': game_name,
                                'game_id': gid
                            }
                            
                            await self.telegram.send_lightning_prediction(
                                prediction=predicted,
                                confidence=confidence,
                                ev_data=ev_data,
                                lightning_stats=lightning_stats,
                                strategies_detail=strategies_detail,
                                road_display=road_display,
                                game_stats=game_stats_lightning
                            )
                        else:
                            # Use standard comprehensive prediction when no Lightning data
                            await self.telegram.send_comprehensive_prediction({
                                'predicted': predicted,
                                'confidence': confidence,
                                'game_id': gid,
                                'game_number': args.get('gameNumber'),
                                'game_name': game_name,
                                'timestamp': datetime.now().strftime('%H:%M:%S'),
                                'strategies_data': {
                                    'consensus': consensus,
                                    'all_strategies': all_strategies
                                },
                                'deep_analysis': deep_analysis,
                                'recent_stats': recent_stats,
                                'pairs_data': {'player_pairs': player_pairs, 'banker_pairs': banker_pairs},
                                'shoe_cards_out': self.current_game_data.get('shoe_cards_out', 0),
                                'total_stats': global_stats,
                                'big_road': viz_data.get('big_road', ''),
                                'score_grid': viz_data.get('score_grid', ''),
                                'last_results': viz_data.get('last_results', '')
                            })

                    else:
                        logger.info(
                            f"ℹ️ Predicción {predicted} ({confidence:.1f}%) por debajo del umbral "
                            f"({self.min_confidence_to_send}%), no enviada a Telegram"
                        )
                
                logger.info(f"🎮 Nueva ronda: {args.get('gameNumber')}")
            
            elif msg_type == 'baccarat.cardDealt':
                args = data.get('args', {})
                game_data = args.get('gameData', {})
                
                player_hand = game_data.get('playerHand', {})
                banker_hand = game_data.get('bankerHand', {})
                
                self.current_game_data['player_cards'] = player_hand.get('cards', [])
                self.current_game_data['banker_cards'] = banker_hand.get('cards', [])
                self.current_game_data['player_score'] = player_hand.get('score')
                self.current_game_data['banker_score'] = banker_hand.get('score')
            
            elif msg_type == 'baccarat.potentialMultipliers':
                args = data.get('args', {})
                multipliers_dict = args.get('multipliers', {})
                self.current_game_data['lightning_multipliers'] = multipliers_dict
                
                # Record in Lightning tracker
                if multipliers_dict and self.current_game_data.get('game_id'):
                    self.lightning_tracker.record_round(
                        self.current_game_data['game_id'],
                        multipliers_dict
                    )
                    logger.debug(f"⚡ Lightning multipliers recorded: {multipliers_dict}")
            
            elif msg_type == 'baccarat.gameHistory':
                args = data.get('args', {})
                roads_data = args.get('roads', {})
                
                if roads_data:
                    self.road_analyzer.update_from_websocket(roads_data)
                    
                    if self.current_game_data.get('game_id'):
                        await self.db.save_roads(self.current_game_data['game_id'], roads_data)
            
            elif msg_type == 'baccarat.roads':
                args = data.get('args', {})
                self.road_analyzer.update_from_websocket(args)
                
                if self.current_game_data.get('game_id'):
                    await self.db.save_roads(self.current_game_data['game_id'], args)
            
            elif msg_type == 'baccarat.encodedShoeState':
                # FUENTE DE VERDAD: siempre sincronizar con Evolution
                args = data.get('args', {})
                history_v2 = args.get('history_v2', [])
                stats = args.get('stats', {})
                current_game_count = stats.get('gameCount', 0)
                
                if history_v2:
                    # Detectar cambio de zapato
                    is_new_shoe = (
                        current_game_count
                        < self._last_shoe_game_count
                    ) or (current_game_count <= 1)
                    
                    # Sincronizar estrategias
                    self.strategies.sync_from_shoe_history(
                        history_v2
                    )
                    
                    # Sincronizar predictor ML
                    self.predictor.history.clear()
                    self.predictor.score_history.clear()
                    for game in history_v2:
                        self.predictor.add_round(
                            game.get('winner'),
                            game.get('player_score', 0),
                            game.get('banker_score', 0)
                        )
                    
                    # Guardar stats reales del zapato
                    self.shoe_stats = {
                        'player': stats.get(
                            'playerWins', 0
                        ),
                        'banker': stats.get(
                            'bankerWins', 0
                        ),
                        'tie': stats.get('ties', 0),
                        'player_pairs': stats.get(
                            'playerPairs', 0
                        ),
                        'banker_pairs': stats.get(
                            'bankerPairs', 0
                        ),
                    }
                    
                    if not self._shoe_synced or is_new_shoe:
                        logger.info(
                            f"🔄 Sincronizado Evolution: "
                            f"{current_game_count} rondas "
                            f"P:{self.shoe_stats['player']} "
                            f"B:{self.shoe_stats['banker']} "
                            f"T:{self.shoe_stats['tie']}"
                        )
                        self._shoe_synced = True
                    
                    if is_new_shoe:
                        logger.info(
                            "🆕 Nuevo zapato detectado"
                        )
                
                self._last_shoe_game_count = current_game_count
            
            elif msg_type == 'baccarat.resolved':
                args = data.get('args', {})
                result = args.get('result', {})
                
                winner = result.get('winner')
                game_id = args.get('gameId') or self.current_game_data.get('game_id')
                game_number = args.get('gameNumber') or self.current_game_data.get('game_number')
                
                if not game_id or not winner:
                    return
                
                player_score = result.get('playerScore', 0)
                banker_score = result.get('bankerScore', 0)
                player_pair = result.get('playerPair', False)
                banker_pair = result.get('bankerPair', False)
                
                round_data = {
                    'game_id': game_id,
                    'game_number': game_number,
                    'winner': winner,
                    'player_score': player_score,
                    'banker_score': banker_score,
                    'player_pair': player_pair,
                    'banker_pair': banker_pair,
                    'is_natural': result.get('natural', False),
                    'winning_spots': args.get('winningSpots', []),
                    'with_lightning': args.get('withLightning', False),
                    'shoe_cards_out': self.current_game_data.get('shoe_cards_out'),
                    'total_winners': self.current_game_data.get('total_winners'),
                    'total_amount': self.current_game_data.get('total_amount'),
                    'player_cards': self.current_game_data.get('player_cards', []),
                    'banker_cards': self.current_game_data.get('banker_cards', []),
                    'lightning_multipliers': self.current_game_data.get('lightning_multipliers', {})
                }
                
                await self.db.save_round(round_data)
                
                # SIEMPRE actualizar resultados en DB (incluso tras reinicios)
                ml_updated = await self.db.update_prediction_result(game_id, winner)
                sv_updated = await self.db.update_strategy_votes_result(game_id, winner)
                
                if self.last_prediction:
                    self._strategy_report_count += 1
                    
                    predicted, confidence = self.last_prediction
                    was_correct = (predicted == winner)
                    
                    logger.info(f"🎯 RESULTADO: {winner} | Predije: {predicted} | {'✅ CORRECTO' if was_correct else '❌ INCORRECTO'}")
                    
                    # Reporte de precisión por estrategia cada 30 rondas resueltas
                    if self._strategy_report_count >= 30:
                        self._strategy_report_count = 0
                        acc_list = await self.db.get_strategy_accuracy(min_votes=3)
                        if acc_list:
                            lines = ["📊 <b>Precisión por estrategia</b> (uso real)\n"]
                            for i, row in enumerate(acc_list[:8], 1):
                                lines.append(
                                    f"  {i}. {row['strategy']}: {row['accuracy']:.1f}% ({row['correct']}/{row['total']})"
                                )
                            report = "\n".join(lines)
                            logger.info(f"Precisión estrategias:\n{report}")
                            await self.telegram.send_message(report)
                    
                    # Stats del zapato de Evolution
                    recent_stats = self.shoe_stats
                    total_stats = await self.db.get_total_prediction_stats()
                    
                    await self.telegram.send_result({
                        'predicted': predicted,
                        'actual': winner,
                        'was_correct': was_correct,
                        'confidence': confidence,
                        'game_id': game_id,
                        'game_number': game_number,
                        'player_cards': self.current_game_data.get('player_cards', []),
                        'banker_cards': self.current_game_data.get('banker_cards', []),
                        'player_score': player_score,
                        'banker_score': banker_score,
                        'shoe_cards_out': self.current_game_data.get('shoe_cards_out', 0),
                        'recent_stats': recent_stats,
                        'total_stats': total_stats
                    })
                elif ml_updated > 0:
                    # Tenía predicción pero bot reinició - actualizar silenciosamente
                    logger.info(f"🔄 Resultado {winner} actualizado retroactivamente (gid {game_id[:12]})")
                
                # NO agregar a strategies aquí - encodedShoeState
                # es la fuente de verdad y llega justo después
                # Re-entrenar ML cada 30 rondas con todos los datos
                if len(self.predictor.history) % 30 == 0 and len(self.predictor.history) >= 20:
                    df = await self.db.get_recent_rounds(500)
                    self.predictor.train(df)
                
                self.current_game_data = {}
                self.last_prediction = None
            
            elif msg_type == 'baccarat.gameWinners':
                args = data.get('args', {})
                if self.current_game_data.get('game_id'):
                    self.current_game_data['total_winners'] = args.get('totalWinners')
                    self.current_game_data['total_amount'] = args.get('totalAmount')
                    
        except Exception as e:
            if str(e):
                logger.warning(f"⚠️ Error procesando mensaje: {e}")

async def main():
    DB_URL = 'postgresql://localhost/dragon_bot'
    TARGET_URL = 'https://dragonslots-1.com/es/live-casino/game/evolution/xxxtremelightningbaccarat'
    
    db = DragonBotDB(DB_URL)
    await db.init()
    
    bot = DragonBot(db, TARGET_URL)
    
    logger.info("🚀 Dragon Bot ML + Auto-Reconexión + Estadísticas started...")
    
    try:
        await bot.run()
    finally:
        if db.pool:
            await db.pool.close()

if __name__ == '__main__':
    asyncio.run(main())
