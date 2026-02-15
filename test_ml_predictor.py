# dragon_bot_ml.py
import asyncio
import asyncpg
import json
import os
import logging
from datetime import datetime
from playwright.async_api import async_playwright
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from collections import deque

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MLPredictor:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.le = LabelEncoder()
        self.le.fit(['Banker', 'Player', 'Tie'])
        self.history = deque(maxlen=50)
        self.is_trained = False
        
    def add_round(self, winner):
        self.history.append(winner)
        
    def prepare_features(self, history_list):
        if len(history_list) < 10:
            return None
            
        features = []
        
        last_5 = history_list[-5:]
        for i, winner in enumerate(last_5):
            features.append(self.le.transform([winner])[0])
        
        last_10 = history_list[-10:]
        features.append(last_10.count('Banker'))
        features.append(last_10.count('Player'))
        features.append(last_10.count('Tie'))
        
        current_streak = 1
        if len(history_list) > 1:
            last = history_list[-1]
            for i in range(len(history_list)-2, -1, -1):
                if history_list[i] == last:
                    current_streak += 1
                else:
                    break
        features.append(current_streak)
        
        alternations = 0
        for i in range(len(last_10)-1):
            if last_10[i] != last_10[i+1]:
                alternations += 1
        features.append(alternations)
        
        return features
    
    def train(self, rounds_df):
        if len(rounds_df) < 20:
            logger.warning("Necesito mínimo 20 rondas para entrenar")
            return False
        
        X, y = [], []
        history_list = rounds_df['winner'].tolist()
        
        for i in range(10, len(history_list)):
            features = self.prepare_features(history_list[:i])
            if features:
                X.append(features)
                y.append(self.le.transform([history_list[i]])[0])
        
        if len(X) < 10:
            return False
        
        self.model.fit(X, y)
        self.is_trained = True
        
        accuracy = np.mean(self.model.predict(X) == y) * 100
        logger.info(f"🤖 Modelo entrenado - Accuracy: {accuracy:.2f}%")
        return True
    
    def predict_next(self):
        if not self.is_trained or len(self.history) < 10:
            return None, None
        
        features = self.prepare_features(list(self.history))
        if not features:
            return None, None
        
        pred_encoded = self.model.predict([features])[0]
        probabilities = self.model.predict_proba([features])[0]
        
        predicted_winner = self.le.inverse_transform([pred_encoded])[0]
        confidence = probabilities[pred_encoded] * 100
        
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
                
                CREATE INDEX IF NOT EXISTS idx_game_id ON baccarat_rounds(game_id);
                CREATE INDEX IF NOT EXISTS idx_timestamp ON baccarat_rounds(timestamp DESC);
            ''')
        logger.info("✓ Database initialized")
    
    async def save_round(self, data):
        if not data.get('game_id'):
            return
        if not data.get('winner'):
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
                    str(data.get('game_id')),
                    str(data.get('game_number', '')),
                    str(data.get('winner')),
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
                pass  # Silenciar errores de duplicados
    
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
                pass  # Silenciar errores
    
    async def update_prediction_result(self, game_id, actual_winner):
        if not game_id or not actual_winner:
            return
            
        async with self.pool.acquire() as conn:
            try:
                await conn.execute('''
                    UPDATE ml_predictions
                    SET actual_winner = $2,
                        was_correct = (predicted_winner = $2)
                    WHERE game_id = $1
                ''', str(game_id), str(actual_winner))
            except Exception as e:
                pass  # Silenciar errores
    
    async def get_recent_rounds(self, limit=100):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT winner, player_score, banker_score, is_natural, timestamp
                FROM baccarat_rounds
                ORDER BY timestamp DESC
                LIMIT $1
            ''', limit)
            return pd.DataFrame(rows, columns=['winner', 'player_score', 'banker_score', 'is_natural', 'timestamp'])

class DragonBot:
    def __init__(self, db, target_url):
        self.db = db
        self.target_url = target_url
        self.current_game_data = {}
        self.predictor = MLPredictor()
        self.last_prediction = None
        
    async def initialize_ml(self):
        logger.info("🤖 Inicializando ML Predictor...")
        df = await self.db.get_recent_rounds(100)
        
        if len(df) > 0:
            for winner in df['winner'].tolist()[::-1]:
                self.predictor.add_round(winner)
            self.predictor.train(df)
        else:
            logger.info("⏳ No hay datos históricos, esperando rondas...")
    
    async def run(self):
        await self.initialize_ml()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            
            def handle_websocket(ws):
                logger.info(f"✅ WebSocket connected")
                
                def on_frame(payload):
                    asyncio.create_task(self.process_message(payload))
                
                ws.on('framereceived', on_frame)
            
            page.on('websocket', handle_websocket)
            
            logger.info(f"🚀 Navegando a {self.target_url}")
            await page.goto(self.target_url, timeout=60000)
            
            try:
                await asyncio.sleep(999999)
            except KeyboardInterrupt:
                logger.info("⛔ Bot stopped")
            finally:
                await browser.close()
    
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
                
                predicted, confidence = self.predictor.predict_next()
                if predicted and self.current_game_data.get('game_id'):
                    self.last_prediction = (predicted, confidence)
                    await self.db.save_prediction(
                        self.current_game_data['game_id'],
                        predicted,
                        confidence
                    )
                    print(self.predictor.get_recommendation())
                
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
                self.current_game_data['lightning_multipliers'] = args.get('multipliers', {})
            
            elif msg_type == 'baccarat.resolved':
                args = data.get('args', {})
                result = args.get('result', {})
                
                winner = result.get('winner')
                game_id = args.get('gameId') or self.current_game_data.get('game_id')
                game_number = args.get('gameNumber') or self.current_game_data.get('game_number')
                
                if not game_id or not winner:
                    return
                
                round_data = {
                    'game_id': game_id,
                    'game_number': game_number,
                    'winner': winner,
                    'player_score': result.get('playerScore'),
                    'banker_score': result.get('bankerScore'),
                    'player_pair': result.get('playerPair', False),
                    'banker_pair': result.get('bankerPair', False),
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
                
                if self.last_prediction:
                    await self.db.update_prediction_result(game_id, winner)
                    
                    predicted, confidence = self.last_prediction
                    was_correct = (predicted == winner)
                    
                    logger.info(f"🎯 RESULTADO: {winner} | Predije: {predicted} | {'✅ CORRECTO' if was_correct else '❌ INCORRECTO'}")
                
                self.predictor.add_round(winner)
                
                if len(self.predictor.history) % 20 == 0 and len(self.predictor.history) >= 20:
                    df = await self.db.get_recent_rounds(100)
                    self.predictor.train(df)
                
                self.current_game_data = {}
                self.last_prediction = None
            
            elif msg_type == 'baccarat.gameWinners':
                args = data.get('args', {})
                if self.current_game_data.get('game_id'):
                    self.current_game_data['total_winners'] = args.get('totalWinners')
                    self.current_game_data['total_amount'] = args.get('totalAmount')
                    
        except Exception as e:
            pass  # Silenciar todos los errores de parsing

async def main():
    DB_URL = 'postgresql://localhost/dragon_bot'
    TARGET_URL = 'https://dragonslots-1.com/es/live-casino/game/evolution/xxxtremelightningbaccarat'
    
    db = DragonBotDB(DB_URL)
    await db.init()
    
    bot = DragonBot(db, TARGET_URL)
    
    logger.info("🚀 Dragon Bot ML started...")
    
    try:
        await bot.run()
    finally:
        if db.pool:
            await db.pool.close()

if __name__ == '__main__':
    asyncio.run(main())
