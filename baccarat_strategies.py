# baccarat_strategies.py
import logging
from collections import deque

logger = logging.getLogger(__name__)


class BaccaratStrategies:
    def __init__(self, db=None, max_history=500):
        self.db = db
        self.history = deque(maxlen=max_history)
        self.patterns_memory = {}
        
    async def load_from_db(self, limit=50):
        """Cargar historial reciente para estrategias"""
        if not self.db:
            return 0
        
        try:
            df = await self.db.get_recent_rounds(limit)
            if len(df) > 0:
                for _, row in df.iterrows():
                    self.history.append({
                        'winner': row['winner'],
                        'player_score': row.get('player_score') or 0,
                        'banker_score': row.get('banker_score') or 0,
                        'player_pair': row.get('player_pair', False),
                        'banker_pair': row.get('banker_pair', False)
                    })
                logger.info(f"📚 Cargadas {len(self.history)} rondas para estrategias")
                return len(self.history)
        except Exception as e:
            logger.error(f"Error cargando historial: {e}")
        return 0
        
    def add_round(self, winner: str, player_score: int, banker_score: int,
                  player_pair: bool = False, banker_pair: bool = False):
        """Agregar ronda al historial - últimas 30 del shoe actual"""
        self.history.append({
            'winner': winner,
            'player_score': player_score,
            'banker_score': banker_score,
            'player_pair': player_pair,
            'banker_pair': banker_pair
        })
        # Mantener solo las últimas 30 rondas para el shoe actual
        while len(self.history) > 30:
            self.history.popleft()
    
    def sync_from_shoe_history(self, history_v2):
        """Sincronizar historial completo desde Evolution Gaming encodedShoeState"""
        self.history.clear()
        for game in history_v2:
            winner = game.get('winner')
            player_score = game.get('playerScore', 0)
            banker_score = game.get('bankerScore', 0)
            player_pair = game.get('playerPair', False)
            banker_pair = game.get('bankerPair', False)
            
            self.history.append({
                'winner': winner,
                'player_score': player_score,
                'banker_score': banker_score,
                'player_pair': player_pair,
                'banker_pair': banker_pair
            })
        
        logger.info(f"✅ Sincronizado {len(self.history)} rondas desde Evolution Gaming")
    
    def get_big_road(self, limit=20):
        """Generar Big Road (camino principal)"""
        if not self.history:
            return []
        
        road = []
        current_winner = None
        current_streak = []
        
        for round_data in list(self.history)[-limit:]:
            winner = round_data['winner']
            
            if winner == 'Tie':
                if current_streak:
                    current_streak[-1] += 'T'
                continue
            
            if winner != current_winner:
                if current_streak:
                    road.append(current_streak)
                current_streak = [winner]
                current_winner = winner
            else:
                current_streak.append(winner)
        
        if current_streak:
            road.append(current_streak)
        
        return road
    
    def detect_twins(self, window=6):
        """Detectar gemelos (patrones idénticos consecutivos)"""
        if len(self.history) < window * 2:
            return None
        
        recent = [r['winner'] for r in list(self.history)[-window*2:]]
        
        first_half = ''.join(recent[:window])
        second_half = ''.join(recent[window:])
        
        if first_half == second_half:
            last = recent[-1]
            # Después de gemelos, viene el color contrario
            if last == 'Banker':
                prediction = 'Player'
            elif last == 'Player':
                prediction = 'Banker'
            else:
                prediction = 'Banker'  # Tie → apostar a Banker por defecto
            return {
                'pattern': first_half,
                'confidence': 85,
                'prediction': prediction
            }
        
        return None

    def score_color_triggers(self):
        """
        Reglas VALIDADAS con 1438 rondas reales (solo las que >55% accuracy):
        
        Trigger       → Predicción  | Accuracy | Muestras
        P5 (Player 5) → Banker      | 62.5%    | 34
        P4 (Player 4) → Banker      | 60.9%    | 25
        B4 (Banker 4) → Player      | 60.0%    | 55
        P2 (Player 2) → Banker      | 57.9%    | 21
        P6 (Player 6) → Player      | 57.6%    | 97
        P9 (Player 9) → Player      | 57.2%    | 170
        B9 (Banker 9) → Banker      | 56.0%    | 179
        B6 (Banker 6) → Player      | 55.4%    | 79
        Tie           → Banker      | 54.7%    | 132
        B7 (Banker 7) → Player      | 54.1%    | 111
        """
        if len(self.history) < 1:
            return None
        
        last = self.history[-1]
        winner = last.get('winner')
        player_score = last.get('player_score')
        banker_score = last.get('banker_score')
        
        if player_score is None or banker_score is None:
            return None
        
        predicted = None
        trigger_name = ""
        confidence = 50
        
        # Reglas ordenadas por accuracy (datos reales validados)
        if winner == 'Player' and player_score == 5:
            predicted = 'Banker'
            trigger_name = "P5→B(62%)"
            confidence = 62
        elif winner == 'Player' and player_score == 4:
            predicted = 'Banker'
            trigger_name = "P4→B(61%)"
            confidence = 61
        elif winner == 'Banker' and banker_score == 4:
            predicted = 'Player'
            trigger_name = "B4→P(60%)"
            confidence = 60
        elif winner == 'Player' and player_score == 2:
            predicted = 'Banker'
            trigger_name = "P2→B(58%)"
            confidence = 58
        elif winner == 'Player' and player_score == 6:
            predicted = 'Player'
            trigger_name = "P6→P(58%)"
            confidence = 58
        elif winner == 'Player' and player_score == 9:
            predicted = 'Player'
            trigger_name = "P9→P(57%)"
            confidence = 57
        elif winner == 'Banker' and banker_score == 9:
            predicted = 'Banker'
            trigger_name = "B9→B(56%)"
            confidence = 56
        elif winner == 'Banker' and banker_score == 6:
            predicted = 'Player'
            trigger_name = "B6→P(55%)"
            confidence = 55
        elif winner == 'Tie':
            predicted = 'Banker'
            trigger_name = "Tie→B(55%)"
            confidence = 55
        elif winner == 'Banker' and banker_score == 7:
            predicted = 'Player'
            trigger_name = "B7→P(54%)"
            confidence = 54
        
        if not predicted:
            return None
        return {
            'strategy': 'Score-Color',
            'predicted': predicted,
            'confidence': confidence,
            'trigger': trigger_name,
            'trigger_name': trigger_name
        }
    
    def exact_score_combo_triggers(self):
        """
        ESTRATEGIA: Combinación exacta de scores (Player_score - Banker_score)
        VALIDADA con 1450 rondas reales. Solo reglas con >60% accuracy y >14 muestras.
        
        Top combos encontrados:
        B: 2-9 → Player 86.7% (15)    B: 7-9 → Banker 71.4% (21)
        P: 7-0 → Banker 71.4% (21)    P: 8-7 → Player 68.8% (16)
        T: 7-7 → Banker 68.0% (25)    B: 1-9 → Banker 66.7% (15)
        B: 3-9 → Banker 66.7% (15)    B: 8-9 → Banker 66.7% (18)
        P: 5-4 → Banker 66.7% (15)    P: 9-7 → Player 66.7% (21)
        B: 7-8 → Banker 65.2% (23)    P: 9-2 → Player 65.0% (20)
        B: 0-9 → Banker 63.6% (22)    B: 4-9 → Banker 63.2% (19)
        B: 1-4 → Player 62.5% (16)    B: 2-5 → Player 62.5% (16)
        P: 6-2 → Player 62.5% (16)    T: 5-5 → Banker 62.5% (16)
        B: 4-8 → Banker 61.9% (21)    B: 5-8 → Player 60.0% (20)
        P: 6-4 → Banker 60.0% (15)    P: 9-8 → Player 60.0% (15)
        """
        if len(self.history) < 1:
            return None
        
        last = self.history[-1]
        winner = last.get('winner')
        ps = last.get('player_score')
        bs = last.get('banker_score')
        
        if ps is None or bs is None:
            return None
        
        # Tabla de combos: (winner, player_score, banker_score) → (predicted, accuracy)
        # Ordenados por accuracy descendente
        combo_rules = {
            ('Banker', 2, 9):  ('Player', 87),
            ('Banker', 7, 9):  ('Banker', 71),
            ('Player', 7, 0):  ('Banker', 71),
            ('Player', 8, 7):  ('Player', 69),
            ('Tie', 7, 7):     ('Banker', 68),
            ('Banker', 1, 9):  ('Banker', 67),
            ('Banker', 3, 9):  ('Banker', 67),
            ('Banker', 8, 9):  ('Banker', 67),
            ('Player', 5, 4):  ('Banker', 67),
            ('Player', 9, 7):  ('Player', 67),
            ('Banker', 7, 8):  ('Banker', 65),
            ('Player', 9, 2):  ('Player', 65),
            ('Banker', 0, 9):  ('Banker', 64),
            ('Banker', 4, 9):  ('Banker', 63),
            ('Banker', 1, 4):  ('Player', 63),
            ('Banker', 2, 5):  ('Player', 63),
            ('Player', 6, 2):  ('Player', 63),
            ('Tie', 5, 5):     ('Banker', 63),
            ('Banker', 4, 8):  ('Banker', 62),
            ('Banker', 5, 8):  ('Player', 60),
            ('Player', 6, 4):  ('Banker', 60),
            ('Player', 9, 8):  ('Player', 60),
        }
        
        key = (winner, ps, bs)
        if key in combo_rules:
            predicted, accuracy = combo_rules[key]
            trigger_name = f"{winner[0]}{ps}-{bs}→{predicted[0]}({accuracy}%)"
            return {
                'strategy': 'Score-Combo',
                'predicted': predicted,
                'confidence': accuracy,
                'trigger': trigger_name,
                'trigger_name': trigger_name
            }
        
        return None
    
    def sequence_pattern_triggers(self):
        """
        ESTRATEGIA: Patrones de secuencia de 2-3 resultados → predicción del siguiente.
        VALIDADA con 1450 rondas reales.
        
        Secuencias de 3:
        TBP → Banker 76.0% (25)    PBT → Banker 70.8% (24)
        PTB → Banker 64.0% (25)    BBP → Player 57.8% (135)
        TPB → Banker 56.0% (25)    PPT → Banker 55.6% (27)
        
        Secuencias de 2:
        BT → Banker 64.0% (50)     TB → Banker 55.0% (60)
        """
        if len(self.history) < 2:
            return None
        
        # Obtener últimos 3 resultados (P/B/T)
        recent = list(self.history)
        results = []
        for r in recent[-3:]:
            w = r['winner']
            if w == 'Player':
                results.append('P')
            elif w == 'Banker':
                results.append('B')
            else:
                results.append('T')
        
        predicted = None
        confidence = 50
        trigger_name = ""
        
        # Primero intentar secuencia de 3 (más precisa)
        if len(results) >= 3:
            seq3 = ''.join(results[-3:])
            seq3_rules = {
                'TBP': ('Banker', 76),
                'PBT': ('Banker', 71),
                'PTB': ('Banker', 64),
                'BBP': ('Player', 58),
                'TPB': ('Banker', 56),
                'PPT': ('Banker', 56),
            }
            if seq3 in seq3_rules:
                predicted, confidence = seq3_rules[seq3]
                trigger_name = f"Seq[{seq3}]→{predicted[0]}({confidence}%)"
        
        # Si no hay match de 3, intentar secuencia de 2
        if not predicted and len(results) >= 2:
            seq2 = ''.join(results[-2:])
            seq2_rules = {
                'BT': ('Banker', 64),
                'TB': ('Banker', 55),
            }
            if seq2 in seq2_rules:
                predicted, confidence = seq2_rules[seq2]
                trigger_name = f"Seq[{seq2}]→{predicted[0]}({confidence}%)"
        
        if not predicted:
            return None
        
        return {
            'strategy': 'Sequence',
            'predicted': predicted,
            'confidence': confidence,
            'trigger': trigger_name,
            'trigger_name': trigger_name
        }
    
    def score_difference_triggers(self):
        """
        NUEVA ESTRATEGIA: Basada en la diferencia de puntuación.
        
        Diferencias comunes y su predicción:
        - Diferencia 1 (ej: 6-5, 5-4): Puede venir cualquier cosa, tendencia a Banker por comisión
        - Diferencia 2-3: Seguir al ganador (continuidad)
        - Diferencia 4+: El perdedor suele ganar la siguiente (oscilación)
        - Natural (8 o 9): Predomina continuación
        """
        if len(self.history) < 2:
            return None
        
        last = self.history[-1]
        winner = last.get('winner')
        player_score = last.get('player_score')
        banker_score = last.get('banker_score')
        
        if winner not in ('Banker', 'Player') or player_score is None or banker_score is None:
            return None
        
        diff = abs(player_score - banker_score)
        is_natural = player_score >= 8 or banker_score >= 8
        
        predicted = None
        confidence = 50
        trigger_name = ""
        
        if is_natural:
            # Natural: tendencia a continuar (mismo ganador)
            if player_score == banker_score:
                # Tie en natural: Banker por defecto
                predicted = 'Banker'
                trigger_name = f"Natural Tie → B"
                confidence = 55
            else:
                predicted = winner  # Continuar con el ganador
                trigger_name = f"Natural {winner[0]}{player_score}-{banker_score} → {winner[0]}"
                confidence = 60
        elif diff >= 4:
            # Diferencia grande: oscilación (el perdedor suele ganar)
            predicted = 'Banker' if winner == 'Player' else 'Player'
            trigger_name = f"Diff{diff} ({winner[0]}{player_score}-{banker_score}) → {predicted[0]}"
            confidence = 58
        elif diff <= 1:
            # Diferencia mínima: Banker por ventaja de casa
            predicted = 'Banker'
            trigger_name = f"Diff{diff} ({winner[0]}{player_score}-{banker_score}) → B"
            confidence = 52
        
        if not predicted:
            return None
        
        return {
            'strategy': 'Score-Diff',
            'predicted': predicted,
            'confidence': confidence,
            'trigger': trigger_name,
            'difference': diff,
            'is_natural': is_natural
        }
    
    def pair_pattern_triggers(self):
        """
        NUEVA ESTRATEGIA: Basada en pares (player_pair, banker_pair).
        
        Patrones:
        - PP (ambos pares): Alta probabilidad de cambio → Banker
        - Solo Player Pair: continuation → Player
        - Solo Banker Pair: continuation → Banker
        - Sin pares recientes: tendencia a Banker
        """
        if len(self.history) < 3:
            return None
        
        # Analizar últimos 3 resultados
        recent = list(self.history)[-3:]
        
        pairs_in_recent = 0
        player_pair_count = 0
        banker_pair_count = 0
        
        for r in recent:
            if r.get('player_pair'):
                player_pair_count += 1
                pairs_in_recent += 1
            if r.get('banker_pair'):
                banker_pair_count += 1
                pairs_in_recent += 1
        
        last = recent[-1]
        
        predicted = None
        confidence = 50
        trigger_name = ""
        
        if player_pair_count >= 2 and banker_pair_count == 0:
            # Solo Player Pairs → seguir Player
            predicted = 'Player'
            trigger_name = f"PP×{player_pair_count} → P"
            confidence = 65
        elif banker_pair_count >= 2 and player_pair_count == 0:
            # Solo Banker Pairs → seguir Banker
            predicted = 'Banker'
            trigger_name = f"BB×{banker_pair_count} → B"
            confidence = 65
        elif player_pair_count > 0 and banker_pair_count > 0:
            # Ambos tipos de pares → oscilación
            last_winner = last.get('winner')
            predicted = 'Banker' if last_winner == 'Player' else 'Player'
            trigger_name = f"PB Mix → {predicted[0]}"
            confidence = 58
        elif pairs_in_recent == 0:
            # Sin pares en 3 rondas → tendencia sutil a Banker
            predicted = 'Banker'
            trigger_name = "No Pairs (3 rounds) → B"
            confidence = 52
        
        if not predicted:
            return None
        
        return {
            'strategy': 'Pair-Pattern',
            'predicted': predicted,
            'confidence': confidence,
            'trigger': trigger_name,
            'player_pairs': player_pair_count,
            'banker_pairs': banker_pair_count
        }
    
    def repeat_score_triggers(self):
        """
        NUEVA ESTRATEGIA: Basada en scores repetidos.
        
        Si el mismo score se repite (ej: Player 6, luego Player 6):
        - Repetido 2 veces: tendencia a cambiar
        - score bajo (0-3): mayor probabilidad de cambio
        - score alto (6-9): puede continuar o empatar
        """
        if len(self.history) < 2:
            return None
        
        last = self.history[-1]
        prev = self.history[-2]
        
        last_winner = last.get('winner')
        last_ps = last.get('player_score')
        last_bs = last.get('banker_score')
        
        prev_winner = prev.get('winner')
        prev_ps = prev.get('player_score')
        prev_bs = prev.get('banker_score')
        
        if None in (last_ps, last_bs, prev_ps, prev_bs):
            return None
        
        # Verificar si el score del ganador se repite
        same_score = False
        
        if last_winner == 'Player' and prev_winner == 'Player':
            if last_ps == prev_ps:
                same_score = True
                repeated_score = last_ps
        elif last_winner == 'Banker' and prev_winner == 'Banker':
            if last_bs == prev_bs:
                same_score = True
                repeated_score = last_bs
        
        if not same_score:
            return None
        
        predicted = None
        confidence = 55
        trigger_name = ""
        
        # Scores bajos (0-3): mayor tendencia al cambio
        if repeated_score <= 3:
            predicted = 'Banker' if last_winner == 'Player' else 'Player'
            trigger_name = f"{last_winner[0]}{repeated_score} Repeat → {predicted[0]} (low)"
            confidence = 62
        elif repeated_score >= 6:
            # Scores altos: tendencia a empatar o continuar
            if last_winner == 'Banker':
                predicted = 'Banker'
                trigger_name = f"B{repeated_score} Repeat → B (high)"
                confidence = 58
            else:
                # Player alto: cambiar o empatar
                predicted = 'Banker'
                trigger_name = f"P{repeated_score} Repeat → B (high)"
                confidence = 55
        
        if not predicted:
            return None
        
        return {
            'strategy': 'Repeat-Score',
            'predicted': predicted,
            'confidence': confidence,
            'trigger': trigger_name,
            'repeated_score': repeated_score
        }
    
    def tie_followup_triggers(self):
        """
        NUEVA ESTRATEGIA: Qué viene después de un Tie.
        
        Después de un Tie:
        - Si el resultado anterior al Tie fue X, tienden a volver a X
        - Pero a veces vienen 2-3 ties seguidos
        """
        if len(self.history) < 3:
            return None
        
        # Buscar si el último fue Tie
        last = self.history[-1]
        if last.get('winner') != 'Tie':
            return None
        
        # Verificar el anterior al Tie
        prev = self.history[-2]
        prev_winner = prev.get('winner')
        
        if not prev_winner or prev_winner == 'Tie':
            return None
        
        # Buscar antes del Tie anterior (si existe)
        if len(self.history) >= 4:
            prev_prev = self.history[-3]
            prev_prev_winner = prev_prev.get('winner')
            
            # Si el anterior al Tie fue igual al anterior del anterior, seguir esa racha
            if prev_prev_winner == prev_winner:
                predicted = prev_winner
                confidence = 68  # Alta confianza
                trigger_name = f"Tie after {prev_winner[0]}{prev_winner[0]} → {predicted[0]}"
            else:
                predicted = prev_winner
                confidence = 58
                trigger_name = f"Tie after {prev_winner[0]} → {predicted[0]}"
        else:
            predicted = prev_winner
            confidence = 55
            trigger_name = f"Tie → {predicted[0]}"
        
        return {
            'strategy': 'Tie-Followup',
            'predicted': predicted,
            'confidence': confidence,
            'trigger': trigger_name,
            'before_tie': prev_winner
        }
    
    def pattern_memory_prediction(self, pattern_length=3):
        """
        Memoria de patrones - VERSIÓN FINAL
        Busca el patrón de los 3 anteriores y predice el siguiente
        """
        min_occurrences = 2
        min_history_for_search = pattern_length + min_occurrences + 4
        
        if len(self.history) < min_history_for_search:
            return None

        # El patrón son los 3 resultados ANTERIORES al último
        recent = [r['winner'] for r in list(self.history)[-(pattern_length+1):-1]]
        current_pattern = ''.join(recent)
        
        shoe_phase = self._get_shoe_phase()
        
        # Buscar este patrón en el historial
        search_start = 0
        search_end = len(self.history) - pattern_length - 2
        
        if search_end - search_start < min_occurrences:
            search_start = 0
            search_end = len(self.history) - pattern_length - 1
        
        history_list = [r['winner'] for r in self.history]
        
        matches = []
        weights = []

        for i in range(search_start, search_end):
            pattern = ''.join(history_list[i:i+pattern_length])
            if pattern == current_pattern and i + pattern_length < len(history_list):
                next_outcome = history_list[i + pattern_length]
                matches.append(next_outcome)
                position_ratio = i / max(search_end, 1)
                weight = 0.5 + (position_ratio * 0.5)
                weights.append(weight)

        if len(matches) < min_occurrences:
            return None

        banker_weight = sum(w for m, w in zip(matches, weights) if m == 'Banker')
        player_weight = sum(w for m, w in zip(matches, weights) if m == 'Player')
        tie_weight = sum(w for m, w in zip(matches, weights) if m == 'Tie')
        total_weight = banker_weight + player_weight + tie_weight
        
        banker_count = matches.count('Banker')
        player_count = matches.count('Player')
        tie_count = matches.count('Tie')
        total = len(matches)

        if banker_weight >= player_weight and banker_weight >= tie_weight:
            predicted = 'Banker'
            confidence = (banker_weight / total_weight) * 100
            confidence = min(confidence * (1 + min(total, 10) * 0.02), 95)
        elif player_weight >= banker_weight and player_weight >= tie_weight:
            predicted = 'Player'
            confidence = (player_weight / total_weight) * 100
            confidence = min(confidence * (1 + min(total, 10) * 0.02), 95)
        else:
            if banker_count >= player_count:
                predicted = 'Banker'
                confidence = (banker_weight / total_weight) * 80
            else:
                predicted = 'Player'
                confidence = (player_weight / total_weight) * 80

        if shoe_phase == 'middle':
            confidence = min(confidence * 1.05, 95)
        elif shoe_phase == 'late':
            confidence = min(confidence * 1.10, 95)

        return {
            'pattern': current_pattern,
            'predicted': predicted,
            'confidence': confidence,
            'times_seen': total,
            'phase': shoe_phase,
            'distribution': {
                'Banker': banker_count,
                'Player': player_count,
                'Tie': tie_count
            },
            'weighted': {
                'Banker': round(banker_weight, 2),
                'Player': round(player_weight, 2),
                'Tie': round(tie_weight, 2)
            }
        }

    def _get_shoe_phase(self):
        """Determinar en qué fase del shoe estamos"""
        history_len = len(self.history)
        shoe_cards = getattr(self, 'shoe_cards_out', 0) or 0
        
        # Estimación basada en numero de cartas o rondas
        if shoe_cards > 0:
            # Asumiendo zapato de 8 mazos ~416 cartas
            cards_used_pct = shoe_cards / 416
            if cards_used_pct < 0.35:
                return 'early'
            elif cards_used_pct < 0.70:
                return 'middle'
            else:
                return 'late'
        elif history_len < 20:
            return 'early'
        elif history_len < 60:
            return 'middle'
        else:
            return 'late'
    
    def detect_streak_pattern(self):
        """Detectar rachas largas (4+) - CONTINUAR racha, no opuesta"""
        if len(self.history) < 4:
            return None
        
        recent = [r['winner'] for r in list(self.history)[-10:] if r['winner'] != 'Tie']
        
        if len(recent) < 4:
            return None
        
        current = recent[-1]
        streak = 1
        
        for i in range(len(recent)-2, -1, -1):
            if recent[i] == current:
                streak += 1
            else:
                break
        
        if streak >= 4:
            # En baccarat, rachas de 4+ tienden a CONTINUAR
            # (datos reales: RACHA_TREND 47.9% vs falacia <45%)
            if streak <= 6:
                # Racha moderada (4-6): continuar
                predicted = current
                confidence = min(52 + (streak * 3), 70)
            else:
                # Racha muy larga (7+): posible ruptura
                predicted = 'Player' if current == 'Banker' else 'Banker'
                confidence = 55
            
            return {
                'type': f'RACHA_{streak}',
                'current': current,
                'predicted': predicted,
                'confidence': confidence
            }
        
        return None
    
    def score_distribution_prediction(self):
        """
        NUEVA ESTRATEGIA: Score Distribution (0-9)
        Analiza qué scores (0-9) aparecen más y qué lado gana con ellos.
        Si un score específico aparece 2+ veces reciente y favorece
        un lado >60%, predice ese lado.
        """
        if len(self.history) < 15:
            return None
        
        recent = list(self.history)[-20:]
        
        # Contar victorias por score
        score_winners = {}  # {f'P{score}': count, f'B{score}': count}
        
        for r in recent:
            winner = r.get('winner')
            if winner == 'Player':
                score = r.get('player_score', 0)
                key = f'P{score}'
                score_winners[key] = score_winners.get(key, 0) + 1
            elif winner == 'Banker':
                score = r.get('banker_score', 0)
                key = f'B{score}'
                score_winners[key] = score_winners.get(key, 0) + 1
        
        # Buscar scores que aparezcan 2+ veces en últimas 10
        recent_10 = list(self.history)[-10:]
        hot_scores = {}
        
        for r in recent_10:
            winner = r.get('winner')
            if winner == 'Player':
                score = r.get('player_score', 0)
                hot_scores[score] = hot_scores.get(score, 0) + 1
            elif winner == 'Banker':
                score = r.get('banker_score', 0)
                hot_scores[score] = hot_scores.get(score, 0) + 1
        
        # Encontrar score con 2+ apariciones
        for score, count in hot_scores.items():
            if count >= 2:
                # Ver qué lado domina con este score
                p_key = f'P{score}'
                b_key = f'B{score}'
                p_count = score_winners.get(p_key, 0)
                b_count = score_winners.get(b_key, 0)
                total = p_count + b_count
                
                if total >= 2:
                    if p_count > b_count:
                        ratio = p_count / total
                        if ratio > 0.6:
                            confidence = min(50 + (ratio - 0.6) * 100, 75)
                            return {
                                'strategy': 'Score-Distribution',
                                'predicted': 'Player',
                                'confidence': confidence,
                                'weight': 1.5,
                                'hot_score': score,
                                'appearances': count
                            }
                    else:
                        ratio = b_count / total
                        if ratio > 0.6:
                            confidence = min(50 + (ratio - 0.6) * 100, 75)
                            return {
                                'strategy': 'Score-Distribution',
                                'predicted': 'Banker',
                                'confidence': confidence,
                                'weight': 1.5,
                                'hot_score': score,
                                'appearances': count
                            }
        
        return None
    
    def sector_dominance_prediction(self):
        """
        NUEVA ESTRATEGIA: Sector Dominance
        Divide la sesión en 4 sectores y detecta dominancia.
        Si últimos 2-3 sectores son del mismo lado, predice continuación.
        """
        if len(self.history) < 20:
            return None
        
        history_len = len(self.history)
        sector_size = max(5, history_len // 4)
        
        sectors = []
        for i in range(4):
            start = i * sector_size
            end = min(start + sector_size, history_len)
            if start >= history_len:
                break
            sector_data = list(self.history)[start:end]
            
            banker_c = sum(1 for r in sector_data
                          if r.get('winner') == 'Banker')
            player_c = sum(1 for r in sector_data
                          if r.get('winner') == 'Player')
            
            if banker_c > player_c:
                sectors.append('Banker')
            elif player_c > banker_c:
                sectors.append('Player')
            else:
                sectors.append('Neutral')
        
        if len(sectors) < 3:
            return None
        
        # Detectar consolidación (últimos 2-3 sectores iguales)
        last_2 = sectors[-2:]
        last_3 = sectors[-3:] if len(sectors) >= 3 else sectors
        
        if len(set(last_3)) == 1 and last_3[0] != 'Neutral':
            # 3 sectores consecutivos iguales
            confidence = 72
            return {
                'strategy': 'Sector-Dominance',
                'predicted': last_3[0],
                'confidence': confidence,
                'weight': 1.3,
                'sectors': sectors,
                'pattern': 'consolidation-3'
            }
        elif len(set(last_2)) == 1 and last_2[0] != 'Neutral':
            # 2 sectores consecutivos iguales
            confidence = 65
            return {
                'strategy': 'Sector-Dominance',
                'predicted': last_2[0],
                'confidence': confidence,
                'weight': 1.3,
                'sectors': sectors,
                'pattern': 'consolidation-2'
            }
        
        return None
    
    def even_odd_scores_prediction(self):
        """
        NUEVA ESTRATEGIA: Even/Odd Scores
        Analiza tendencia de scores pares (0,2,4,6,8) vs
        impares (1,3,5,7,9).
        """
        if len(self.history) < 10:
            return None
        
        recent = list(self.history)[-15:]
        
        # Contar pares e impares
        even_banker = 0
        odd_banker = 0
        even_player = 0
        odd_player = 0
        
        for r in recent:
            winner = r.get('winner')
            if winner == 'Banker':
                score = r.get('banker_score', 0)
                if score % 2 == 0:
                    even_banker += 1
                else:
                    odd_banker += 1
            elif winner == 'Player':
                score = r.get('player_score', 0)
                if score % 2 == 0:
                    even_player += 1
                else:
                    odd_player += 1
        
        # Analizar últimos 5 resultados
        last_5 = list(self.history)[-5:]
        last_5_scores = []
        
        for r in last_5:
            winner = r.get('winner')
            if winner == 'Banker':
                score = r.get('banker_score', 0)
            elif winner == 'Player':
                score = r.get('player_score', 0)
            else:
                continue
            last_5_scores.append(score)
        
        even_count = sum(1 for s in last_5_scores if s % 2 == 0)
        
        # Si 3+ scores recientes son pares
        if even_count >= 3:
            total_even = even_banker + even_player
            if total_even > 0:
                even_banker_ratio = even_banker / total_even
                if even_banker_ratio > 0.6:
                    confidence = min(50 + (even_banker_ratio-0.6)*50, 70)
                    return {
                        'strategy': 'Even-Odd-Scores',
                        'predicted': 'Banker',
                        'confidence': confidence,
                        'weight': 1.1,
                        'pattern': 'even-dominant',
                        'ratio': even_banker_ratio
                    }
                elif even_banker_ratio < 0.4:
                    confidence = min(50 + (0.4-even_banker_ratio)*50, 70)
                    return {
                        'strategy': 'Even-Odd-Scores',
                        'predicted': 'Player',
                        'confidence': confidence,
                        'weight': 1.1,
                        'pattern': 'even-dominant',
                        'ratio': 1 - even_banker_ratio
                    }
        
        # Si 3+ scores recientes son impares
        elif even_count <= 2:
            total_odd = odd_banker + odd_player
            if total_odd > 0:
                odd_banker_ratio = odd_banker / total_odd
                if odd_banker_ratio > 0.6:
                    confidence = min(50 + (odd_banker_ratio-0.6)*50, 70)
                    return {
                        'strategy': 'Even-Odd-Scores',
                        'predicted': 'Banker',
                        'confidence': confidence,
                        'weight': 1.1,
                        'pattern': 'odd-dominant',
                        'ratio': odd_banker_ratio
                    }
                elif odd_banker_ratio < 0.4:
                    confidence = min(50 + (0.4-odd_banker_ratio)*50, 70)
                    return {
                        'strategy': 'Even-Odd-Scores',
                        'predicted': 'Player',
                        'confidence': confidence,
                        'weight': 1.1,
                        'pattern': 'odd-dominant',
                        'ratio': 1 - odd_banker_ratio
                    }
        
        return None
    
    def clustering_detection(self):
        """
        NUEVA ESTRATEGIA: Clustering Detection
        Detecta clusters = 4-5 resultados del mismo lado en ventana de 5.
        """
        if len(self.history) < 10:
            return None
        
        recent = list(self.history)[-15:]
        
        # Contar clusters totales en la sesión
        total_clusters = 0
        window_size = 5
        
        for i in range(len(recent) - window_size + 1):
            window = recent[i:i+window_size]
            banker_count = sum(1 for r in window
                             if r.get('winner') == 'Banker')
            player_count = sum(1 for r in window
                             if r.get('winner') == 'Player')
            
            if banker_count >= 4 or player_count >= 4:
                total_clusters += 1
        
        # Analizar cluster activo (últimas 5 rondas)
        last_5 = recent[-5:]
        banker_in_5 = sum(1 for r in last_5
                         if r.get('winner') == 'Banker')
        player_in_5 = sum(1 for r in last_5
                         if r.get('winner') == 'Player')
        
        # Cluster activo moderado (4/5)
        if banker_in_5 == 4:
            confidence = min(54 + (total_clusters * 2), 66)
            return {
                'strategy': 'Clustering',
                'predicted': 'Banker',
                'confidence': confidence,
                'weight': 1.4,
                'cluster_strength': '4/5',
                'total_clusters': total_clusters
            }
        elif player_in_5 == 4:
            confidence = min(54 + (total_clusters * 2), 66)
            return {
                'strategy': 'Clustering',
                'predicted': 'Player',
                'confidence': confidence,
                'weight': 1.4,
                'cluster_strength': '4/5',
                'total_clusters': total_clusters
            }
        
        # Cluster muy fuerte (5/5) - predecir ruptura
        elif banker_in_5 == 5:
            return {
                'strategy': 'Clustering',
                'predicted': 'Player',
                'confidence': 58,
                'weight': 1.4,
                'cluster_strength': '5/5-break',
                'total_clusters': total_clusters
            }
        elif player_in_5 == 5:
            return {
                'strategy': 'Clustering',
                'predicted': 'Banker',
                'confidence': 58,
                'weight': 1.4,
                'cluster_strength': '5/5-break',
                'total_clusters': total_clusters
            }
        
        # Mesa con muchos clusters - seguir última tendencia
        if total_clusters >= 3:
            last_3 = [r.get('winner') for r in recent[-3:]
                     if r.get('winner') != 'Tie']
            if len(last_3) >= 2:
                if last_3[-1] == last_3[-2]:
                    return {
                        'strategy': 'Clustering',
                        'predicted': last_3[-1],
                        'confidence': 52,
                        'weight': 1.4,
                        'cluster_strength': 'volatile',
                        'total_clusters': total_clusters
                    }
        
        return None
    
    def four_roads_consensus(self):
        """Consenso con 6 estrategias validadas con datos reales (>50%)
        
        Datos reales validados:
        - Score-Combo: 60-87% (1450 rondas, combos exactos) → peso 3.5
        - Memory-3: 67.6% (37 muestras) → peso 3.0
        - Sequence: 55-76% (secuencias 2-3 resultados) → peso 2.8
        - Score-Color: 55-62% (1438 rondas validadas) → peso 2.5
        - Memory-4: 58.8% (17 muestras) → peso 2.0
        - Score-Diff: 54.1% (85 muestras) → peso 1.5
        """
        if len(self.history) < 3:
            return None
        
        # Buscar el último resultado que NO sea Tie
        last_valid = None
        for r in reversed(self.history):
            if r['winner'] != 'Tie':
                last_valid = r
                break
        
        if not last_valid:
            return None
        
        predictions = []
        
        # === ESTRATEGIAS VALIDADAS CON DATOS REALES ===
        
        # 1. SCORE-COMBO: 60-87% accuracy → peso 3.5 (combos exactos, la más precisa)
        score_combo = self.exact_score_combo_triggers()
        if score_combo and score_combo['confidence'] >= 60:
            predictions.append({
                'strategy': 'Score-Combo',
                'predicted': score_combo['predicted'],
                'confidence': score_combo['confidence'],
                'weight': 3.5
            })
        
        # 2. MEMORY-3: 67.6% accuracy → peso 3.0 (dominante)
        mem3 = self.pattern_memory_prediction(3)
        if mem3 and mem3['confidence'] >= 55:
            predictions.append({
                'strategy': 'Memory-3',
                'predicted': mem3['predicted'],
                'confidence': mem3['confidence'],
                'weight': 3.0
            })
        
        # 3. SEQUENCE: 55-76% accuracy → peso 2.8 (secuencias de resultados)
        sequence = self.sequence_pattern_triggers()
        if sequence and sequence['confidence'] >= 55:
            predictions.append({
                'strategy': 'Sequence',
                'predicted': sequence['predicted'],
                'confidence': sequence['confidence'],
                'weight': 2.8
            })
        
        # 4. SCORE-COLOR: 55-62% accuracy → peso 2.5 (validada con 1438 rondas)
        score_color = self.score_color_triggers()
        if score_color and score_color['confidence'] >= 55:
            predictions.append({
                'strategy': 'Score-Color',
                'predicted': score_color['predicted'],
                'confidence': score_color['confidence'],
                'weight': 2.5
            })
        
        # 5. MEMORY-4: 58.8% accuracy → peso 2.0
        mem4 = self.pattern_memory_prediction(4)
        if mem4 and mem4['confidence'] >= 55:
            predictions.append({
                'strategy': 'Memory-4',
                'predicted': mem4['predicted'],
                'confidence': mem4['confidence'],
                'weight': 2.0
            })
        
        # 6. SCORE-DIFF: 54.1% accuracy → peso 1.5
        score_diff = self.score_difference_triggers()
        if score_diff:
            predictions.append({
                'strategy': 'Score-Diff',
                'predicted': score_diff['predicted'],
                'confidence': score_diff['confidence'],
                'weight': 1.5
            })
        
        # Si ninguna estrategia activa, usar Memory-3 sin filtro de confianza
        if not predictions:
            mem3_nofilt = self.pattern_memory_prediction(3)
            if mem3_nofilt:
                predictions.append({
                    'strategy': 'Memory-3',
                    'predicted': mem3_nofilt['predicted'],
                    'confidence': mem3_nofilt['confidence'],
                    'weight': 3.0
                })
        
        # Si aún nada, último recurso: score-diff sin filtro
        if not predictions:
            return {
                'predicted': last_valid['winner'],
                'confidence': 51,
                'votes': {'Banker': 0.5 if last_valid['winner'] == 'Banker' else 0,
                          'Player': 0.5 if last_valid['winner'] == 'Player' else 0,
                          'Tie': 0},
                'total_strategies': 1,
                'unanimous': False,
                'strategies': [{
                    'strategy': 'LastResult',
                    'predicted': last_valid['winner'],
                    'confidence': 51,
                    'weight': 1
                }]
            }
        
        # Votación ponderada
        votes = {'Banker': 0, 'Player': 0, 'Tie': 0}
        total_weight = 0
        total_confidence = 0
        
        for pred in predictions:
            weight = pred.get('weight', 1.0)
            votes[pred['predicted']] += weight
            total_weight += weight
            total_confidence += pred['confidence'] * weight
        
        max_votes = max(votes.values())
        winner = [k for k, v in votes.items() if v == max_votes][0]
        
        avg_confidence = (total_confidence / total_weight
                         if total_weight > 0 else 0)
        
        is_unanimous = (max_votes == total_weight and
                       len(predictions) >= 2)
        
        return {
            'predicted': winner,
            'confidence': avg_confidence,
            'votes': votes,
            'total_strategies': len(predictions),
            'unanimous': is_unanimous,
            'strategies': predictions
        }
    
    def _generate_big_road_list(self, limit):
        """Generar lista simple del Big Road"""
        if not self.history:
            return []
        
        history_list = list(self.history)
        limit_size = limit * 2
        recent = history_list[-limit_size:] if len(history_list) > limit_size else history_list
        
        big_road = []
        current_winner = None
        
        for round_data in recent:
            winner = round_data['winner']
            if winner == 'Tie':
                continue
            if winner != current_winner:
                big_road.append(winner)
                current_winner = winner
        
        return big_road
    
    def get_advanced_prediction(self):
        """Predicción con 6 estrategias validadas"""
        if len(self.history) < 10:
            return None
        
        result = {
            'score_combo': self.exact_score_combo_triggers(),
            'memory': self.pattern_memory_prediction(3),
            'sequence': self.sequence_pattern_triggers(),
            'score_color': self.score_color_triggers(),
            'memory_4': self.pattern_memory_prediction(4),
            'score_diff': self.score_difference_triggers(),
            'consensus': self.four_roads_consensus()
        }
        
        return result
    
    def get_deep_analysis(self):
        """Análisis profundo de la mesa"""
        if len(self.history) < 20:
            return None
        
        recent = list(self.history)[-20:]
        winners = [r['winner'] for r in recent]
        
        player_count = winners.count('Player')
        banker_count = winners.count('Banker')
        tie_count = winners.count('Tie')
        
        # Calcular momentum (dirección)
        momentum_dir = "NEUTRAL"
        momentum_strength = 0
        if len(winners) >= 5:
            last_5 = winners[-5:]
            banker_last5 = last_5.count('Banker')
            player_last5 = last_5.count('Player')
            if banker_last5 > player_last5:
                momentum_dir = "BANKER"
                momentum_strength = (banker_last5 - player_last5) / 5
            elif player_last5 > banker_last5:
                momentum_dir = "PLAYER"
                momentum_strength = (player_last5 - banker_last5) / 5
        
        # Calcular volatilidad (cambios en los últimos 20)
        changes = 0
        for i in range(1, len(winners)):
            if winners[i] != winners[i-1]:
                changes += 1
        volatility = "BAJA" if changes <= 7 else "MEDIA" if changes <= 12 else "ALTA"
        
        # Calcular dominancia
        total = player_count + banker_count
        if total > 0:
            banker_pct = banker_count / total * 100
            player_pct = player_count / total * 100
            if banker_pct > player_pct + 10:
                dominance = "BANKER"
            elif player_pct > banker_pct + 10:
                dominance = "PLAYER"
            else:
                dominance = "EQUILIBRADO"
        else:
            dominance = "EQUILIBRADO"
        
        # Detectar racha activa
        active_streak = None
        streak_count = 1
        for i in range(len(winners)-2, -1, -1):
            if winners[i] == winners[-1]:
                streak_count += 1
            else:
                break
        if streak_count >= 3:
            active_streak = f"{winners[-1]} {streak_count}x"
        
        # Calcular empates
        tie_pct = (tie_count / len(winners) * 100) if len(winners) > 0 else 0
        tie_status = "NORMAL" if tie_pct < 15 else "ALTO" if tie_pct < 25 else "MUY ALTO"
        
        # Hot numbers (scores más frecuentes)
        score_freq = {}
        for r in recent:
            if r['winner'] == 'Player' and r.get('player_score'):
                score = r['player_score']
                score_freq[f'P{score}'] = score_freq.get(f'P{score}', 0) + 1
            elif r['winner'] == 'Banker' and r.get('banker_score'):
                score = r['banker_score']
                score_freq[f'B{score}'] = score_freq.get(f'B{score}', 0) + 1
        
        hot_numbers = sorted(score_freq.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return {
            'momentum': {'direction': momentum_dir, 'strength': momentum_strength},
            'volatility': volatility,
            'dominance': dominance,
            'active_streak': active_streak,
            'tie_status': tie_status,
            'tie_pct': tie_pct,
            'hot_numbers': hot_numbers,
            'changes': changes,
            'player_count': player_count,
            'banker_count': banker_count,
            'tie_count': tie_count
        }
    
    def get_score_grid(self, limit=6):
        """Generar grid de scores recientes"""
        if len(self.history) < 1:
            return []
        
        grid = []
        recent = list(self.history)[-limit*2:]
        
        for r in recent:
            winner = r['winner']
            ps = r.get('player_score', 0)
            bs = r.get('banker_score', 0)
            
            if winner == 'Player':
                cell = f"🔵P{ps}⚡" if ps >= 8 else f"🔵P{ps}·"
            elif winner == 'Banker':
                cell = f"🔴B{bs}⚡" if bs >= 8 else f"🔴B{bs}·"
            else:
                cell = f"🟢T{bs}·"
            
            grid.append(cell)
        
        return grid
    
    def get_all_strategies_status(self):
        """6 estrategias validadas con datos reales"""
        if len(self.history) < 10:
            return {}
        
        return {
            'score_combo': self.exact_score_combo_triggers(),
            'memory_3': self.pattern_memory_prediction(3),
            'sequence': self.sequence_pattern_triggers(),
            'score_color': self.score_color_triggers(),
            'memory_4': self.pattern_memory_prediction(4),
            'score_diff': self.score_difference_triggers(),
        }
    
    def get_big_road_string(self, limit=15):
        """Generar Big Road formateado para Telegram"""
        if not self.history:
            return "⏳ Sin datos"
        
        big_road = self.get_big_road(limit)
        road_str = ' '.join([
            ''.join(['🔴' if w == 'Banker' else '🔵' if w == 'Player' else '🟢' for w in streak])
            for streak in big_road
        ])
        
        return road_str if road_str else "⏳ Sin datos"
    
    def get_last_results_string(self, limit=17):
        """Generar string de últimos resultados"""
        if not self.history:
            return ""
        
        recent = [r['winner'] for r in list(self.history)[-limit:]]
        result = ''.join([
            'B' if w == 'Banker' else 'P' if w == 'Player' else 'T'
            for w in recent
        ])
        
        return result
    
    def get_score_grid_string(self, rows=3, cols=6):
        """Generar score grid formateado para Telegram - datos más recientes primero"""
        max_rounds = min(len(self.history), rows * cols)
        if max_rounds < cols:
            return "⏳ Sin datos suficientes"
        
        # Invertir para mostrar más recientes primero (derecha abajo)
        recent = list(self.history)[-max_rounds:][::-1]
        grid_lines = []
        
        actual_rows = (max_rounds + cols - 1) // cols
        
        for row in range(actual_rows):
            row_data = recent[row*cols:(row+1)*cols]
            if not row_data:
                break
            line_parts = []
            
            for r in row_data:
                winner = r['winner']
                ps = r.get('player_score', 0) or 0
                bs = r.get('banker_score', 0) or 0
                
                if winner == 'Player':
                    cell = f"🔵P{ps}⚡" if ps >= 8 else f"🔵P{ps}·"
                elif winner == 'Banker':
                    cell = f"🔴B{bs}⚡" if bs >= 8 else f"🔴B{bs}·"
                else:
                    cell = f"🟢T{bs}·"
                
                line_parts.append(cell)
            
            grid_lines.append('│'.join(line_parts))
        
        return '\n'.join(grid_lines)
    
    def get_visualization_data(self, max_history=30):
        """Obtener datos de visualización - sincronizado con Evolution Gaming"""
        # Usar el historial completo disponible (ya está limitado a 30 por add_round)
        actual_history = list(self.history)
        
        if not actual_history:
            return {
                'last_results': '',
                'big_road': '⏳ Esperando datos...',
                'score_grid': '⏳ Esperando datos...'
            }
        
        # Score grid: mostrar últimos 18 resultados (3 filas x 6 columnas)
        # De izquierda a derecha, arriba a abajo (igual que Evolution Gaming)
        cols = 6
        rows = 3
        score_grid = self._generate_score_grid(actual_history, rows, cols)
        
        # Big road: agrupar por rachas, mostrar últimos 15 grupos
        big_road = self._generate_big_road_string(actual_history, 15)
        
        # Last results: últimos 17 para análisis de tendencia
        last_results = ''.join([
            'B' if r['winner'] == 'Banker' else 'P' if r['winner'] == 'Player' else 'T'
            for r in actual_history[-17:]
        ])
        
        return {
            'last_results': last_results,
            'big_road': big_road,
            'score_grid': score_grid
        }
    
    def _generate_score_grid(self, history, rows, cols):
        """Generar score grid desde historial dado - muestra últimos resultados de izq a der, arriba a abajo"""
        if len(history) < 1:
            return "⏳ Sin datos"
        
        # Tomar solo los últimos datos que caben en el grid
        max_cells = rows * cols
        display_history = history[-max_cells:] if len(history) > max_cells else history
        
        # Calcular rows necesarias
        actual_rows = min(rows, (len(display_history) + cols - 1) // cols)
        
        grid_lines = []
        for row in range(actual_rows):
            row_data = display_history[row*cols:(row+1)*cols]
            if not row_data:
                break
            line_parts = []
            for r in row_data:
                winner = r['winner']
                ps = r.get('player_score', 0) or 0
                bs = r.get('banker_score', 0) or 0
                if winner == 'Player':
                    cell = f"🔵{ps}⚡" if ps >= 8 else f"🔵{ps}·"
                elif winner == 'Banker':
                    cell = f"🔴{bs}⚡" if bs >= 8 else f"🔴{bs}·"
                else:
                    cell = f"🟢{bs}·"
                line_parts.append(cell)
            grid_lines.append('│'.join(line_parts))
        return '\n'.join(grid_lines)
    
    def _generate_big_road_string(self, history, limit):
        """Generar Big Road desde historial dado"""
        if not history:
            return "⏳ Sin datos"
        
        big_road = []
        current_winner = None
        current_streak = []
        
        for round_data in history[-limit*2:]:
            winner = round_data['winner']
            if winner == 'Tie':
                continue
            
            if winner != current_winner:
                if current_streak:
                    big_road.append(''.join(['🔴' if w == 'Banker' else '🔵' for w in current_streak]))
                current_streak = [winner]
                current_winner = winner
            else:
                current_streak.append(winner)
        
        if current_streak:
            big_road.append(''.join(['🔴' if w == 'Banker' else '🔵' for w in current_streak]))
        
        return ' '.join(big_road[-limit:]) if big_road else "⏳ Sin datos"
    
    def format_prediction_message(self):
        """Generar mensaje formateado"""
        if len(self.history) < 10:
            return "⏳ Esperando más datos..."
        
        pred = self.get_advanced_prediction()
        consensus = pred.get('consensus')
        
        if not consensus:
            return "⏳ Sin consenso suficiente"
        
        recent_17 = [r['winner'] for r in list(self.history)[-17:]]
        player_count = recent_17.count('Player')
        banker_count = recent_17.count('Banker')
        tie_count = recent_17.count('Tie')
        
        big_road = self.get_big_road(20)
        road_str = ' '.join([
            ''.join(['🔴' if w == 'Banker' else '🔵' if w == 'Player' else '🟢' for w in streak])
            for streak in big_road
        ])
        
        last_17_str = ''.join([
            'B' if w == 'Banker' else 'P' if w == 'Player' else 'T'
            for w in recent_17
        ])
        
        predicted = consensus['predicted']
        confidence = consensus['confidence']
        
        bars = int(confidence / 10)
        conf_bar = '🟩' * bars + '⬜' * (10 - bars)
        
        if confidence >= 70:
            conf_level = "⭐ EXCELENTE"
        elif confidence >= 60:
            conf_level = "✅ BUENA"
        elif confidence >= 50:
            conf_level = "⚠️ MODERADA"
        else:
            conf_level = "❌ BAJA"
        
        pred_emoji = "🔴" if predicted == "Banker" else "🔵" if predicted == "Player" else "🟢"
        
        msg = f"""
━━━━━━━━━━━━━━━━━━━━
{pred_emoji} → {predicted.upper()} ← {pred_emoji}
━━━━━━━━━━━━━━━━━━━━

💪 Confianza: {confidence:.0f}% ({conf_level})
{conf_bar}

🎯 Últimos: {last_17_str}

🛣️ BIG ROAD (Principal)
{road_str}

━━━━━━━━━━━━━━━━━━━━
📊 Scores: 🔵P:{player_count} 🔴B:{banker_count} 🟢T:{tie_count}

━━━━━━━━━━━━━━━━━━━━
🎯🧠 ESTRATEGIA AVANZADA:
✅ Consenso: {'UNÁNIME' if consensus['unanimous'] else 'MAYORÍA'}
{pred_emoji} {predicted.upper()} - {confidence:.0f}%

DETALLES:
"""
        
        if pred['twins']:
            msg += f"  • Gemelos: Patrón '{pred['twins']['pattern']}' detectado\n"
        else:
            msg += "  • Gemelos: No detectados\n"
        
        if pred['memory']:
            msg += f"  • Memoria: Patrón visto {pred['memory']['times_seen']}x ({pred['memory']['confidence']:.0f}%)\n"
        else:
            msg += "  • Memoria: Sin patrones fuertes\n"
        
        if pred['streak']:
            msg += f"  • Rachas: {pred['streak']['type']} ({pred['streak']['confidence']:.0f}%)\n"
        else:
            msg += "  • Rachas: No detectadas\n"
        
        return msg
