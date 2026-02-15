# road_analyzer.py - MEJORADO
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class RoadAnalyzer:
    """Analiza los roads de baccarat para patrones avanzados - MEJORADO"""

    def __init__(self):
        self.big_road = []
        self.big_eye_road = []
        self.small_road = []
        self.cockroach_road = []
        self.bead_plate = []

    def update_from_websocket(self, road_data):
        """Actualizar roads desde datos del WebSocket"""
        if not road_data:
            return

        self.big_road = road_data.get("bigRoad", [])
        self.big_eye_road = road_data.get("bigEyeRoad", [])
        self.small_road = road_data.get("smallRoad", [])
        self.cockroach_road = road_data.get("cockroachRoad", [])
        self.bead_plate = road_data.get("beadPlate", [])

    def update_from_history(self, history_list):
        """Reconstruir roads desde lista plana de resultados"""
        if not history_list:
            return

        self.big_road = self._build_big_road(history_list)
        self.big_eye_road = self._build_derived_road(self.big_road, delta=1)
        self.small_road = self._build_derived_road(self.big_road, delta=2)
        self.cockroach_road = self._build_derived_road(self.big_road, delta=3)

    def _build_big_road(self, history):
        """Construir Big Road (columnas) desde historial"""
        if not history:
            return []

        road = []
        current_col = []
        last_winner = None

        filtered_hist = [h for h in history if h.lower() in ("banker", "player", "b", "p")]

        for res in filtered_hist:
            w = "banker" if res.lower() in ("banker", "b") else "player"

            if last_winner is None:
                current_col.append(w)
                last_winner = w
            elif w == last_winner:
                current_col.append(w)
            else:
                road.append(current_col)
                current_col = [w]
                last_winner = w

        if current_col:
            road.append(current_col)

        return road

    def _build_derived_road(self, big_road, delta):
        """Construir Derived Road (Big Eye=1, Small=2, Cockroach=3)"""
        if not big_road or len(big_road) <= delta:
            return []

        derived = []
        current_col = []
        last_color = None  # 'red' or 'blue'

        nodes_to_process = []
        for k, col in enumerate(big_road):
            for m, _ in enumerate(col):
                is_start_of_col = m == 0

                if is_start_of_col:
                    if k < delta + 1:
                        continue
                else:
                    if k < delta:
                        continue

                nodes_to_process.append((k, m, is_start_of_col))

        for k, m, is_start in nodes_to_process:
            color = None
            if is_start:
                col_1 = big_road[k - 1]
                col_2 = big_road[k - 1 - delta]
                color = "red" if len(col_1) == len(col_2) else "blue"
            else:
                target_col = big_road[k - delta]
                if m < len(target_col):
                    color = "red"
                else:
                    color = "blue"

            if last_color is None:
                current_col.append(color)
                last_color = color
            elif color == last_color:
                current_col.append(color)
            else:
                derived.append(current_col)
                current_col = [color]
                last_color = color

        if current_col:
            derived.append(current_col)

        return derived

    def _last_road_signal(self, road, mapping):
        if not road:
            return None

        last_cell = None
        for column in reversed(road):
            if column:
                last_cell = column[-1]
                break

        if not last_cell:
            return None

        return mapping.get(last_cell)

    def get_four_roads_consensus(self):
        """Regla 4 roads mejorada: análisis más sofisticado"""
        if not self.big_road or len(self.big_road) < 3:
            return None

        # 1. Big Road Last Result
        big_road_signal = self._last_road_signal(
            self.big_road, {"banker": "Banker", "player": "Player"}
        )
        if not big_road_signal:
            return None

        # 2. Derived Roads Last Color
        derived_signals = []
        for road in [self.big_eye_road, self.small_road, self.cockroach_road]:
            sig = self._last_road_signal(road, {"red": "red", "blue": "blue"})
            if sig:
                derived_signals.append(sig)

        if not derived_signals:
            return None

        # 3. Count Reds con ponderación
        red_count = derived_signals.count("red")
        blue_count = derived_signals.count("blue")

        # 4. Logic mejorada
        predicted = big_road_signal
        confidence = 0

        # Mayor ponderación para más confirmaciones
        if red_count == 3:
            # Unanimidad en derived roads
            confidence = 80
        elif red_count == 2:
            # 2 de 3 confirman
            confidence = 65
        elif red_count == 1 and blue_count == 2:
            # 1 rojo, 2 azules - moderado
            confidence = 45
            # En este caso, considerar seguir el color azul
            predicted = "Player" if big_road_signal == "Banker" else "Banker"
        else:
            # Menos de 1 rojo o muy disperso
            return None

        match_count = (red_count + 1) if predicted == big_road_signal else (blue_count + 1)
        return {
            "predicted": predicted,
            "confidence": confidence,
            "match_count": match_count,
            "signals": [f"BigRoad:{predicted}"] + derived_signals,
            "counts": {"RedDerived": red_count, "BlueDerived": blue_count},
            "unanimous": (red_count == 3),
        }

    def detect_dragon_tail(self):
        """Detectar cola de dragón (racha larga que baja)"""
        if not self.big_road or len(self.big_road) < 2:
            return None

        last_column = self.big_road[-1]

        if len(last_column) >= 6:
            return {
                "pattern": "DRAGON_TAIL",
                "length": len(last_column),
                "confidence": min(60 + (len(last_column) * 5), 90),
                "prediction": "CHANGE",
            }
        return None

    def analyze_big_eye_pattern(self):
        """Analizar Big Eye Road para regularidad"""
        if not self.big_eye_road or len(self.big_eye_road) < 3:
            return None

        recent = self.big_eye_road[-3:]
        red_count = sum(1 for col in recent for cell in col if cell == "red")
        blue_count = sum(1 for col in recent for cell in col if cell == "blue")

        if red_count > blue_count * 2:
            return {"pattern": "IRREGULAR", "prediction": "Banker", "confidence": 55}
        elif blue_count > red_count * 2:
            return {"pattern": "REGULAR", "prediction": "Player", "confidence": 55}

        return None

    def detect_chop(self):
        """Detectar patrón de alternancia (chop)"""
        if not self.big_road or len(self.big_road) < 5:
            return None

        recent_5 = self.big_road[-5:]
        single_results = [col for col in recent_5 if len(col) == 1]

        if len(single_results) >= 4:
            alternating = True
            for i in range(len(single_results) - 1):
                if single_results[i][0] == single_results[i + 1][0]:
                    alternating = False
                    break

            if alternating:
                last_result = single_results[-1][0]
                next_prediction = "Player" if last_result == "banker" else "Banker"

                return {"pattern": "CHOP", "confidence": 70, "prediction": next_prediction}

        return None

    def detect_streak_from_roads(self):
        """Detectar rachas usando todos los roads - MEJORADO"""
        if not self.big_road:
            return None

        last_column = self.big_road[-1]
        streak_length = len(last_column)

        if streak_length < 3:
            return None

        streak_color = last_column[0]

        # Contar confirmaciones en derived roads
        confirming_patterns = 0
        for road in [self.small_road, self.cockroach_road]:
            if road and len(road) >= 2:
                confirming_patterns += 1

        # Trend Following para rachas moderadas (3-6)
        # Break para rachas muy largas (7+) — unificado con baccarat_strategies
        if streak_length >= 7:
            prediction = "Player" if streak_color == "banker" else "Banker"
            action = "BREAK_STREAK"
            confidence = 55 + (confirming_patterns * 8)
        else:
            # Racha de 3-6: seguirla (trend following)
            prediction = "Banker" if streak_color == "banker" else "Player"
            action = "FOLLOW_STREAK"
            confidence = 50 + (streak_length * 3) + (confirming_patterns * 10)

        confidence = min(confidence, 85)

        return {
            "pattern": f"STREAK_{streak_length}",
            "current": streak_color.upper(),
            "confidence": confidence,
            "prediction": prediction,
            "action": action,
        }

    def detect_natural_pattern(self):
        """NUEVO: Detectar patrones de naturales"""
        if not self.big_road or len(self.big_road) < 2:
            return None

        # Analizar las últimas 2 columnas para patrones de naturales
        recent_cols = self.big_road[-2:]

        # Simplificado: detectar alternación fuerte
        if len(recent_cols) == 2:
            col1_color = recent_cols[0][0]
            col2_color = recent_cols[1][0]

            if col1_color != col2_color and len(recent_cols[1]) == 1:
                # Alternación fuerte después de columna corta
                return {
                    "pattern": "ALTERNATING",
                    "confidence": 55,
                    "prediction": "Banker" if col2_color == "player" else "Player",
                }

        return None

    # detect_zigzag removido: duplicaba la lógica de detect_chop
    # Ambos detectaban alternancia P-B-P-B con columnas de longitud 1,
    # generando votos duplicados en el consenso de roads.

    def get_advanced_road_prediction(self):
        """Predicción combinada de todos los análisis de roads - MEJORADO"""
        predictions = []

        dragon = self.detect_dragon_tail()
        if dragon:
            predictions.append(dragon)

        big_eye = self.analyze_big_eye_pattern()
        if big_eye:
            predictions.append(big_eye)

        chop = self.detect_chop()
        if chop:
            predictions.append(chop)

        streak = self.detect_streak_from_roads()
        if streak:
            predictions.append(streak)

        # zigzag removido: duplicaba detect_chop

        natural = self.detect_natural_pattern()
        if natural:
            predictions.append(natural)

        if not predictions:
            return None

        banker_votes = sum(1 for p in predictions if p.get("prediction") == "Banker")
        player_votes = sum(1 for p in predictions if p.get("prediction") == "Player")

        # Votación ponderada por confianza
        banker_confidence = sum(
            p.get("confidence", 50) for p in predictions if p.get("prediction") == "Banker"
        )
        player_confidence = sum(
            p.get("confidence", 50) for p in predictions if p.get("prediction") == "Player"
        )

        if banker_votes > player_votes:
            final_prediction = "Banker"
            confidence = banker_confidence / banker_votes
        elif player_votes > banker_votes:
            final_prediction = "Player"
            confidence = player_confidence / player_votes
        else:
            # Empate: usar el patrón más fuerte
            strongest = max(predictions, key=lambda x: x.get("confidence", 0))
            final_prediction = strongest.get("prediction", "Banker")
            confidence = strongest.get("confidence", 50)

        return {
            "predicted": final_prediction,
            "confidence": min(confidence, 85),
            "patterns_detected": [p.get("pattern") for p in predictions],
            "details": predictions,
            "votes": {"Banker": banker_votes, "Player": player_votes},
        }

    def format_roads_for_telegram(self):
        """Formatear roads para mostrar en Telegram"""
        if not self.big_road:
            return "📊 Roads no disponibles aún"

        recent_results = []
        for column in self.big_road[-10:]:
            for result in column:
                recent_results.append("🔴" if result == "banker" else "🔵")

        big_road_str = " ".join(recent_results[-15:])

        analysis = self.get_advanced_road_prediction()

        if analysis:
            patterns_str = "\n".join([f"  • {p}" for p in analysis["patterns_detected"]])

            msg = f"""
📊 <b>ANÁLISIS DE ROADS</b>

🛣️ Big Road (últimos 15):
{big_road_str}

🎯 Patrones detectados:
{patterns_str}

💡 Predicción Roads: <b>{analysis["predicted"]}</b>
💪 Confianza: {analysis["confidence"]:.0f}%
🗳️ Votos: 🔴{analysis["votes"]["Banker"]} vs 🔵{analysis["votes"]["Player"]}
"""
        else:
            msg = f"""
📊 <b>ANÁLISIS DE ROADS</b>

🛣️ Big Road (últimos 15):
{big_road_str}

⏳ Esperando más datos para análisis...
"""

        return msg
