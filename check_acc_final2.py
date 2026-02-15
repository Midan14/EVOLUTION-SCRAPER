import asyncio
import asyncpg

async def main():
    pool = await asyncpg.create_pool(
        "postgresql://localhost/dragon_bot",
        min_size=1, max_size=2
    )
    conn = await pool.acquire()

    # Count strategy_votes total vs with was_correct
    r1 = await conn.fetchrow("SELECT COUNT(*) as total FROM strategy_votes")
    r2 = await conn.fetchrow("SELECT COUNT(*) as total FROM strategy_votes WHERE was_correct IS NOT NULL")
    r3 = await conn.fetchrow("SELECT COUNT(*) as total FROM strategy_votes WHERE actual_winner IS NOT NULL")
    print("strategy_votes: total=" + str(r1["total"]) + " was_correct_set=" + str(r2["total"]) + " actual_winner_set=" + str(r3["total"]))

    # Strategy predictions - with accuracy per strategy
    sql_sp = "SELECT strategy, COUNT(*) as total, "
    sql_sp += "SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as correct, "
    sql_sp += "ROUND(100.0 * SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) / COUNT(*), 1) as accuracy "
    sql_sp += "FROM strategy_predictions WHERE was_correct IS NOT NULL "
    sql_sp += "GROUP BY strategy ORDER BY accuracy DESC"

    rows = await conn.fetch(sql_sp)
    print("")
    print("=== PRECISION POR ESTRATEGIA (strategy_predictions) ===")
    for r in rows:
        acc = float(r["accuracy"])
        if acc >= 50:
            tag = "OK"
        elif acc >= 45:
            tag = "??"
        else:
            tag = "XX"
        name = r["strategy"]
        total = r["total"]
        correct = r["correct"]
        pct = str(acc) + "%"
        print(tag + " | " + name.ljust(24) + " | total=" + str(total).rjust(4) + " | ok=" + str(correct).rjust(4) + " | " + pct)

    # Vote distribution from strategy_predictions
    sql_dist = "SELECT strategy, predicted_winner, COUNT(*) as cnt "
    sql_dist += "FROM strategy_predictions WHERE was_correct IS NOT NULL "
    sql_dist += "GROUP BY strategy, predicted_winner ORDER BY strategy, predicted_winner"

    rows_d = await conn.fetch(sql_dist)
    print("")
    print("=== DISTRIBUCION VOTOS (strategy_predictions) ===")
    current = ""
    for r in rows_d:
        name = r["strategy"]
        pw = r["predicted_winner"]
        cnt = r["cnt"]
        if name != current:
            print("")
            current = name
        print("  " + name.ljust(24) + " -> " + pw.ljust(8) + " x" + str(cnt))

    # Last 100 rounds  
    sql5 = "SELECT strategy, COUNT(*) as total, "
    sql5 += "SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as correct, "
    sql5 += "ROUND(100.0 * SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) / COUNT(*), 1) as accuracy "
    sql5 += "FROM strategy_predictions WHERE was_correct IS NOT NULL "
    sql5 += "AND id > (SELECT MAX(id) - 500 FROM strategy_predictions) "
    sql5 += "GROUP BY strategy ORDER BY accuracy DESC"

    rows5 = await conn.fetch(sql5)
    print("")
    print("=== PRECISION ULTIMAS ~100 RONDAS ===")
    for r in rows5:
        acc = float(r["accuracy"])
        if acc >= 50:
            tag = "OK"
        elif acc >= 45:
            tag = "??"
        else:
            tag = "XX"
        name = r["strategy"]
        total = r["total"]
        correct = r["correct"]
        pct = str(acc) + "%"
        print(tag + " | " + name.ljust(24) + " | total=" + str(total).rjust(4) + " | ok=" + str(correct).rjust(4) + " | " + pct)

    # ML prediction distribution
    sql_ml = "SELECT predicted_winner, COUNT(*) as cnt, "
    sql_ml += "SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as ok "
    sql_ml += "FROM ml_predictions WHERE was_correct IS NOT NULL "
    sql_ml += "GROUP BY predicted_winner"
    ml_rows = await conn.fetch(sql_ml)
    print("")
    print("=== ML POR PREDICCION ===")
    for r in ml_rows:
        pw = r["predicted_winner"]
        cnt = r["cnt"]
        ok = r["ok"]
        pct = round(ok / cnt * 100, 1) if cnt > 0 else 0
        print("  " + pw.ljust(8) + " -> total=" + str(cnt) + " ok=" + str(ok) + " " + str(pct) + "%")

    await pool.release(conn)
    await pool.close()

asyncio.run(main())
