#!/usr/bin/env python3
"""Analizar accuracy real de TODAS las estrategias y del sistema general"""
import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect(database='dragon_bot')
    
    print("=" * 60)
    print("ANÁLISIS COMPLETO DE ACCURACY")
    print("=" * 60)
    
    # 1. Accuracy general de predicciones ML
    print("\n--- ML PREDICTIONS (predicción final enviada) ---")
    ml = await conn.fetch("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as correct,
            SUM(CASE WHEN NOT was_correct THEN 1 ELSE 0 END) as wrong
        FROM ml_predictions
        WHERE actual_winner IS NOT NULL
    """)
    if ml and ml[0]['total'] > 0:
        t, c, w = ml[0]['total'], ml[0]['correct'], ml[0]['wrong']
        print(f"  Total: {t} | Correct: {c} | Wrong: {w} | Accuracy: {c/t*100:.1f}%")
    
    # 2. Accuracy por estrategia individual
    print("\n--- STRATEGY VOTES (cada estrategia individual) ---")
    strats = await conn.fetch("""
        SELECT 
            strategy_name,
            COUNT(*) as total,
            SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as correct,
            ROUND(100.0 * SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) / COUNT(*), 1) as accuracy
        FROM strategy_votes
        WHERE actual_winner IS NOT NULL AND actual_winner != 'Tie'
        GROUP BY strategy_name
        ORDER BY accuracy DESC
    """)
    
    print(f"  {'Estrategia':<25} {'Total':>6} {'OK':>5} {'Fail':>5} {'Acc%':>6}")
    print("  " + "-" * 50)
    for s in strats:
        fail = s['total'] - s['correct']
        marker = "✅" if s['accuracy'] >= 50 else "❌"
        print(f"  {marker} {s['strategy_name']:<23} {s['total']:>6} {s['correct']:>5} {fail:>5} {s['accuracy']:>5}%")
    
    # 3. Accuracy de las últimas 50 predicciones
    print("\n--- ÚLTIMAS 50 PREDICCIONES ML ---")
    recent = await conn.fetch("""
        SELECT predicted_winner, actual_winner, was_correct, confidence, created_at
        FROM ml_predictions
        WHERE actual_winner IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 50
    """)
    if recent:
        correct_count = sum(1 for r in recent if r['was_correct'])
        total_count = len(recent)
        print(f"  Últimas {total_count}: {correct_count}/{total_count} = {correct_count/total_count*100:.1f}%")
        
        # Desglose por confianza
        high_conf = [r for r in recent if r['confidence'] and r['confidence'] >= 60]
        mid_conf = [r for r in recent if r['confidence'] and 50 <= r['confidence'] < 60]
        low_conf = [r for r in recent if r['confidence'] and r['confidence'] < 50]
        
        if high_conf:
            hc = sum(1 for r in high_conf if r['was_correct'])
            print(f"  Confianza >= 60%: {hc}/{len(high_conf)} = {hc/len(high_conf)*100:.1f}%")
        if mid_conf:
            mc = sum(1 for r in mid_conf if r['was_correct'])
            print(f"  Confianza 50-59%: {mc}/{len(mid_conf)} = {mc/len(mid_conf)*100:.1f}%")
        if low_conf:
            lc = sum(1 for r in low_conf if r['was_correct'])
            print(f"  Confianza < 50%: {lc}/{len(low_conf)} = {lc/len(low_conf)*100:.1f}%")
    
    # 4. Cuántas veces cada estrategia CAMBIÓ el resultado final
    print("\n--- ANÁLISIS: ¿Qué estrategias votan MAL consistentemente? ---")
    bad_strats = await conn.fetch("""
        SELECT 
            strategy_name,
            predicted_winner,
            actual_winner,
            COUNT(*) as times
        FROM strategy_votes
        WHERE actual_winner IS NOT NULL AND actual_winner != 'Tie' AND NOT was_correct
        GROUP BY strategy_name, predicted_winner, actual_winner
        ORDER BY times DESC
        LIMIT 20
    """)
    for b in bad_strats:
        print(f"  {b['strategy_name']}: Predijo {b['predicted_winner']} pero fue {b['actual_winner']} ({b['times']}x)")
    
    # 5. Últimas 20 predicciones detalladas
    print("\n--- ÚLTIMAS 20 PREDICCIONES (detalle) ---")
    last20 = await conn.fetch("""
        SELECT predicted_winner, actual_winner, was_correct, confidence, created_at
        FROM ml_predictions
        WHERE actual_winner IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 20
    """)
    for r in last20:
        mark = "✅" if r['was_correct'] else "❌"
        conf = r['confidence'] or 0
        print(f"  {mark} Predijo: {r['predicted_winner']:<7} Real: {r['actual_winner']:<7} Conf: {conf:.0f}% | {r['created_at']}")
    
    # 6. Distribución real P vs B
    print("\n--- DISTRIBUCIÓN REAL (últimas 100 rondas) ---")
    dist = await conn.fetch("""
        SELECT winner, COUNT(*) as cnt
        FROM baccarat_rounds
        ORDER BY created_at DESC
        LIMIT 100
    """)
    # Reagrupar
    dist2 = await conn.fetch("""
        SELECT winner, COUNT(*) as cnt
        FROM (SELECT winner FROM baccarat_rounds ORDER BY created_at DESC LIMIT 100) sub
        GROUP BY winner
    """)
    for d in dist2:
        print(f"  {d['winner']}: {d['cnt']}")
    
    await conn.close()

asyncio.run(main())
