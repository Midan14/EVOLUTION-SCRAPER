import asyncio
import asyncpg

async def main():
    pool = await asyncpg.create_pool(
        "postgresql://localhost/dragon_bot",
        min_size=1, max_size=2
    )
    conn = await pool.acquire()

    # Today's rounds
    r1 = await conn.fetch(
        "SELECT game_id, winner, created_at FROM baccarat_rounds "
        "WHERE created_at > '2026-02-14' ORDER BY created_at DESC LIMIT 10"
    )
    print("=== Rondas de hoy ===")
    for r in r1:
        ts = str(r["created_at"])[:19]
        print("  " + r["game_id"][:16] + " winner=" + str(r["winner"]).ljust(8) + " " + ts)

    # Check if strategy_votes game_ids match today's rounds
    r2 = await conn.fetch(
        "SELECT sv.game_id, sv.created_at as sv_time "
        "FROM strategy_votes sv ORDER BY sv.id DESC LIMIT 5"
    )
    print("")
    print("=== Latest strategy_votes times ===")
    for r in r2:
        ts = str(r["sv_time"])[:19]
        print("  " + r["game_id"][:16] + " " + ts)

    # Do any strategy_votes game_ids appear in baccarat_rounds?
    r3 = await conn.fetchrow(
        "SELECT COUNT(DISTINCT sv.game_id) as cnt "
        "FROM strategy_votes sv "
        "JOIN baccarat_rounds br ON sv.game_id = br.game_id"
    )
    total_sv = await conn.fetchrow("SELECT COUNT(DISTINCT game_id) FROM strategy_votes")
    print("")
    print("strategy_votes game_ids in baccarat_rounds: " + str(r3["cnt"]) + " / " + str(total_sv["count"]))

    # Check if resolved messages update ml_predictions today
    r4 = await conn.fetch(
        "SELECT game_id, predicted_winner, actual_winner, was_correct "
        "FROM ml_predictions "
        "WHERE timestamp > '2026-02-14' AND actual_winner IS NOT NULL "
        "ORDER BY id DESC LIMIT 5"
    )
    print("")
    print("=== Today's ml_predictions with results ===")
    for r in r4:
        print("  " + r["game_id"][:16] + " pred=" + str(r["predicted_winner"]).ljust(8)
              + " actual=" + str(r["actual_winner"]).ljust(8) + " " + str(r["was_correct"]))

    if not r4:
        print("  (NONE - resolved handler is NOT updating today)")

    # How many predictions today total
    r5 = await conn.fetchrow(
        "SELECT COUNT(*) as cnt FROM ml_predictions WHERE timestamp > '2026-02-14'"
    )
    print("Total predictions today: " + str(r5["cnt"]))

    # How many rounds today
    r6 = await conn.fetchrow(
        "SELECT COUNT(*) as cnt FROM baccarat_rounds WHERE created_at > '2026-02-14'"
    )
    print("Total rounds recorded today: " + str(r6["cnt"]))

    await pool.release(conn)
    await pool.close()

asyncio.run(main())
