import asyncio
import asyncpg

async def main():
    pool = await asyncpg.create_pool(
        "postgresql://localhost/dragon_bot",
        min_size=1, max_size=2
    )
    conn = await pool.acquire()

    # Get column info for strategy_votes
    cols = await conn.fetch(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name = 'strategy_votes' ORDER BY ordinal_position"
    )
    print("=== COLUMNAS strategy_votes ===")
    for c in cols:
        print("  " + c["column_name"] + " (" + c["data_type"] + ")")

    # Get column info for strategy_predictions 
    cols2 = await conn.fetch(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name = 'strategy_predictions' ORDER BY ordinal_position"
    )
    print("")
    print("=== COLUMNAS strategy_predictions ===")
    for c in cols2:
        print("  " + c["column_name"] + " (" + c["data_type"] + ")")

    # Get column info for ml_predictions
    cols3 = await conn.fetch(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name = 'ml_predictions' ORDER BY ordinal_position"
    )
    print("")
    print("=== COLUMNAS ml_predictions ===")
    for c in cols3:
        print("  " + c["column_name"] + " (" + c["data_type"] + ")")

    # Sample rows from strategy_votes
    sample = await conn.fetch("SELECT * FROM strategy_votes LIMIT 3")
    print("")
    print("=== SAMPLE strategy_votes ===")
    for s in sample:
        print("  " + str(dict(s)))

    await pool.release(conn)
    await pool.close()

asyncio.run(main())
