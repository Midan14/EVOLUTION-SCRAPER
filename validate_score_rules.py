#!/usr/bin/env python3
"""Validar las reglas de score del usuario contra datos reales"""
import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect(database='dragon_bot')
    
    rows = await conn.fetch("""
        SELECT winner, player_score, banker_score, captured_at
        FROM baccarat_rounds
        WHERE player_score IS NOT NULL AND banker_score IS NOT NULL
        ORDER BY captured_at ASC
    """)
    
    print(f"Total rondas con scores: {len(rows)}")
    print("=" * 70)
    
    rules = [
        ("1) Player 9 (9 azul) -> Player", 
         lambda r: r['winner'] == 'Player' and r['player_score'] == 9, 'Player'),
        ("2) Banker 6 (6 rojo) -> Banker",
         lambda r: r['winner'] == 'Banker' and r['banker_score'] == 6, 'Banker'),
        ("3) Player 8 (8 azul) -> Banker",
         lambda r: r['winner'] == 'Player' and r['player_score'] == 8, 'Banker'),
        ("4) Banker 7 (7 rojo) -> Player",
         lambda r: r['winner'] == 'Banker' and r['banker_score'] == 7, 'Player'),
        ("5) Score 4 (cualquier) -> Banker",
         lambda r: r['player_score'] == 4 or r['banker_score'] == 4, 'Banker'),
        ("6) Tie -> Banker",
         lambda r: r['winner'] == 'Tie', 'Banker'),
        ("7) Banker 9 (9 rojo) -> Player",
         lambda r: r['winner'] == 'Banker' and r['banker_score'] == 9, 'Player'),
    ]
    
    for name, condition, expected in rules:
        counts = {'Banker': 0, 'Player': 0, 'Tie': 0}
        for i in range(len(rows) - 1):
            if condition(rows[i]):
                nxt = rows[i + 1]['winner']
                counts[nxt] = counts.get(nxt, 0) + 1
        total = sum(counts.values())
        if total > 0:
            acc = counts[expected] / total * 100
            no_tie = total - counts['Tie']
            acc_no_tie = counts[expected] / no_tie * 100 if no_tie > 0 else 0
            marker = "OK" if acc > 50 else "XX"
            print(f"\n{name}")
            print(f"  B={counts['Banker']} P={counts['Player']} T={counts['Tie']} | Total={total}")
            print(f"  Regla dice {expected}: {counts[expected]}/{total} = {acc:.1f}% [{marker}]")
            print(f"  Sin ties: {counts[expected]}/{no_tie} = {acc_no_tie:.1f}%")
        else:
            print(f"\n{name}: SIN DATOS")
    
    # Bonus: todas las combinaciones score+ganador -> siguiente
    print("\n" + "=" * 70)
    print("TODAS LAS COMBINACIONES GANADOR+SCORE -> SIGUIENTE (>15 muestras)")
    print("=" * 70)
    
    combos = {}
    for i in range(len(rows) - 1):
        w = rows[i]['winner']
        if w == 'Tie':
            key = f"Tie"
        elif w == 'Banker':
            key = f"B{rows[i]['banker_score']}"
        else:
            key = f"P{rows[i]['player_score']}"
        
        nxt = rows[i + 1]['winner']
        if key not in combos:
            combos[key] = {'Banker': 0, 'Player': 0, 'Tie': 0}
        combos[key][nxt] += 1
    
    print(f"\n{'Trigger':<10} {'B':>5} {'P':>5} {'T':>5} {'Total':>6} {'Best':>8} {'Acc%':>6}")
    print("-" * 55)
    for key in sorted(combos.keys()):
        c = combos[key]
        total = sum(c.values())
        if total < 15:
            continue
        best = max(c, key=c.get)
        no_tie = total - c['Tie']
        best_bp = max(['Banker', 'Player'], key=lambda x: c[x])
        acc = c[best_bp] / no_tie * 100 if no_tie > 0 else 0
        marker = "<<" if acc >= 55 else ""
        print(f"  {key:<8} {c['Banker']:>5} {c['Player']:>5} {c['Tie']:>5} {total:>6} {best_bp:>8} {acc:>5.1f}% {marker}")
    
    await conn.close()

asyncio.run(main())
