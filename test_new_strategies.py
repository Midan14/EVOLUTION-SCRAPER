#!/usr/bin/env python3
"""
Test de las 4 nuevas estrategias avanzadas de Baccarat
"""
import sys
from baccarat_strategies import BaccaratStrategies
from road_analyzer import RoadAnalyzer

def test_strategies():
    print("🧪 Testing Nuevas Estrategias Avanzadas para Baccarat\n")
    
    # Inicializar strategias
    strategies = BaccaratStrategies()
    
    # Datos de prueba simulando una sesión real
    test_data = [
        # Primeras 20 rondas - dominio Banker con scores altos
        {'winner': 'Banker', 'player_score': 4, 'banker_score': 8, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Banker', 'player_score': 3, 'banker_score': 7, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Player', 'player_score': 9, 'banker_score': 6, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Banker', 'player_score': 5, 'banker_score': 8, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Banker', 'player_score': 2, 'banker_score': 6, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Player', 'player_score': 7, 'banker_score': 4, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Banker', 'player_score': 3, 'banker_score': 8, 'player_pair': False, 'banker_pair': True},
        {'winner': 'Banker', 'player_score': 1, 'banker_score': 6, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Player', 'player_score': 9, 'banker_score': 7, 'player_pair': True, 'banker_pair': False},
        {'winner': 'Banker', 'player_score': 4, 'banker_score': 7, 'player_pair': False, 'banker_pair': False},
        
        # Siguientes 20 - scores pares dominan
        {'winner': 'Banker', 'player_score': 3, 'banker_score': 8, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Player', 'player_score': 6, 'banker_score': 5, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Banker', 'player_score': 5, 'banker_score': 8, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Player', 'player_score': 4, 'banker_score': 3, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Banker', 'player_score': 1, 'banker_score': 6, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Player', 'player_score': 8, 'banker_score': 6, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Banker', 'player_score': 3, 'banker_score': 4, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Player', 'player_score': 2, 'banker_score': 1, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Banker', 'player_score': 5, 'banker_score': 6, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Player', 'player_score': 8, 'banker_score': 7, 'player_pair': True, 'banker_pair': False},
        
        # Siguientes 20 - Clustering Player
        {'winner': 'Player', 'player_score': 7, 'banker_score': 6, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Player', 'player_score': 9, 'banker_score': 8, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Player', 'player_score': 8, 'banker_score': 5, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Player', 'player_score': 7, 'banker_score': 4, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Banker', 'player_score': 3, 'banker_score': 6, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Player', 'player_score': 9, 'banker_score': 7, 'player_pair': True, 'banker_pair': False},
        {'winner': 'Player', 'player_score': 8, 'banker_score': 6, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Player', 'player_score': 7, 'banker_score': 5, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Player', 'player_score': 6, 'banker_score': 4, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Banker', 'player_score': 2, 'banker_score': 5, 'player_pair': False, 'banker_pair': False},
        
        # Últimas 10 - alternancia
        {'winner': 'Banker', 'player_score': 3, 'banker_score': 7, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Player', 'player_score': 8, 'banker_score': 6, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Banker', 'player_score': 4, 'banker_score': 9, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Player', 'player_score': 7, 'banker_score': 5, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Banker', 'player_score': 2, 'banker_score': 6, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Player', 'player_score': 9, 'banker_score': 8, 'player_pair': True, 'banker_pair': False},
        {'winner': 'Banker', 'player_score': 3, 'banker_score': 7, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Player', 'player_score': 8, 'banker_score': 6, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Banker', 'player_score': 4, 'banker_score': 7, 'player_pair': False, 'banker_pair': False},
        {'winner': 'Player', 'player_score': 6, 'banker_score': 5, 'player_pair': False, 'banker_pair': False},
    ]
    
    # Agregar rondas
    print("📝 Agregando 50 rondas de prueba...")
    for i, round_data in enumerate(test_data, 1):
        strategies.add_round(
            winner=round_data['winner'],
            player_score=round_data['player_score'],
            banker_score=round_data['banker_score'],
            player_pair=round_data['player_pair'],
            banker_pair=round_data['banker_pair']
        )
    
    print(f"✅ {len(test_data)} rondas agregadas\n")
    
    # Test 1: Score Distribution (0-9)
    print("=" * 50)
    print("1️⃣ SCORE DISTRIBUTION (Análisis 0-9)")
    print("=" * 50)
    score_dist = strategies.score_distribution_prediction()
    if score_dist:
        print(f"✅ Predicción: {score_dist['predicted']}")
        print(f"   Confianza: {score_dist['confidence']:.1f}%")
        print(f"   Score Caliente: {score_dist['hot_score']}")
        print(f"   Frecuencia: {score_dist['score_frequency']}x")
        print(f"   Stats: {score_dist['score_stats']}")
    else:
        print("❌ No se detectó patrón de scores")
    
    print("\n")
    
    # Test 2: Sector Dominance
    print("=" * 50)
    print("2️⃣ SECTOR DOMINANCE")
    print("=" * 50)
    sector_dom = strategies.sector_dominance_prediction()
    if sector_dom:
        print(f"✅ Predicción: {sector_dom['predicted']}")
        print(f"   Confianza: {sector_dom['confidence']:.1f}%")
        print(f"   Razón: {sector_dom['reason']}")
        print(f"   Sectores: {' → '.join(sector_dom['sectors'])}")
    else:
        print("❌ No se detectó dominancia de sector")
    
    print("\n")
    
    # Test 3: Even/Odd Scores
    print("=" * 50)
    print("3️⃣ EVEN/ODD SCORES")
    print("=" * 50)
    even_odd = strategies.even_odd_scores_prediction()
    if even_odd:
        print(f"✅ Predicción: {even_odd['predicted']}")
        print(f"   Confianza: {even_odd['confidence']:.1f}%")
        print(f"   Tipo Score: {even_odd['score_type']}")
        print(f"   Even Ratio: {even_odd['even_ratio']}")
        print(f"   Odd Ratio: {even_odd['odd_ratio']}")
    else:
        print("❌ No se detectó patrón par/impar")
    
    print("\n")
    
    # Test 4: Clustering
    print("=" * 50)
    print("4️⃣ CLUSTERING DETECTION")
    print("=" * 50)
    clustering = strategies.clustering_detection()
    if clustering:
        print(f"✅ Predicción: {clustering['predicted']}")
        print(f"   Confianza: {clustering['confidence']:.1f}%")
        print(f"   Razón: {clustering['reason']}")
        print(f"   Clusters totales: {clustering['cluster_count']}")
        print(f"   Cluster activo: {'Sí' if clustering['active_cluster'] else 'No'}")
    else:
        print("❌ No se detectó clustering")
    
    print("\n")
    
    # Test 5: Consenso integrado
    print("=" * 50)
    print("5️⃣ CONSENSO CON NUEVAS ESTRATEGIAS")
    print("=" * 50)
    consensus = strategies.four_roads_consensus()
    if consensus:
        print(f"✅ Predicción Final: {consensus['predicted']}")
        print(f"   Confianza: {consensus['confidence']:.1f}%")
        print(f"   Estrategias activas: {consensus['total_strategies']}")
        print(f"   Votos: 🔴{consensus['votes']['Banker']} vs 🔵{consensus['votes']['Player']}")
        print(f"   Unánime: {'Sí ✅' if consensus['unanimous'] else 'No ⚠️'}")
        print(f"\n   Estrategias participantes:")
        for strat in consensus['strategies']:
            emoji = '🔴' if strat['predicted'] == 'Banker' else '🔵'
            print(f"     {emoji} {strat['strategy']}: {strat['confidence']:.1f}%")
    else:
        print("❌ No hay consenso suficiente")
    
    print("\n" + "=" * 50)
    print("✅ TEST COMPLETADO")
    print("=" * 50)

if __name__ == "__main__":
    test_strategies()
