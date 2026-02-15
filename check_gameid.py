import asyncio
import asyncpg

async def main():
    pool = await asyncpg.create_pool(
        "postgresql://localhost/dragon_bot",
        min_size=1, max_size=2
    )
    conn = await pool.acquire()

    # Recent strategy_votes with their game_ids
    sv = await conn.fetch(
        "SELECT game_id, strategy_name, predicted_winner, actual_winner, was_correct "
        "FROM strategy_votes ORDER BY id DESC LIMIT 10"
    )
    print("=== Recent strategy_votes ===")
    for r in sv:
        print("  gid=" + r["game_id"][:12] + " st=" + r["strategy_name"].ljust(20)
              + " pred=" + str(r["predicted_winner"]).ljust(8)
              + " actual=" + str(r["actual_winner"]).ljust(8)
              + " correct=" + str(r["was_correct"]))

    # Recent ml_predictions with their results
    ml = await conn.fetch(
        "SELECT game_id, predicted_winner, actual_winner, was_correct "
        "FROM ml_predictions ORDER BY id DESC LIMIT 10"
    )
    print("")
    print("=== Recent ml_predictions ===")
    for r in ml:
        print("  gid=" + r["game_id"][:12] + " pred=" + str(r["predicted_winner"]).ljust(8)
              + " actual=" + str(r["actual_winner"]).ljust(8)
              + " correct=" + str(r["was_correct"]))

    # Check if game_ids in strategy_votes exist in ml_predictions
    common = await conn.fetchrow(
        "SELECT COUNT(DISTINCT sv.game_id) as cnt "
        "FROM strategy_votes sv "
        "JOIN ml_predictions ml ON sv.game_id = ml.game_id"
    )
    sv_total = await conn.fetchrow("SELECT COUNT(DISTINCT game_id) as cnt FROM strategy_votes")
    ml_total = await conn.fetchrow("SELECT COUNT(DISTINCT game_id) as cnt FROM ml_predictions")

    print("")
    print("strategy_votes unique game_ids: " + str(sv_total["cnt"]))
    print("ml_predictions unique game_ids: " + str(ml_total["cnt"]))
    print("Common game_ids: " + str(common["cnt"]))

    # Check game_ids in strategy_votes that were updated in ml_predictions
    updated = await conn.fetch(
        "SELECT sv.game_id, sv.actual_winner as sv_actual, ml.actual_winner as ml_actual "
        "FROM strategy_votes sv "
        "JOIN ml_predictions ml ON sv.game_id = ml.game_id "
        "WHERE ml.actual_winner IS NOT NULL AND sv.actual_winner IS NULL "
        "LIMIT 5"
    )
    print("")
    print("=== Votes NOT updated despite ML having result ===")
    for r in updated:
        print("  gid=" + r["game_id"][:12] + " sv_actual=" + str(r["sv_actual"]) + " ml_actual=" + str(r["ml_actual"]))

    await pool.release(conn)
    await pool.close()

asyncio.run(main())
