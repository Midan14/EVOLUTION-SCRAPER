#!/usr/bin/env python3
"""
Análisis EXHAUSTIVO de todos los patrones de resultados posibles.
Buscar reglas ocultas: combinaciones de scores, pares, naturales, rachas, etc.
"""
import asyncio
import asyncpg
from collections import defaultdict

async def main():
    conn = await asyncpg.connect(database='dragon_bot')
    
    rows = await conn.fetch("""
        SELECT winner, player_score, banker_score, player_pair, banker_pair,
               is_natural
        FROM baccarat_rounds
        WHERE player_score IS NOT NULL AND banker_score IS NOT NULL
        ORDER BY captured_at ASC
    """)
    
    print(f"Total rondas: {len(rows)}")
    print("=" * 80)
    
    # ============================================================
    # 1. COMBINACIÓN EXACTA DE SCORES (P_score - B_score) → siguiente
    # ============================================================
    print("\n📊 1) COMBINACIÓN EXACTA DE SCORES → SIGUIENTE GANADOR")
    print("-" * 80)
    
    score_combos = defaultdict(lambda: {'Banker': 0, 'Player': 0, 'Tie': 0})
    for i in range(len(rows) - 1):
        ps, bs = rows[i]['player_score'], rows[i]['banker_score']
        w = rows[i]['winner']
        key = f"{w[0]}: {ps}-{bs}"
        nxt = rows[i + 1]['winner']
        score_combos[key][nxt] += 1
    
    print(f"{'Combo':<18} {'B':>4} {'P':>4} {'T':>3} {'Tot':>4} {'Best':>7} {'Acc%':>6} {'NoTie%':>7}")
    print("-" * 65)
    results_combo = []
    for key in sorted(score_combos.keys()):
        c = score_combos[key]
        total = sum(c.values())
        if total < 10:
            continue
        no_tie = total - c['Tie']
        best_bp = max(['Banker', 'Player'], key=lambda x: c[x])
        acc = c[best_bp] / no_tie * 100 if no_tie > 0 else 0
        marker = " ★★" if acc >= 60 and no_tie >= 15 else " ★" if acc >= 55 and no_tie >= 10 else ""
        results_combo.append((key, c, total, no_tie, best_bp, acc))
        print(f"  {key:<16} {c['Banker']:>4} {c['Player']:>4} {c['Tie']:>3} {total:>4} {best_bp:>7} {acc:>5.1f}% {marker}")
    
    # ============================================================
    # 2. DESPUÉS DE PAR → siguiente
    # ============================================================
    print("\n\n📊 2) DESPUÉS DE PAR → SIGUIENTE GANADOR")
    print("-" * 80)
    
    pair_patterns = {
        'Player_Pair_Yes': lambda r: r['player_pair'],
        'Banker_Pair_Yes': lambda r: r['banker_pair'],
        'Both_Pairs': lambda r: r['player_pair'] and r['banker_pair'],
        'Any_Pair': lambda r: r['player_pair'] or r['banker_pair'],
        'No_Pair': lambda r: not r['player_pair'] and not r['banker_pair'],
        'P_Pair+P_Win': lambda r: r['player_pair'] and r['winner'] == 'Player',
        'P_Pair+B_Win': lambda r: r['player_pair'] and r['winner'] == 'Banker',
        'B_Pair+P_Win': lambda r: r['banker_pair'] and r['winner'] == 'Player',
        'B_Pair+B_Win': lambda r: r['banker_pair'] and r['winner'] == 'Banker',
    }
    
    for name, condition in pair_patterns.items():
        counts = {'Banker': 0, 'Player': 0, 'Tie': 0}
        for i in range(len(rows) - 1):
            if condition(rows[i]):
                counts[rows[i + 1]['winner']] += 1
        total = sum(counts.values())
        if total < 5:
            continue
        no_tie = total - counts['Tie']
        best = max(['Banker', 'Player'], key=lambda x: counts[x])
        acc = counts[best] / no_tie * 100 if no_tie > 0 else 0
        marker = " ★★" if acc >= 60 else " ★" if acc >= 55 else ""
        print(f"  {name:<20} B={counts['Banker']:>3} P={counts['Player']:>3} T={counts['Tie']:>2} | Tot={total:>3} | {best} {acc:.1f}%{marker}")
    
    # ============================================================
    # 3. DESPUÉS DE NATURAL → siguiente
    # ============================================================
    print("\n\n📊 3) DESPUÉS DE NATURAL (8 o 9) → SIGUIENTE GANADOR")
    print("-" * 80)
    
    nat_patterns = {
        'Natural_Any': lambda r: r['player_score'] >= 8 or r['banker_score'] >= 8,
        'Natural_P_Win': lambda r: r['winner'] == 'Player' and r['player_score'] >= 8,
        'Natural_B_Win': lambda r: r['winner'] == 'Banker' and r['banker_score'] >= 8,
        'Natural_9_P': lambda r: r['winner'] == 'Player' and r['player_score'] == 9,
        'Natural_9_B': lambda r: r['winner'] == 'Banker' and r['banker_score'] == 9,
        'Natural_8_P': lambda r: r['winner'] == 'Player' and r['player_score'] == 8,
        'Natural_8_B': lambda r: r['winner'] == 'Banker' and r['banker_score'] == 8,
        'Nat_Tie_88': lambda r: r['winner'] == 'Tie' and r['player_score'] == 8,
        'Nat_Tie_99': lambda r: r['winner'] == 'Tie' and r['player_score'] == 9,
        'No_Natural': lambda r: r['player_score'] < 8 and r['banker_score'] < 8,
        'Both_Natural': lambda r: r['player_score'] >= 8 and r['banker_score'] >= 8,
    }
    
    for name, condition in nat_patterns.items():
        counts = {'Banker': 0, 'Player': 0, 'Tie': 0}
        for i in range(len(rows) - 1):
            if condition(rows[i]):
                counts[rows[i + 1]['winner']] += 1
        total = sum(counts.values())
        if total < 5:
            continue
        no_tie = total - counts['Tie']
        best = max(['Banker', 'Player'], key=lambda x: counts[x])
        acc = counts[best] / no_tie * 100 if no_tie > 0 else 0
        marker = " ★★" if acc >= 60 else " ★" if acc >= 55 else ""
        print(f"  {name:<20} B={counts['Banker']:>3} P={counts['Player']:>3} T={counts['Tie']:>2} | Tot={total:>3} | {best} {acc:.1f}%{marker}")
    
    # ============================================================
    # 4. SECUENCIAS DE 2 RESULTADOS → tercero
    # ============================================================
    print("\n\n📊 4) SECUENCIA DE 2 RESULTADOS → TERCERO")
    print("-" * 80)
    
    seq2 = defaultdict(lambda: {'Banker': 0, 'Player': 0, 'Tie': 0})
    for i in range(len(rows) - 2):
        w1 = rows[i]['winner'][0]  # B, P, T
        w2 = rows[i + 1]['winner'][0]
        key = f"{w1}{w2}"
        seq2[key][rows[i + 2]['winner']] += 1
    
    print(f"  {'Seq':<6} {'B':>4} {'P':>4} {'T':>3} {'Tot':>4} {'Best':>7} {'NoTie%':>7}")
    print("  " + "-" * 45)
    for key in sorted(seq2.keys()):
        c = seq2[key]
        total = sum(c.values())
        no_tie = total - c['Tie']
        best = max(['Banker', 'Player'], key=lambda x: c[x])
        acc = c[best] / no_tie * 100 if no_tie > 0 else 0
        marker = " ★★" if acc >= 55 else ""
        print(f"  {key:<6} {c['Banker']:>4} {c['Player']:>4} {c['Tie']:>3} {total:>4} {best:>7} {acc:>5.1f}%{marker}")
    
    # ============================================================
    # 5. SECUENCIAS DE 3 RESULTADOS → cuarto
    # ============================================================
    print("\n\n📊 5) SECUENCIA DE 3 RESULTADOS → CUARTO")
    print("-" * 80)
    
    seq3 = defaultdict(lambda: {'Banker': 0, 'Player': 0, 'Tie': 0})
    for i in range(len(rows) - 3):
        w1 = rows[i]['winner'][0]
        w2 = rows[i + 1]['winner'][0]
        w3 = rows[i + 2]['winner'][0]
        key = f"{w1}{w2}{w3}"
        seq3[key][rows[i + 3]['winner']] += 1
    
    print(f"  {'Seq':<8} {'B':>4} {'P':>4} {'T':>3} {'Tot':>4} {'Best':>7} {'NoTie%':>7}")
    print("  " + "-" * 45)
    strong_seq3 = []
    for key in sorted(seq3.keys()):
        c = seq3[key]
        total = sum(c.values())
        if total < 10:
            continue
        no_tie = total - c['Tie']
        best = max(['Banker', 'Player'], key=lambda x: c[x])
        acc = c[best] / no_tie * 100 if no_tie > 0 else 0
        marker = " ★★" if acc >= 60 and no_tie >= 15 else " ★" if acc >= 55 and no_tie >= 10 else ""
        if marker:
            strong_seq3.append((key, best, acc, no_tie))
        print(f"  {key:<8} {c['Banker']:>4} {c['Player']:>4} {c['Tie']:>3} {total:>4} {best:>7} {acc:>5.1f}%{marker}")
    
    # ============================================================
    # 6. DIFERENCIA + GANADOR → siguiente
    # ============================================================
    print("\n\n📊 6) DIFERENCIA DE SCORE + GANADOR → SIGUIENTE")
    print("-" * 80)
    
    diff_patterns = defaultdict(lambda: {'Banker': 0, 'Player': 0, 'Tie': 0})
    for i in range(len(rows) - 1):
        ps, bs = rows[i]['player_score'], rows[i]['banker_score']
        diff = abs(ps - bs)
        w = rows[i]['winner']
        if w == 'Tie':
            key = f"Tie(d={diff})"
        else:
            key = f"{w[0]}+d{diff}"
        diff_patterns[key][rows[i + 1]['winner']] += 1
    
    for key in sorted(diff_patterns.keys()):
        c = diff_patterns[key]
        total = sum(c.values())
        if total < 10:
            continue
        no_tie = total - c['Tie']
        best = max(['Banker', 'Player'], key=lambda x: c[x])
        acc = c[best] / no_tie * 100 if no_tie > 0 else 0
        marker = " ★★" if acc >= 58 else " ★" if acc >= 55 else ""
        print(f"  {key:<15} B={c['Banker']:>3} P={c['Player']:>3} T={c['Tie']:>2} | Tot={total:>3} | {best} {acc:.1f}%{marker}")
    
    # ============================================================
    # 7. RACHAS → siguiente
    # ============================================================
    print("\n\n📊 7) DESPUÉS DE RACHA DE N → SIGUIENTE")
    print("-" * 80)
    
    # Calcular rachas actuales
    for streak_len in range(2, 7):
        for streak_type in ['Banker', 'Player']:
            counts = {'Banker': 0, 'Player': 0, 'Tie': 0}
            for i in range(streak_len, len(rows)):
                # Verificar si hay racha de exactamente streak_len
                is_streak = all(rows[i - j - 1]['winner'] == streak_type for j in range(streak_len))
                # y el anterior NO era del mismo tipo (para que sea exactamente streak_len)
                if streak_len < len(rows) and i - streak_len - 1 >= 0:
                    prev_same = rows[i - streak_len - 1]['winner'] == streak_type
                else:
                    prev_same = False
                
                if is_streak and not prev_same:
                    counts[rows[i]['winner']] += 1
            
            total = sum(counts.values())
            if total < 5:
                continue
            no_tie = total - counts['Tie']
            best = max(['Banker', 'Player'], key=lambda x: counts[x])
            acc = counts[best] / no_tie * 100 if no_tie > 0 else 0
            marker = " ★★" if acc >= 60 else " ★" if acc >= 55 else ""
            print(f"  {streak_type[0]}x{streak_len:<4} B={counts['Banker']:>3} P={counts['Player']:>3} T={counts['Tie']:>2} | Tot={total:>3} | {best} {acc:.1f}%{marker}")
    
    # ============================================================
    # 8. SCORE TOTAL (P+B) → siguiente
    # ============================================================
    print("\n\n📊 8) SCORE TOTAL (P+B) → SIGUIENTE")
    print("-" * 80)
    
    total_score = defaultdict(lambda: {'Banker': 0, 'Player': 0, 'Tie': 0})
    for i in range(len(rows) - 1):
        ps, bs = rows[i]['player_score'], rows[i]['banker_score']
        ts = ps + bs
        total_score[ts][rows[i + 1]['winner']] += 1
    
    for ts in sorted(total_score.keys()):
        c = total_score[ts]
        total = sum(c.values())
        if total < 10:
            continue
        no_tie = total - c['Tie']
        best = max(['Banker', 'Player'], key=lambda x: c[x])
        acc = c[best] / no_tie * 100 if no_tie > 0 else 0
        marker = " ★★" if acc >= 58 else " ★" if acc >= 55 else ""
        print(f"  Total={ts:<3} B={c['Banker']:>3} P={c['Player']:>3} T={c['Tie']:>2} | Tot={total:>3} | {best} {acc:.1f}%{marker}")
    
    # ============================================================
    # 9. SCORE DEL PERDEDOR → siguiente
    # ============================================================
    print("\n\n📊 9) SCORE DEL PERDEDOR → SIGUIENTE")
    print("-" * 80)
    
    loser_score = defaultdict(lambda: {'Banker': 0, 'Player': 0, 'Tie': 0})
    for i in range(len(rows) - 1):
        w = rows[i]['winner']
        ps, bs = rows[i]['player_score'], rows[i]['banker_score']
        if w == 'Banker':
            ls = ps  # player perdió
            key = f"B_wins_P{ls}"
        elif w == 'Player':
            ls = bs  # banker perdió
            key = f"P_wins_B{ls}"
        else:
            continue
        loser_score[key][rows[i + 1]['winner']] += 1
    
    for key in sorted(loser_score.keys()):
        c = loser_score[key]
        total = sum(c.values())
        if total < 10:
            continue
        no_tie = total - c['Tie']
        best = max(['Banker', 'Player'], key=lambda x: c[x])
        acc = c[best] / no_tie * 100 if no_tie > 0 else 0
        marker = " ★★" if acc >= 58 else " ★" if acc >= 55 else ""
        print(f"  {key:<18} B={c['Banker']:>3} P={c['Player']:>3} T={c['Tie']:>2} | Tot={total:>3} | {best} {acc:.1f}%{marker}")
    
    # ============================================================
    # RESUMEN: TOP REGLAS RENTABLES
    # ============================================================
    print("\n\n" + "=" * 80)
    print("🏆 RESUMEN: TODAS LAS REGLAS CON >55% ACCURACY Y >15 MUESTRAS")
    print("=" * 80)
    
    # Recopilar todas las reglas fuertes
    all_rules = []
    
    # Score combos
    for key, c, total, no_tie, best, acc in results_combo:
        if acc >= 55 and no_tie >= 15:
            all_rules.append((f"Score {key}", best, acc, no_tie))
    
    # Seq3
    for key, best, acc, no_tie in strong_seq3:
        if no_tie >= 15:
            all_rules.append((f"Seq3 {key}", best, acc, no_tie))
    
    all_rules.sort(key=lambda x: -x[2])
    
    print(f"\n  {'Regla':<30} {'Predicción':>10} {'Accuracy':>10} {'Muestras':>10}")
    print("  " + "-" * 65)
    for name, pred, acc, samples in all_rules:
        print(f"  {name:<30} {pred:>10} {acc:>9.1f}% {samples:>10}")
    
    await conn.close()

asyncio.run(main())
