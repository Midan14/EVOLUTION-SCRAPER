#!/usr/bin/env python3
"""
Reporte de precisión por estrategia con datos de producción.
Ejecutar: python report_strategy_accuracy.py
Usa DB_URL del .env o por defecto postgresql://localhost/dragon_bot
"""
import asyncio
import os

# Cargar .env si existe
if os.path.isfile(".env"):
    with open(".env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from dragon_bot_ml import DragonBotDB

async def main():
    db_url = os.getenv("DB_URL", "postgresql://localhost/dragon_bot")
    db = DragonBotDB(db_url)
    await db.init()
    min_votes = int(os.getenv("MIN_VOTES_REPORT", "1"))
    acc_list = await db.get_strategy_accuracy(min_votes=min_votes)
    await db.pool.close()
    
    if not acc_list:
        print("No hay suficientes datos (strategy_votes con resultado).")
        print("El bot registra cada voto al predecir y actualiza al resolver.")
        return
    
    print("\n" + "=" * 50)
    print("  PRECISIÓN POR ESTRATEGIA (uso real)")
    print("=" * 50)
    for i, row in enumerate(acc_list, 1):
        print(f"  {i:2}. {row['strategy']:20} {row['accuracy']:5.1f}%  ({row['correct']}/{row['total']})")
    print("=" * 50 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
