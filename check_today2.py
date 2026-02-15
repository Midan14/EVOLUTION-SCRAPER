import asyncio
import asyncpg

async def main():
    pool = await asyncpg.create_pool(
        "postgresql://localhost/dragon_bot",
        min_size=1, max_size=2
    )
    conn = await pool.acquire()

    # Get baccarat_rounds columns
    cols = await conn.fetch(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'baccarat_rounds' ORDER BY ordinal_position"
    )
    print("=== baccarat_rounds columns ===")
    for c in cols:
        print("  " + c["column_name"])

    # Recent rounds
    r1 = await conn.fetch(
        "SELECT game_id, winner, timestamp FROM baccarat_rounds "
        "ORDER BY id DESC LIMIT 10"
    )
    print("")
    print("=== Last 10 rounds ===")
    for r in r1:
        ts = str(r["timestamp"])[:19] if r["timestamp"] else "?"
        print("  " + r["game_id"][:16] + " winner=" + str(r["winner"]).ljust(8) + " " + ts)

    # Today's data
    r2 = await conn.fetchrow(
        "SELECT COUNT(*) as cnt FROM baccarat_rounds "
        "WHERE timestamp > '2026-02-14'"
    )
    print("")
    print("Rounds today: " + str(r2["cnt"]))

    r3 = await conn.fetchrow(
        "SELECT COUNT(*) as cnt FROM ml_predictions "
        "WHERE timestamp > '2026-02-14'"
    )
    print("ML predictions today: " + str(r3["cnt"]))

    r4 = await conn.fetchrow(
        "SELECT COUNT(*) as cnt FROM ml_predictions "
        "WHERE timestamp > '2026-02-14' AND actual_winner IS NOT NULL"
    )
    print("ML predictions today WITH result: " + str(r4["cnt"]))

    # Check strategy_votes for today's resolved games
    r5 = await conn.fetch(
        "SELECT sv.game_id, sv.strategy_name, sv.actual_winner "
        "FROM strategy_votes sv "
        "WHERE sv.game_id IN ("
        "  SELECT game_id FROM baccarat_rounds ORDER BY id DESC LIMIT 50"
        ") "
        "LIMIT 10"
    )
    print("")
    print("=== strategy_votes for last 50 resolved games ===")
    for r in r5:
        print("  " + r["game_id"][:16] + " st=" + r["strategy_name"].ljust(20) + " actual=" + str(r["actual_winner"]))

    if not r5:
        print("  (NONE - the game_ids don't overlap)")

    await pool.release(conn)
    await pool.close()

asyncio.run(main())
