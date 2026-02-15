import asyncio
import asyncpg

async def main():
    pool = await asyncpg.create_pool(
        "postgresql://localhost/dragon_bot",
        min_size=1, max_size=2
    )
    conn = await pool.acquire()

    # Strategy accuracy
    sql1 = "SELECT strategy_name, COUNT(*) as total, "
    sql1 += "SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as correct, "
    sql1 += "ROUND(100.0 * SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) / COUNT(*), 1) as accuracy "
    sql1 += "FROM strategy_votes WHERE was_correct IS NOT NULL "
    sql1 += "GROUP BY strategy_name ORDER BY accuracy DESC"

    rows = await conn.fetch(sql1)
    print("=== PRECISION POR ESTRATEGIA ===")
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
        pct = str(acc) + "%"
        print(tag + " | " + name.ljust(24) + " | total=" + str(total).rjust(4) + " | ok=" + str(correct).rjust(4) + " | " + pct)

    # Vote distribution per strategy
    sql3 = "SELECT strategy_name, predicted_winner, COUNT(*) as cnt "
    sql3 += "FROM strategy_votes WHERE was_correct IS NOT NULL "
    sql3 += "GROUP BY strategy_name, predicted_winner ORDER BY strategy_name, predicted_winner"

    rows3 = await conn.fetch(sql3)
    print("")
    print("=== DISTRIBUCION DE VOTOS ===")
    current = ""
    for r in rows3:
        name = r["strategy_name"]
        pw = r["predicted_winner"]
        cnt = r["cnt"]
        if name != current:
            print("")
            current = name
        print("  " + name.ljust(24) + " -> " + pw.ljust(8) + " x" + str(cnt))

    # ML accuracy
    sql_ml = "SELECT COUNT(*) as total, "
    sql_ml += "SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as correct "
    sql_ml += "FROM ml_predictions WHERE was_correct IS NOT NULL"
    ml_row = await conn.fetchrow(sql_ml)
    ml_t = ml_row["total"]
    ml_c = ml_row["correct"]
    print("")
    if ml_t > 0:
        ml_pct = round(ml_c / ml_t * 100, 1)
        print("ML Predictions: " + str(ml_t) + " total, " + str(ml_c) + " correctas, " + str(ml_pct) + "%")
    else:
        print("ML Predictions: sin datos")

    # Overall consensus accuracy from strategy_predictions
    sql_sp = "SELECT COUNT(*) as total, "
    sql_sp += "SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as correct "
    sql_sp += "FROM strategy_predictions WHERE was_correct IS NOT NULL"
    sp_row = await conn.fetchrow(sql_sp)
    sp_t = sp_row["total"]
    sp_c = sp_row["correct"]
    if sp_t > 0:
        sp_pct = round(sp_c / sp_t * 100, 1)
        print("Consenso Strategy: " + str(sp_t) + " total, " + str(sp_c) + " correctas, " + str(sp_pct) + "%")

    # Total rounds
    sql4 = "SELECT COUNT(*) as total FROM baccarat_rounds"
    total_row = await conn.fetchrow(sql4)
    print("Total rondas registradas: " + str(total_row["total"]))

    # Recent accuracy (last 100)
    sql5 = "SELECT strategy_name, COUNT(*) as total, "
    sql5 += "SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as correct, "
    sql5 += "ROUND(100.0 * SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) / COUNT(*), 1) as accuracy "
    sql5 += "FROM strategy_votes WHERE was_correct IS NOT NULL "
    sql5 += "AND game_id IN (SELECT DISTINCT game_id FROM strategy_votes ORDER BY game_id DESC LIMIT 100) "
    sql5 += "GROUP BY strategy_name ORDER BY accuracy DESC"

    rows5 = await conn.fetch(sql5)
    print("")
    print("=== PRECISION ULTIMAS 100 RONDAS ===")
    for r in rows5:
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
        pct = str(acc) + "%"
        print(tag + " | " + name.ljust(24) + " | total=" + str(total).rjust(4) + " | ok=" + str(correct).rjust(4) + " | " + pct)

    await pool.release(conn)
    await pool.close()

asyncio.run(main())
