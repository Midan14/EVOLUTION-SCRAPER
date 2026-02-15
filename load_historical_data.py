# load_historical_data.py
import asyncio
import asyncpg
import json

async def load_data():
    # Conectar a BD
    conn = await asyncpg.connect('postgresql://localhost/dragon_bot')
    
    # Leer archivo capturado
    with open('ws_messages_authenticated.json', 'r') as f:
        messages = json.load(f)
    
    print(f"📂 Cargando {len(messages)} mensajes...")
    
    rounds_saved = 0
    
    for msg in messages:
        data = msg.get('data', {})
        msg_type = data.get('type')
        
        # Buscar resultados completos
        if msg_type == 'baccarat.resolved':
            args = data.get('args', {})
            result = args.get('result', {})
            
            game_id = args.get('gameId')
            if not game_id:
                continue
            
            try:
                await conn.execute('''
                    INSERT INTO baccarat_rounds 
                    (game_id, game_number, winner, player_score, banker_score,
                     player_pair, banker_pair, is_natural, winning_spots, with_lightning)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (game_id) DO NOTHING
                ''',
                    game_id,
                    args.get('gameNumber'),
                    result.get('winner'),
                    result.get('playerScore'),
                    result.get('bankerScore'),
                    result.get('playerPair'),
                    result.get('bankerPair'),
                    result.get('natural'),
                    json.dumps(args.get('winningSpots', [])),
                    args.get('withLightning')
                )
                rounds_saved += 1
                print(f"✅ Ronda {rounds_saved}: {result.get('winner')} ({result.get('bankerScore')}-{result.get('playerScore')})")
            except Exception as e:
                print(f"❌ Error: {e}")
    
    await conn.close()
    
    print(f"\n🎯 Total guardado: {rounds_saved} rondas")
    print("\n✅ Ahora puedes ejecutar: python dragon_bot_ml.py")

if __name__ == '__main__':
    asyncio.run(load_data())
