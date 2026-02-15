import asyncio
import asyncpg

async def main():
    pool = await asyncpg.create_pool(
        "postgresql://localhost/dragon_bot",
        min_size=1, max_size=2
    )
    conn = await pool.acquire()

    # How many ml_predictions have actual_winner set vs null
    r1 = await conn.fetchrow(
        "SELECT COUNT(*) as total, "
        "SUM(CASE WHEN actual_winner IS NOT NULL THEN 1 ELSE 0 END) as with_result "
        "FROM ml_predictions"
    )
    print("ml_predictions: total=" + str(r1["total"]) + " with_result=" + str(r1["with_result"]))

    # How many strategy_votes have actual_winner set vs null
    r2 = await conn.fetchrow(
        "SELECT COUNT(*) as total, "
        "SUM(CASE WHEN actual_winner IS NOT NULL THEN 1 ELSE 0 END) as with_result "
        "FROM strategy_votes"
    )
    print("strategy_votes: total=" + str(r2["total"]) + " with_result=" + str(r2["with_result"]))

    # Show some ml_predictions WITH results
    ml = await conn.fetch(
        "SELECT game_id, predicted_winner, actual_winner, was_correct, timestamp "
        "FROM ml_predictions WHERE actual_winner IS NOT NULL ORDER BY id DESC LIMIT 5"
    )
    print("")
    print("=== Recent ml_predictions WITH results ===")
    for r in ml:
        ts = str(r["timestamp"])[:19] if r["timestamp"] else "?"
        print("  gid=" + r["game_id"][:12] + " pred=" + str(r["predicted_winner"]).ljust(8)
              + " actual=" + str(r["actual_winner"]).ljust(8)
              + " correct=" + str(r["was_correct"]) + " ts=" + ts)

    # Show some without results (most recent)
    ml2 = await conn.fetch(
        "SELECT game_id, predicted_winner, actual_winner, timestamp "
        "FROM ml_predictions WHERE actual_winner IS NULL ORDER BY id DESC LIMIT 5"
    )
    print("")
    print("=== Recent ml_predictions WITHOUT results ===")
    for r in ml2:
        ts = str(r["timestamp"])[:19] if r["timestamp"] else "?"
        print("  gid=" + r["game_id"][:12] + " pred=" + str(r["predicted_winner"]).ljust(8) + " ts=" + ts)

    # Check if strategy_votes for game_ids that DO have results in ml_predictions
    fixed = await conn.fetch(
        "SELECT sv.game_id, sv.strategy_name, sv.predicted_winner, sv.actual_winner, sv.was_correct "
        "FROM strategy_votes sv "
        "JOIN ml_predictions ml ON sv.game_id = ml.game_id "
        "WHERE ml.actual_winner IS NOT NULL "
        "ORDER BY sv.id DESC LIMIT 10"
    )
    print("")
    print("=== strategy_votes for games ML has results ===")
    for r in fixed:
        print("  gid=" + r["game_id"][:12] + " st=" + r["strategy_name"].ljust(20)
              + " pred=" + str(r["predicted_winner"]).ljust(8)
              + " actual=" + str(r["actual_winner"]).ljust(8)
              + " correct=" + str(r["was_correct"]))

    await pool.release(conn)
    await pool.close()

asyncio.run(main())
