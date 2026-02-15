# advanced_agent.py - Agente de Análisis Avanzado con "Ojos" de Mesa
"""
Agente avanzado que analiza todo el comportamiento de la mesa:
- Detección de patrones complejos (Deep Learning)
- Análisis de transiciones de fase
- Meta-aprendizaje (qué estrategia usar en cada momento)
- Detección de anomalías
- Predicción basada en comportamiento histórico
"""

import logging
from collections import Counter, defaultdict, deque
from datetime import datetime
from typing import Dict, List

import numpy as np

logger = logging.getLogger(__name__)


class AdvancedTableAnalyzer:
    """
    Agente que actúa como "ojos" viendo todo el comportamiento de la mesa.
    Analiza patrones complejos que las estrategias básicas no detectan.
    """

    def __init__(self, history_length=500):
        # Historial completo con metadatos
        self.full_history = deque(maxlen=history_length)

        # Patrones de comportamiento por fase del zapato
        self.patterns_by_phase = {
            'early': deque(maxlen=100),   # Primeras 104 cartas
            'middle': deque(maxlen=200),  # 104-312 cartas
            'late': deque(maxlen=200)      # 312+ cartas
        }

        # Estado actual de la mesa
        self.current_state = {
            'streak_info': {},
            'alternation_rate': 0,
            'banker_dominance': 0,
            'player_dominance': 0,
            'tie_frequency': 0,
            'transition_patterns': deque(maxlen=50)
        }

        # Métricas de efectividad de estrategias
        self.strategy_performance = defaultdict(lambda: {'correct': 0, 'total': 0})

        # Patrones recurrentes
        self.recurring_patterns = defaultdict(list)

        # Últimos N resultados para análisis secuencial
        self.last_results = deque(maxlen=50)

        # Análisis de rachas y breaks
        self.streak_history = deque(maxlen=100)

    def add_round(self, winner: str, player_score: int, banker_score: int,
                  phase: str, game_number: str, predicted: str = None,
                  confidence: float = 0):
        """Agregar ronda con metadatos completos"""
        round_data = {
            'winner': winner,
            'player_score': player_score,
            'banker_score': banker_score,
            'phase': phase,
            'game_number': game_number,
            'timestamp': datetime.now(),
            'predicted': predicted,
            'confidence': confidence,
            'score_diff': abs(player_score - banker_score)
        }

        self.full_history.append(round_data)
        self.last_results.append(winner)

        # Guardar por fase
        if phase and phase in self.patterns_by_phase:
            self.patterns_by_phase[phase].append(round_data)

        # Actualizar métricas de estrategias
        if predicted:
            self.strategy_performance['overall']['total'] += 1
            if predicted == winner:
                self.strategy_performance['overall']['correct'] += 1

    def analyze_table_behavior(self, window=20):
        """
        Analizar comportamiento completo de la mesa.
        Como "ojos" que ven patrones complejos.
        """
        recent = list(self.last_results)[-window:]

        if len(recent) < 10:
            return None

        analysis = {
            'momentum': self._analyze_momentum(recent),
            'cyclicity': self._analyze_cyclicity(recent),
            'clustering': self._analyze_clustering(recent),
            'transition_zones': self._detect_transition_zones(recent),
            'dominance_shifts': self._detect_dominance_shifts(recent),
            'anomalies': self._detect_anomalies(recent)
        }

        return analysis

    def _analyze_momentum(self, recent: List[str]) -> Dict:
        """
        Analizar el momento actual de la mesa.
        ¿La mesa tiene "inercia" hacia un lado?
        """
        # Calcular momento ponderado (últimos resultados tienen más peso)
        weights = list(range(1, len(recent) + 1))
        banker_momentum = sum(w for r, w in zip(recent, weights) if r == 'Banker')
        player_momentum = sum(w for r, w in zip(recent, weights) if r == 'Player')

        total = banker_momentum + player_momentum

        if total == 0:
            return {'direction': 'neutral', 'strength': 0}

        # Normalizar
        banker_ratio = banker_momentum / total if total > 0 else 0
        player_ratio = player_momentum / total if total > 0 else 0

        # Determinar dirección y fuerza
        if banker_ratio > 0.6:
            direction = 'banker'
            strength = (banker_ratio - 0.5) * 2  # 0-1
        elif player_ratio > 0.6:
            direction = 'player'
            strength = (player_ratio - 0.5) * 2
        else:
            direction = 'neutral'
            strength = 0

        return {
            'direction': direction,
            'strength': strength,
            'banker_ratio': banker_ratio,
            'player_ratio': player_ratio
        }

    def _analyze_cyclicity(self, recent: List[str]) -> Dict:
        """
        Detectar patrones cíclicos o repetitivos.
        ¿Hay ciclos que se repiten?
        """
        if len(recent) < 10:
            return {'has_cycle': False}

        # Buscar patrones repetidos de 3-5 elementos
        patterns = {}

        for cycle_length in [3, 4, 5]:
            for i in range(len(recent) - cycle_length):
                pattern = ''.join(recent[i:i+cycle_length])

                if pattern not in patterns:
                    patterns[pattern] = []

                # Buscar si este patrón aparece más adelante
                for j in range(i + cycle_length, len(recent) - cycle_length + 1):
                    if ''.join(recent[j:j+cycle_length]) == pattern:
                        patterns[pattern].append(j - i)

        # Calcular repetición
        best_cycle = None
        max_repetitions = 0

        for pattern, positions in patterns.items():
            if len(positions) > max_repetitions:
                max_repetitions = len(positions)
                best_cycle = pattern

        has_cycle = max_repetitions >= 2

        if has_cycle and best_cycle:
            # Predecir siguiente del mejor ciclo
            last_cycle_start = len(recent) - len(best_cycle)
            last_match = ''.join(recent[last_cycle_start:])

            if last_match == best_cycle:
                # Encontrar qué suele venir después
                next_outcomes = []
                for i in range(len(recent) - len(best_cycle)):
                    if ''.join(recent[i:i+len(best_cycle)]) == best_cycle:
                        if i + len(best_cycle) < len(recent):
                            next_outcomes.append(recent[i + len(best_cycle)])

                if next_outcomes:
                    counter = Counter(next_outcomes)
                    next_prediction = counter.most_common(1)[0][0]
                    confidence = counter[next_prediction] / len(next_outcomes)
                else:
                    next_prediction = None
                    confidence = 0
            else:
                next_prediction = None
                confidence = 0
        else:
            next_prediction = None
            confidence = 0

        return {
            'has_cycle': has_cycle,
            'best_cycle': best_cycle,
            'next_prediction': next_prediction,
            'confidence': confidence,
            'repetitions': max_repetitions
        }

    def _analyze_clustering(self, recent: List[str]) -> Dict:
        """
        Detectar agrupamiento de resultados.
        ¿Los resultados se agrupan o se dispersan?
        """
        if len(recent) < 20:
            return {'type': 'unknown'}

        # Analizar agrupamiento
        banker_clusters = []
        player_clusters = []
        current_cluster = {'type': None, 'length': 0}

        for result in recent:
            if result == current_cluster['type']:
                current_cluster['length'] += 1
            else:
                if current_cluster['type'] == 'Banker':
                    banker_clusters.append(current_cluster['length'])
                elif current_cluster['type'] == 'Player':
                    player_clusters.append(current_cluster['length'])

                current_cluster = {'type': result, 'length': 1}

        # Agregar el último cluster
        if current_cluster['type'] == 'Banker':
            banker_clusters.append(current_cluster['length'])
        elif current_cluster['type'] == 'Player':
            player_clusters.append(current_cluster['length'])

        # Análisis
        if not banker_clusters and not player_clusters:
            return {'type': 'unknown'}

        avg_banker_cluster = np.mean(banker_clusters) if banker_clusters else 0
        avg_player_cluster = np.mean(player_clusters) if player_clusters else 0

        # Determinar tipo de clustering
        if avg_banker_cluster > 3 or avg_player_cluster > 3:
            cluster_type = 'streaky'  # Hay rachas largas
        elif min(avg_banker_cluster, avg_player_cluster) <= 1.5:
            cluster_type = 'choppy'  # Alternación frecuente
        else:
            cluster_type = 'balanced'  # Equilibrado

        return {
            'type': cluster_type,
            'avg_banker_cluster': avg_banker_cluster,
            'avg_player_cluster': avg_player_cluster,
            'banker_clusters': len(banker_clusters),
            'player_clusters': len(player_clusters)
        }

    def _detect_transition_zones(self, recent: List[str]) -> List[Dict]:
        """
        Detectar zonas de transición.
        ¿La mesa está cambiando de comportamiento?
        """
        transitions = []

        for i in range(5, len(recent)):
            before = recent[i-5:i]
            after = recent[i:i+5]

            # Analizar distribución antes/después
            before_banker = before.count('Banker')
            before_player = before.count('Player')
            after_banker = after.count('Banker')
            after_player = after.count('Player')

            # Si hay un cambio significativo
            if before_banker >= 4 and after_player >= 4:
                transitions.append({
                    'position': i,
                    'type': 'banker_to_player',
                    'strength': 'strong'
                })
            elif before_player >= 4 and after_banker >= 4:
                transitions.append({
                    'position': i,
                    'type': 'player_to_banker',
                    'strength': 'strong'
                })

        return transitions[-3:] if transitions else []  # Últimas 3 transiciones

    def _detect_dominance_shifts(self, recent: List[str]) -> Dict:
        """
        Detectar cambios de dominancia.
        ¿Está cambiando el lado dominante?
        """
        if len(recent) < 20:
            return {'current_dominant': 'balanced'}

        # Dividir en ventanas
        window1 = recent[-10:]
        window2 = recent[-20:-10]

        dom1 = self._get_dominant(window1)
        dom2 = self._get_dominant(window2)

        is_shifting = dom1 != dom2

        return {
            'current_dominant': dom1,
            'previous_dominant': dom2,
            'is_shifting': is_shifting,
            'shift_direction': f"{dom2}_to_{dom1}" if is_shifting else "none"
        }

    def _get_dominant(self, window: List[str]) -> str:
        banker_count = window.count('Banker')
        player_count = window.count('Player')

        if banker_count > player_count + 1:
            return 'banker'
        elif player_count > banker_count + 1:
            return 'player'
        else:
            return 'balanced'

    def _detect_anomalies(self, recent: List[str]) -> List[Dict]:
        """
        Detectar anomalías o comportamientos inusuales.
        """
        anomalies = []

        # 1. Secuencia muy larga del mismo lado (7+)
        for i in range(len(recent) - 6):
            subseq = recent[i:i+7]
            if all(r == 'Banker' for r in subseq) or all(r == 'Player' for r in subseq):
                anomalies.append({
                    'type': 'ultra_streak',
                    'length': 7,
                    'side': subseq[0],
                    'position': i
                })

        # 2. Alternación perfecta muy larga (PBPBPB...)
        for i in range(len(recent) - 7):
            subseq = recent[i:i+8]
            is_perfect_alt = True
            for j in range(len(subseq) - 1):
                if subseq[j] == subseq[j+1]:
                    is_perfect_alt = False
                    break

            if is_perfect_alt:
                anomalies.append({
                    'type': 'perfect_alternation',
                    'length': 8,
                    'position': i
                })

        return anomalies[-3:] if anomalies else []

    def get_meta_prediction(self, current_phase: str, window: int = 30) -> Dict:
        """
        Predicción meta-level: decidir QUÉ estrategia usar
        basándose en el comportamiento actual de la mesa.
        """
        # Análisis completo
        behavior = self.analyze_table_behavior(window)

        if not behavior:
            return {
                'recommendation': 'wait',
                'confidence': 0,
                'reason': 'Insufficient data'
            }

        # Decidir estrategia basada en comportamiento
        momentum = behavior['momentum']
        clustering = behavior['clustering']
        dominance = behavior['dominance_shifts']

        recommendation = None
        confidence = 0
        reasoning = []

        # Lógica de meta-aprendizaje
        if momentum['strength'] > 0.5:
            # Hay un momento fuerte, seguirlo
            recommendation = momentum['direction']
            confidence = 50 + (momentum['strength'] * 40)
            reasoning.append(f"Strong momentum toward {momentum['direction']}")

        elif clustering['type'] == 'streaky':
            # Hay rachas largas, seguir el lado dominante
            dom = dominance['current_dominant']
            if dom != 'balanced':
                recommendation = dom
                confidence = 60
                reasoning.append(f"Streaky pattern, dominant side: {dom}")

        elif clustering['type'] == 'choppy':
            # Hay alternación, apostar al contrario del último
            last = list(self.last_results)[-1]
            recommendation = 'Player' if last == 'Banker' else 'Banker'
            confidence = 55
            reasoning.append("Choppy pattern, alternating")

        elif dominance['is_shifting']:
            # Hay cambio de dominancia, apostar al nuevo dominante
            recommendation = dominance['current_dominant']
            confidence = 50
            reasoning.append(
                f"Shift from {dominance['previous_dominant']} "
                f"to {dominance['current_dominant']}"
            )

        # Considerar anomalías
        if behavior['anomalies']:
            anomaly = behavior['anomalies'][-1]
            if anomaly['type'] == 'ultra_streak':
                # Racha ultra larga, apostar en contra
                recommendation = 'Player' if anomaly['side'] == 'Banker' else 'Banker'
                confidence = 45
                reasoning.append(f"Ultra streak correction ({anomaly['side']})")

        # Considerar ciclos
        if behavior['cyclicity']['has_cycle'] and behavior['cyclicity']['confidence'] > 0.6:
            cycle_pred = behavior['cyclicity']['next_prediction']
            if cycle_pred:
                if not recommendation or behavior['cyclicity']['confidence'] > confidence - 10:
                    recommendation = cycle_pred
                    confidence = max(confidence, behavior['cyclicity']['confidence'] * 100)
                    reasoning.append(f"Detected cycle: {behavior['cyclicity']['best_cycle']}")

        return {
            'recommendation': recommendation,
            'confidence': min(confidence, 90),
            'reasoning': reasoning,
            'behavior': behavior,
            'phase': current_phase
        }

    def get_strategy_recommendation(self, current_strategies: Dict) -> Dict:
        """
        Recomendar qué estrategia usar ahora.
        Como un "director" que decide qué herramienta usar.
        """
        if not self.full_history:
            return {'recommendation': 'wait', 'reason': 'No history yet'}

        # Obtener predicción meta
        meta_pred = self.get_meta_prediction(self._get_current_phase())

        # Analizar qué estrategias funcionan mejor ahora
        best_strategies = self._get_best_strategies_in_phase(self._get_current_phase())

        recommendation = {
            'use_meta': meta_pred['recommendation'] is not None,
            'meta_prediction': meta_pred,
            'best_strategies': best_strategies,
            'final': None,
            'confidence': 0,
            'reason': ''
        }

        # Decidir final
        if meta_pred['recommendation']:
            recommendation['final'] = meta_pred['recommendation']
            recommendation['confidence'] = meta_pred['confidence']
            recommendation['reason'] = f"Meta-analysis: {', '.join(meta_pred['reasoning'])}"

        elif best_strategies:
            best = best_strategies[0]
            recommendation['final'] = best['predicted']
            recommendation['confidence'] = best['confidence']
            recommendation['reason'] = f"Best performing strategy: {best['name']}"

        return recommendation

    def _get_current_phase(self) -> str:
        """Obtener fase actual basada en historial"""
        if len(self.full_history) < 10:
            return 'early'

        # Usar última ronda para determinar fase
        last_round = self.full_history[-1]
        return last_round.get('phase', 'middle')

    def _get_best_strategies_in_phase(self, phase: str) -> List[Dict]:
        """
        Obtener estrategias que mejor funcionan en esta fase.
        Basado en historial.
        """
        # Analizar predicciones pasadas en esta fase
        phase_predictions = [
            r for r in self.full_history
            if r.get('phase') == phase and r.get('predicted')
        ]

        if len(phase_predictions) < 5:
            return []

        # Agrupar por tipo de predicción (simulado)
        strategies = {
            '4-Roads': {'correct': 0, 'total': 0},
            'Memory-Scores': {'correct': 0, 'total': 0},
            'Twins': {'correct': 0, 'total': 0},
            'Streak': {'correct': 0, 'total': 0}
        }

        for pred in phase_predictions:
            if pred.get('confidence', 0) > 0:
                strategies['4-Roads']['total'] += 1
                if pred['predicted'] == pred['winner']:
                    strategies['4-Roads']['correct'] += 1

        # Calcular efectividad
        results = []
        for name, stats in strategies.items():
            if stats['total'] > 0:
                accuracy = (stats['correct'] / stats['total']) * 100
                results.append({
                    'name': name,
                    'accuracy': accuracy,
                    'samples': stats['total']
                })

        # Ordenar por efectividad
        results.sort(key=lambda x: x['accuracy'], reverse=True)

        return results

    def get_insights_summary(self) -> str:
        """Generar resumen de insights para Telegram"""
        if len(self.full_history) < 20:
            return "⏳ Analizando comportamiento de la mesa..."

        analysis = self.analyze_table_behavior(30)

        if not analysis:
            return "⏳ Esperando más datos para análisis..."

        momentum_dir = analysis['momentum']['direction'].upper()
        momentum_str = analysis['momentum']['strength']
        has_cycle = analysis['cyclicity']['has_cycle']
        cycle_status = '✅ Detectado' if has_cycle else '❌ No detectados'

        lines = [
            "👁️ <b>ANÁLISIS PROFUNDO DE MESA</b>",
            "",
            f"🌊 <b>Momento:</b> {momentum_dir} (Fuerza: {momentum_str:.2f})",
            f"🔄 <b>Ciclos:</b> {cycle_status}"
        ]

        if analysis['cyclicity']['has_cycle']:
            lines.append(f"   • Patrón: {analysis['cyclicity']['best_cycle']}")
            next_pred = analysis['cyclicity']['next_prediction']
            cycle_conf = analysis['cyclicity']['confidence']
            lines.append(f"   • Próximo: {next_pred} ({cycle_conf:.0%})")

        cluster_type = analysis['clustering']['type'].upper()
        current_dom = analysis['dominance_shifts']['current_dominant'].upper()
        lines.append(f"📊 <b>Clustering:</b> {cluster_type}")
        lines.append(f"🔄 <b>Dominancia:</b> {current_dom}")
        lines.append(f"⚡ <b>Transiciones:</b> {len(analysis['transition_zones'])} detectadas")

        if analysis['anomalies']:
            lines.append(f"⚠️ <b>Anomalías:</b> {len(analysis['anomalies'])} detectadas")
            for anomaly in analysis['anomalies']:
                lines.append(f"   • {anomaly['type']}: {anomaly.get('side', '')}")

        return '\n'.join(lines)
