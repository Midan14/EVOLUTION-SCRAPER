import asyncio
import asyncpg

async def main():
    pool = await asyncpg.create_pool(
        "postgresql://localhost/dragon_bot",
        min_size=1, max_size=2
    )
    conn = await pool.acquire()

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

    sql2 = "SELECT COUNT(*) as total, "
    sql2 += "SUM(CASE WHEN result = predicted THEN 1 ELSE 0 END) as correct "
    sql2 += "FROM predictions WHERE result IS NOT NULL"

    total_row = await conn.fetchrow(sql2)
    t = total_row["total"]
    c = total_row["correct"]
    if t > 0:
        pct = round(c / t * 100, 1)
        print("")
        print("TOTAL GENERAL: " + str(t) + " predicciones, " + str(c) + " correctas, " + str(pct) + "%")

    # Also get vote direction distribution
    sql3 = "SELECT strategy_name, vote, COUNT(*) as cnt "
    sql3 += "FROM strategy_votes WHERE was_correct IS NOT NULL "
    sql3 += "GROUP BY strategy_name, vote ORDER BY strategy_name, vote"

    rows3 = await conn.fetch(sql3)
    print("")
    print("=== DISTRIBUCION DE VOTOS ===")
    current = ""
    for r in rows3:
        name = r["strategy_name"]
        vote = r["vote"]
        cnt = r["cnt"]
        if name != current:
            print("")
            current = name
        print("  " + name.ljust(24) + " -> " + vote.ljust(8) + " x" + str(cnt))

    await pool.release(conn)
    await pool.close()

asyncio.run(main())
