import asyncio
import asyncpg

async def main():
    pool = await asyncpg.create_pool(
        'postgresql://localhost/dragon_bot',
        min_size=1, max_size=2
    )
    conn = await pool.acquire()

    q1 = (
        "SELECT strategy_name, COUNT(*) as total, "
        "SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as correct, "
        "ROUND(100.0 * SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) "
        "/ COUNT(*), 1) as accuracy "
        "FROM strategy_votes "
        "WHERE was_correct IS NOT NULL "
        "GROUP BY strategy_name "
        "ORDER BY total DESC"
    )
    rows = await conn.fetch(q1)

    print("=== PRECISION POR ESTRATEGIA ===")
    for r in rows:
        acc = float(r['accuracy'])
        tag = "OK" if acc >= 50 else "??" if acc >= 45 else "XX"
        name = r['strategy_name']
        total = r['total']
        correct = r['correct']
        print(f"[{tag}] {name:<22} t={total:>4} ok={correct:>4} {acc:.1f}%")

    q2 = (
        "SELECT COUNT(*) as total, "
        "SUM(CASE WHEN result = predicted THEN 1 ELSE 0 END) as correct "
        "FROM predictions WHERE result IS NOT NULL"
    )
    total_row = await conn.fetchrow(q2)
    t = total_row['total']
    c = total_row['correct']
    if t > 0:
        print(f"\nTOTAL: {t} pred, {c} ok, {c/t*100:.1f}%")

    await pool.release(conn)
    await pool.close()

asyncio.run(main())
