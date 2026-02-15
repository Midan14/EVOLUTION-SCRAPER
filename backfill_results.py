import asyncio
import asyncpg

async def main():
    pool = await asyncpg.create_pool(
        "postgresql://localhost/dragon_bot",
        min_size=1, max_size=2
    )
    conn = await pool.acquire()

    # Update strategy_votes from baccarat_rounds
    result1 = await conn.execute(
        "UPDATE strategy_votes sv "
        "SET actual_winner = br.winner, "
        "    was_correct = (sv.predicted_winner = br.winner) "
        "FROM baccarat_rounds br "
        "WHERE sv.game_id = br.game_id "
        "AND sv.actual_winner IS NULL"
    )
    print("strategy_votes actualizados: " + result1)

    # Update ml_predictions from baccarat_rounds
    result2 = await conn.execute(
        "UPDATE ml_predictions mp "
        "SET actual_winner = br.winner, "
        "    was_correct = (mp.predicted_winner = br.winner) "
        "FROM baccarat_rounds br "
        "WHERE mp.game_id = br.game_id "
        "AND mp.actual_winner IS NULL"
    )
    print("ml_predictions actualizados: " + result2)

    # Now check accuracy
    rows = await conn.fetch(
        "SELECT strategy_name, COUNT(*) as total, "
        "SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as correct, "
        "ROUND(100.0 * SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) / COUNT(*), 1) as accuracy "
        "FROM strategy_votes WHERE was_correct IS NOT NULL "
        "GROUP BY strategy_name ORDER BY accuracy DESC"
    )
    print("")
    print("=== PRECISION REAL POR ESTRATEGIA (strategy_votes) ===")
    for r in rows:
        acc = float(r["accuracy"])
        if acc >= 50:
            tag = "OK"
        elif acc >= 45:
            tag = "??"
        else:
            tag = "XX"
        name = r["strategy_name"]
        total = r["total"]
        correct = r["correct"]
        print(tag + " | " + name.ljust(24) + " | total=" + str(total).rjust(4) + " | ok=" + str(correct).rjust(4) + " | " + str(acc) + "%")

    # ML accuracy
    ml_row = await conn.fetchrow(
        "SELECT COUNT(*) as total, "
        "SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as correct "
        "FROM ml_predictions WHERE was_correct IS NOT NULL"
    )
    t = ml_row["total"]
    c = ml_row["correct"]
    if t > 0:
        print("")
        print("ML total: " + str(t) + " predicciones, " + str(c) + " correctas, " + str(round(c/t*100, 1)) + "%")

    await pool.release(conn)
    await pool.close()

asyncio.run(main())
