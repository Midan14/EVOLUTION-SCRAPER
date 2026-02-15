# dragon_bot_advanced.py
import asyncio
import asyncpg
import json
import os
import logging
from datetime import datetime
from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DragonBotDB:
    def __init__(self, dsn):
        self.dsn = dsn
        self.pool = None
    
    async def init(self):
        self.pool = await asyncpg.create_pool(self.dsn, min_size=5, max_size=20)
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
                
                CREATE TABLE IF NOT EXISTS shoe_statistics (
                    id SERIAL PRIMARY KEY,
                    shoe_id VARCHAR(100),
                    timestamp TIMESTAMP DEFAULT NOW(),
                    game_count INT,
                    player_wins INT,
                    banker_wins INT,
                    ties INT,
                    player_pairs INT,
                    banker_pairs INT,
                    history_data JSONB,
                    UNIQUE(shoe_id, timestamp)
                );
                
                CREATE TABLE IF NOT EXISTS roadmaps (
                    id SERIAL PRIMARY KEY,
                    game_id VARCHAR(100),
                    timestamp TIMESTAMP DEFAULT NOW(),
                    big_road JSONB,
                    bead_road JSONB,
                    big_eye_boy JSONB,
                    small_road JSONB,
                    cockroach_road JSONB,
                    FOREIGN KEY (game_id) REFERENCES baccarat_rounds(game_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_game_id ON baccarat_rounds(game_id);
                CREATE INDEX IF NOT EXISTS idx_timestamp ON baccarat_rounds(timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_winner ON baccarat_rounds(winner);
                CREATE INDEX IF NOT EXISTS idx_shoe_id ON shoe_statistics(shoe_id);
            ''')
        logger.info("✓ Database initialized with roadmaps support")
    
    async def save_round(self, data):
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
                    data['game_id'],
                    data.get('game_number'),
                    data.get('winner'),
                    data.get('player_score'),
                    data.get('banker_score'),
                    data.get('player_pair'),
                    data.get('banker_pair'),
                    data.get('is_natural'),
                    json.dumps(data.get('player_cards', [])),
                    json.dumps(data.get('banker_cards', [])),
                    json.dumps(data.get('lightning_multipliers', {})),
                    json.dumps(data.get('winning_spots', [])),
                    data.get('with_lightning'),
                    data.get('shoe_cards_out'),
                    data.get('total_winners'),
                    data.get('total_amount')
                )
                logger.info(f"✓ Saved round {data['game_id']}: {data.get('winner')} wins")
            except Exception as e:
                logger.error(f"DB Error: {e}")
    
    async def save_shoe_stats(self, shoe_id, stats):
        """Guardar estadísticas del zapato (contadores P/B/T)"""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute('''
                    INSERT INTO shoe_statistics 
                    (shoe_id, game_count, player_wins, banker_wins, ties, 
                     player_pairs, banker_pairs, history_data)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (shoe_id, timestamp) DO UPDATE
                    SET game_count = EXCLUDED.game_count,
                        player_wins = EXCLUDED.player_wins,
                        banker_wins = EXCLUDED.banker_wins,
                        ties = EXCLUDED.ties,
                        player_pairs = EXCLUDED.player_pairs,
                        banker_pairs = EXCLUDED.banker_pairs,
                        history_data = EXCLUDED.history_data
                ''',
                    shoe_id,
                    stats.get('gameCount'),
                    stats.get('playerWins'),
                    stats.get('bankerWins'),
                    stats.get('ties'),
                    stats.get('playerPairs', 0),
                    stats.get('bankerPairs', 0),
                    json.dumps(stats.get('history_v2', []))
                )
                logger.info(f"✓ Shoe stats: P:{stats.get('playerWins')} B:{stats.get('bankerWins')} T:{stats.get('ties')}")
            except Exception as e:
                logger.error(f"Shoe stats error: {e}")
    
    async def save_roadmap(self, game_id, roadmap_data):
        """Guardar roadmaps para análisis de patrones"""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute('''
                    INSERT INTO roadmaps 
                    (game_id, big_road, bead_road, big_eye_boy, small_road, cockroach_road)
                    VALUES ($1, $2, $3, $4, $5, $6)
                ''',
                    game_id,
                    json.dumps(roadmap_data.get('big_road', [])),
                    json.dumps(roadmap_data.get('bead_road', [])),
                    json.dumps(roadmap_data.get('big_eye_boy', [])),
                    json.dumps(roadmap_data.get('small_road', [])),
                    json.dumps(roadmap_data.get('cockroach_road', []))
                )
                logger.info(f"✓ Roadmap saved for {game_id}")
            except Exception as e:
                logger.error(f"Roadmap error: {e}")

class DragonBot:
    def __init__(self, db, target_url):
        self.db = db
        self.target_url = target_url
        self.current_game_data = {}
        self.current_shoe_id = None
        
    async def run(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                channel='chrome',  # Usar Google Chrome en lugar de Chromium
                args=['--disable-blink-features=AutomationControlled']
            )
            
            context = await browser.new_context()
            page = await context.new_page()
            
            def handle_websocket(ws):
                logger.info(f"✅ WebSocket connected")
                
                def on_frame(payload):
                    asyncio.create_task(self.process_message(payload))
                
                ws.on('framereceived', on_frame)
            
            page.on('websocket', handle_websocket)
            
            logger.info(f"🚀 Navigating to {self.target_url}")
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
            
            # Nueva ronda
            if msg_type == 'baccarat.newGame':
                args = data.get('args', {})
                self.current_game_data = {
                    'game_id': args.get('gameId'),
                    'game_number': args.get('gameNumber'),
                    'shoe_cards_out': args.get('shoeCardsOut')
                }
                logger.info(f"🎮 New game: {args.get('gameNumber')}")
            
            # Cartas repartidas
            elif msg_type == 'baccarat.cardDealt':
                args = data.get('args', {})
                game_data = args.get('gameData', {})
                
                player_hand = game_data.get('playerHand', {})
                banker_hand = game_data.get('bankerHand', {})
                
                self.current_game_data['player_cards'] = player_hand.get('cards', [])
                self.current_game_data['banker_cards'] = banker_hand.get('cards', [])
                self.current_game_data['player_score'] = player_hand.get('score')
                self.current_game_data['banker_score'] = banker_hand.get('score')
            
            # Multiplicadores Lightning
            elif msg_type == 'baccarat.potentialMultipliers':
                args = data.get('args', {})
                self.current_game_data['lightning_multipliers'] = args.get('multipliers', {})
            
            # ⭐ NUEVO: Estadísticas del Zapato (P/B/T counters)
            elif msg_type == 'baccarat.encodedShoeState':
                args = data.get('args', {})
                stats = args.get('stats', {})
                history = args.get('history_v2', [])
                
                # Generar shoe_id único basado en contadores
                shoe_id = f"shoe_{stats.get('gameCount', 0)}_{stats.get('playerWins', 0)}_{stats.get('bankerWins', 0)}"
                self.current_shoe_id = shoe_id
                
                # Guardar estadísticas del zapato
                await self.db.save_shoe_stats(shoe_id, {
                    **stats,
                    'history_v2': history
                })
                
                # Extraer roadmap del history
                roadmap_data = self.build_roadmap_from_history(history)
                if self.current_game_data.get('game_id'):
                    await self.db.save_roadmap(
                        self.current_game_data['game_id'],
                        roadmap_data
                    )
            
            # Resultado final
            elif msg_type == 'baccarat.resolved':
                args = data.get('args', {})
                result = args.get('result', {})
                
                round_data = {
                    **self.current_game_data,
                    'winner': result.get('winner'),
                    'player_score': result.get('playerScore'),
                    'banker_score': result.get('bankerScore'),
                    'player_pair': result.get('playerPair'),
                    'banker_pair': result.get('bankerPair'),
                    'is_natural': result.get('natural'),
                    'winning_spots': args.get('winningSpots', []),
                    'with_lightning': args.get('withLightning')
                }
                
                await self.db.save_round(round_data)
                
                logger.info(f"🎯 Result: {round_data['winner']} ({round_data['banker_score']}-{round_data['player_score']})")
                
                self.current_game_data = {}
            
            # Ganadores
            elif msg_type == 'baccarat.gameWinners':
                args = data.get('args', {})
                if self.current_game_data.get('game_id'):
                    self.current_game_data['total_winners'] = args.get('totalWinners')
                    self.current_game_data['total_amount'] = args.get('totalAmount')
                    
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def build_roadmap_from_history(self, history):
        """Construir roadmaps desde el historial"""
        big_road = []
        bead_road = []
        
        for i, round_data in enumerate(history):
            winner = round_data.get('winner')
            natural = round_data.get('natural', False)
            player_score = round_data.get('playerScore')
            banker_score = round_data.get('bankerScore')
            
            # Big Road (patrón principal)
            big_road.append({
                'position': i,
                'winner': winner,
                'natural': natural
            })
            
            # Bead Road (todos los resultados en orden)
            bead_road.append({
                'round': i + 1,
                'winner': winner,
                'player_score': player_score,
                'banker_score': banker_score
            })
        
        return {
            'big_road': big_road,
            'bead_road': bead_road,
            'big_eye_boy': self.calculate_big_eye_boy(big_road),
            'small_road': [],  # Se puede calcular con algoritmo específico
            'cockroach_road': []  # Se puede calcular con algoritmo específico
        }
    
    def calculate_big_eye_boy(self, big_road):
        """Calcular Big Eye Boy (detecta predictibilidad)"""
        # Algoritmo simplificado
        big_eye = []
        # Implementación completa requiere lógica específica de baccarat
        return big_eye

async def main():
    DB_URL = os.getenv('DATABASE_URL', 'postgresql://bot_user:secure_password_123@localhost/dragon_bot')
    TARGET_URL = os.getenv('TARGET_URL', 'https://dragonslots-1.com/es/live-casino/game/evolution/xxxtremelightningbaccarat')
    
    db = DragonBotDB(DB_URL)
    await db.init()
    
    bot = DragonBot(db, TARGET_URL)
    
    logger.info("🚀 Dragon Bot Advanced started - Capturing roadmaps 24/7...")
    
    try:
        await bot.run()
    finally:
        if db.pool:
            await db.pool.close()

if __name__ == '__main__':
    asyncio.run(main())
