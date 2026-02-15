import asyncio
import asyncpg

async def main():
    pool = await asyncpg.create_pool(
        "postgresql://localhost/dragon_bot",
        min_size=1, max_size=2
    )
    conn = await pool.acquire()

    # Check what strategies exist in strategy_predictions vs strategy_votes
    r1 = await conn.fetch("SELECT DISTINCT strategy FROM strategy_predictions ORDER BY strategy")
    print("=== Estrategias en strategy_predictions ===")
    for r in r1:
        print("  " + r["strategy"])

    r2 = await conn.fetch("SELECT DISTINCT strategy_name FROM strategy_votes ORDER BY strategy_name")
    print("")
    print("=== Estrategias en strategy_votes ===")
    for r in r2:
        print("  " + r["strategy_name"])

    # Check who writes to strategy_predictions
    cols = await conn.fetch(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'strategy_predictions' ORDER BY ordinal_position"
    )
    print("")
    print("=== Cols strategy_predictions ===")
    for c in cols:
        print("  " + c["column_name"])

    # Sample from strategy_predictions
    sample = await conn.fetch("SELECT * FROM strategy_predictions ORDER BY id DESC LIMIT 5")
    print("")
    print("=== Sample strategy_predictions (recent) ===")
    for s in sample:
        print("  " + str(dict(s)))

    await pool.release(conn)
    await pool.close()

asyncio.run(main())
