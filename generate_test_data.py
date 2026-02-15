"""
generate_test_data.py - Generador de datos de prueba + backtest offline sin DB.

Genera rondas de baccarat realistas y ejecuta backtest contra BaccaratStrategies
para validar que las estrategias funcionan correctamente antes de producción.

Uso:
    python3 generate_test_data.py                         # 500 rondas, exporta métricas
    python3 generate_test_data.py --rounds 1000           # 1000 rondas
    python3 generate_test_data.py --shoes 5               # 5 zapatos completos (~80 rondas c/u)
    python3 generate_test_data.py --min-confidence 60     # Umbral de confianza
    python3 generate_test_data.py --export-json results.json
    python3 generate_test_data.py --save-rounds data/test_rounds.json  # Guardar rondas para reuso
    python3 generate_test_data.py --load-rounds data/test_rounds.json  # Cargar rondas previas
"""

import argparse
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from baccarat_strategies import BaccaratStrategies
from road_analyzer import RoadAnalyzer

# ---------------------------------------------------------------------------
# Generación realista de rondas
# ---------------------------------------------------------------------------

# Valores de cartas en baccarat (A=1, 2-9=face, 10/J/Q/K=0)
CARD_VALUES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 0, 0, 0, 0]  # A,2,3,...,9,10,J,Q,K


def _build_shoe(num_decks: int = 8) -> List[int]:
    """Construir un zapato de baccarat con num_decks barajas."""
    shoe = CARD_VALUES * 4 * num_decks  # 4 palos × num_decks barajas
    random.shuffle(shoe)
    return shoe


def _baccarat_score(cards: List[int]) -> int:
    """Calcular score de baccarat (suma mod 10)."""
    return sum(cards) % 10


def _deal_round(shoe: List[int], pos: int):
    """
    Simular una ronda completa de baccarat según reglas oficiales.
    Retorna (winner, player_score, banker_score, player_cards, banker_cards, cards_used).
    """
    if pos + 6 > len(shoe):
        return None  # No quedan suficientes cartas

    # Deal inicial: P, B, P, B
    player_cards = [shoe[pos], shoe[pos + 2]]
    banker_cards = [shoe[pos + 1], shoe[pos + 3]]
    cards_used = 4
    next_card_pos = pos + 4

    p_score = _baccarat_score(player_cards)
    b_score = _baccarat_score(banker_cards)

    player_third = None

    # Regla de naturales
    if p_score >= 8 or b_score >= 8:
        pass  # No se reparten más cartas
    else:
        # Regla del Player: pide si tiene 0-5
        if p_score <= 5:
            player_third = shoe[next_card_pos]
            player_cards.append(player_third)
            cards_used += 1
            next_card_pos += 1
            p_score = _baccarat_score(player_cards)

        # Regla del Banker (depende de si Player pidió tercera carta)
        if player_third is None:
            # Player se plantó: Banker pide si tiene 0-5
            if b_score <= 5:
                banker_cards.append(shoe[next_card_pos])
                cards_used += 1
                b_score = _baccarat_score(banker_cards)
        else:
            # Player pidió tercera: reglas complejas del Banker
            draw_banker = False
            pt = player_third  # Valor de la tercera carta del Player

            if b_score <= 2:
                draw_banker = True
            elif b_score == 3 and pt != 8:
                draw_banker = True
            elif b_score == 4 and pt in (2, 3, 4, 5, 6, 7):
                draw_banker = True
            elif b_score == 5 and pt in (4, 5, 6, 7):
                draw_banker = True
            elif b_score == 6 and pt in (6, 7):
                draw_banker = True
            # b_score == 7: Banker se planta

            if draw_banker:
                banker_cards.append(shoe[next_card_pos])
                cards_used += 1
                b_score = _baccarat_score(banker_cards)

    # Determinar ganador
    if p_score > b_score:
        winner = "Player"
    elif b_score > p_score:
        winner = "Banker"
    else:
        winner = "Tie"

    # Pares
    player_pair = len(player_cards) >= 2 and player_cards[0] == player_cards[1]
    banker_pair = len(banker_cards) >= 2 and banker_cards[0] == banker_cards[1]

    is_natural = (
        len(player_cards) == 2
        and len(banker_cards) == 2
        and (_baccarat_score(player_cards[:2]) >= 8 or _baccarat_score(banker_cards[:2]) >= 8)
    )

    return {
        "winner": winner,
        "player_score": p_score,
        "banker_score": b_score,
        "player_pair": player_pair,
        "banker_pair": banker_pair,
        "is_natural": is_natural,
        "cards_used": cards_used,
        "with_lightning": random.random() < 0.05,  # ~5% lightning
    }


def generate_shoe_rounds(shoe_index: int = 0, base_time: Optional[datetime] = None) -> List[Dict]:
    """Generar todas las rondas de un zapato completo (8 barajas)."""
    shoe = _build_shoe(8)
    rounds = []
    pos = 0
    # Descartar carta de corte (burn)
    pos += 1

    if base_time is None:
        base_time = datetime.now()

    round_num = 0
    while pos + 6 <= len(shoe):
        # El zapato se corta típicamente cuando quedan ~30-50 cartas
        remaining = len(shoe) - pos
        if remaining < 40 and round_num > 20:
            # Probabilidad creciente de cortar el zapato
            if random.random() < (1 - remaining / 60):
                break

        result = _deal_round(shoe, pos)
        if result is None:
            break

        pos += result.pop("cards_used")
        round_num += 1

        result["game_id"] = f"shoe{shoe_index:03d}_r{round_num:03d}"
        result["game_number"] = f"S{shoe_index}-R{round_num}"
        result["shoe_cards_out"] = pos
        result["timestamp"] = (base_time + timedelta(seconds=round_num * 25)).isoformat()

        rounds.append(result)

    return rounds


def generate_rounds(
    num_rounds: Optional[int] = None, num_shoes: Optional[int] = None
) -> List[Dict]:
    """Generar rondas de prueba. Especificar num_rounds O num_shoes."""
    all_rounds: List[Dict] = []
    shoe_idx = 0
    base_time = datetime.now() - timedelta(hours=4)

    if num_shoes:
        for _ in range(num_shoes):
            shoe_rounds = generate_shoe_rounds(shoe_idx, base_time)
            all_rounds.extend(shoe_rounds)
            base_time += timedelta(minutes=len(shoe_rounds) * 0.5 + 5)
            shoe_idx += 1
    else:
        target = num_rounds or 500
        while len(all_rounds) < target:
            shoe_rounds = generate_shoe_rounds(shoe_idx, base_time)
            all_rounds.extend(shoe_rounds)
            base_time += timedelta(minutes=len(shoe_rounds) * 0.5 + 5)
            shoe_idx += 1
        all_rounds = all_rounds[:target]

    return all_rounds


# ---------------------------------------------------------------------------
# Backtest engine
# ---------------------------------------------------------------------------


def backtest(
    rounds: List[Dict],
    min_confidence: float = 55.0,
    min_strategies: int = 2,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Ejecuta backtest offline de BaccaratStrategies + RoadAnalyzer.
    Devuelve métricas detalladas.
    """
    road_analyzer = RoadAnalyzer()
    strategies = BaccaratStrategies(road_analyzer=road_analyzer)

    history_winners: List[str] = []
    prev_shoe_cards: Optional[int] = None

    metrics: Dict[str, Any] = {
        "total_rounds": len(rounds),
        "evaluated": 0,
        "predictions": 0,
        "correct": 0,
        "accuracy": 0.0,
        "skipped_low_confidence": 0,
        "skipped_few_strategies": 0,
        "by_strategy": {},
        "by_phase": {},
        "by_winner": {
            "Banker": {"predicted": 0, "correct": 0},
            "Player": {"predicted": 0, "correct": 0},
        },
        "confidence_buckets": {
            "50-59": {"count": 0, "correct": 0},
            "60-69": {"count": 0, "correct": 0},
            "70-79": {"count": 0, "correct": 0},
            "80+": {"count": 0, "correct": 0},
        },
        "consecutive_wrong": 0,
        "max_consecutive_wrong": 0,
        "consecutive_right": 0,
        "max_consecutive_right": 0,
    }

    for r in rounds:
        winner = r.get("winner")
        if winner not in ("Banker", "Player", "Tie"):
            continue

        shoe_cards_out = r.get("shoe_cards_out") or r.get("shoeCardsOut") or 0

        # Detectar nuevo zapato
        if prev_shoe_cards is not None and shoe_cards_out < prev_shoe_cards:
            strategies.reset_history_soft()
            road_analyzer = RoadAnalyzer()
            strategies.road_analyzer = road_analyzer
            history_winners.clear()
        prev_shoe_cards = shoe_cards_out

        strategies.set_shoe_cards_out(shoe_cards_out)
        road_analyzer.update_from_history(history_winners)

        road_consensus = road_analyzer.get_four_roads_consensus()
        advanced = strategies.get_advanced_prediction(road_consensus=road_consensus)
        metrics["evaluated"] += 1

        consensus = advanced.get("consensus") if advanced else None
        if consensus:
            total_strats = consensus.get("total_strategies") or len(consensus.get("strategies", []))
            conf = consensus.get("confidence", 0)

            if conf < min_confidence:
                metrics["skipped_low_confidence"] += 1
            elif total_strats < min_strategies:
                metrics["skipped_few_strategies"] += 1
            else:
                predicted = consensus.get("predicted")
                metrics["predictions"] += 1
                was_correct = predicted == winner

                if was_correct:
                    metrics["correct"] += 1
                    metrics["consecutive_wrong"] = 0
                    metrics["consecutive_right"] += 1
                    metrics["max_consecutive_right"] = max(
                        metrics["max_consecutive_right"], metrics["consecutive_right"]
                    )
                else:
                    metrics["consecutive_right"] = 0
                    metrics["consecutive_wrong"] += 1
                    metrics["max_consecutive_wrong"] = max(
                        metrics["max_consecutive_wrong"], metrics["consecutive_wrong"]
                    )

                # By winner
                if predicted in metrics["by_winner"]:
                    metrics["by_winner"][predicted]["predicted"] += 1
                    if was_correct:
                        metrics["by_winner"][predicted]["correct"] += 1

                # Confidence bucket
                if conf >= 80:
                    bucket = "80+"
                elif conf >= 70:
                    bucket = "70-79"
                elif conf >= 60:
                    bucket = "60-69"
                else:
                    bucket = "50-59"
                metrics["confidence_buckets"][bucket]["count"] += 1
                if was_correct:
                    metrics["confidence_buckets"][bucket]["correct"] += 1

                # Per-strategy stats
                for s in consensus.get("strategies", []):
                    name = s.get("strategy", "unknown")
                    predicted_s = s.get("predicted")
                    stats = metrics["by_strategy"].setdefault(name, {"used": 0, "correct": 0})
                    stats["used"] += 1
                    if predicted_s == winner:
                        stats["correct"] += 1

                # Phase stats
                phase = advanced.get("shoe_phase", "unknown")
                pstats = metrics["by_phase"].setdefault(phase, {"predictions": 0, "correct": 0})
                pstats["predictions"] += 1
                if was_correct:
                    pstats["correct"] += 1

                if verbose:
                    mark = "✅" if was_correct else "❌"
                    print(
                        f"  {mark} R{metrics['evaluated']:3d}: "
                        f"Pred={predicted:7s} ({conf:4.1f}%) "
                        f"Real={winner:7s} "
                        f"Strats={total_strats}"
                    )

        # Alimentar histórico DESPUÉS de evaluar (para no hacer trampa)
        strategies.add_round(
            winner,
            r.get("player_score") or r.get("playerScore") or 0,
            r.get("banker_score") or r.get("bankerScore") or 0,
            r.get("player_pair") or r.get("playerPair") or False,
            r.get("banker_pair") or r.get("bankerPair") or False,
            r.get("with_lightning") or r.get("withLightning") or False,
        )
        history_winners.append(winner)

    # Calcular accuracies
    metrics["accuracy"] = (
        (metrics["correct"] / metrics["predictions"] * 100) if metrics["predictions"] else 0.0
    )
    for name, stats in metrics["by_strategy"].items():
        stats["accuracy"] = (stats["correct"] / stats["used"] * 100) if stats["used"] else 0.0
    for phase, stats in metrics["by_phase"].items():
        stats["accuracy"] = (
            (stats["correct"] / stats["predictions"] * 100) if stats["predictions"] else 0.0
        )
    for bucket, stats in metrics["confidence_buckets"].items():
        stats["accuracy"] = (stats["correct"] / stats["count"] * 100) if stats["count"] else 0.0
    for side, stats in metrics["by_winner"].items():
        stats["accuracy"] = (
            (stats["correct"] / stats["predicted"] * 100) if stats["predicted"] else 0.0
        )

    # Cleanup tracking fields
    del metrics["consecutive_wrong"]
    del metrics["consecutive_right"]

    return metrics


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

_COLORS = {
    "green": "\033[92m",
    "red": "\033[91m",
    "yellow": "\033[93m",
    "cyan": "\033[96m",
    "bold": "\033[1m",
    "reset": "\033[0m",
}


def _c(text: str, color: str) -> str:
    """Colorize text for terminal."""
    return f"{_COLORS.get(color, '')}{text}{_COLORS['reset']}"


def print_report(metrics: Dict[str, Any], rounds: List[Dict]) -> None:
    """Pretty-print backtest results."""
    print()
    print(_c("═" * 60, "bold"))
    print(_c("  📊 BACKTEST OFFLINE - RESULTADOS", "bold"))
    print(_c("═" * 60, "bold"))

    # Distribución de datos generados
    winners = [r["winner"] for r in rounds if r.get("winner")]
    b_count = winners.count("Banker")
    p_count = winners.count("Player")
    t_count = winners.count("Tie")
    total = len(winners)
    print(f"\n📈 Datos generados: {total} rondas")
    print(
        f"   🔴 Banker: {b_count} ({b_count / total * 100:.1f}%) "
        f"| 🔵 Player: {p_count} ({p_count / total * 100:.1f}%) "
        f"| 🟢 Tie: {t_count} ({t_count / total * 100:.1f}%)"
    )

    # Resultados principales
    preds = metrics["predictions"]
    correct = metrics["correct"]
    acc = metrics["accuracy"]

    print(f"\n🎯 Señales emitidas: {preds} de {metrics['evaluated']} evaluadas")
    print(f"   Skipped (baja confianza): {metrics['skipped_low_confidence']}")
    print(f"   Skipped (pocas estrategias): {metrics['skipped_few_strategies']}")

    acc_color = "green" if acc > 50 else "yellow" if acc > 45 else "red"
    print(f"\n{_c(f'   ✅ Aciertos: {correct}/{preds} = {acc:.2f}%', acc_color)}")
    print(f"   📉 Peor racha de errores: {metrics['max_consecutive_wrong']} seguidos")
    print(f"   📈 Mejor racha de aciertos: {metrics['max_consecutive_right']} seguidos")

    # Por lado
    print(f"\n{'─' * 40}")
    print("  Precisión por lado predicho:")
    for side, stats in metrics["by_winner"].items():
        if stats["predicted"] > 0:
            emoji = "🔴" if side == "Banker" else "🔵"
            s_acc = stats["accuracy"]
            color = "green" if s_acc > 50 else "yellow" if s_acc > 45 else "red"
            print(
                f"   {emoji} {side}: {_c(f'{s_acc:.1f}%', color)} ({stats['correct']}/{stats['predicted']})"
            )

    # Por bucket de confianza
    print(f"\n{'─' * 40}")
    print("  Precisión por nivel de confianza:")
    for bucket, stats in sorted(metrics["confidence_buckets"].items()):
        if stats["count"] > 0:
            b_acc = stats["accuracy"]
            color = "green" if b_acc > 50 else "yellow" if b_acc > 45 else "red"
            bar = "█" * int(b_acc / 5) + "░" * (20 - int(b_acc / 5))
            print(
                f"   {bucket:>5}%: {bar} {_c(f'{b_acc:.1f}%', color)} ({stats['correct']}/{stats['count']})"
            )

    # Por fase del zapato
    if metrics["by_phase"]:
        print(f"\n{'─' * 40}")
        print("  Precisión por fase del zapato:")
        phase_emojis = {"early": "🌱", "middle": "⚖️", "late": "🏁", "unknown": "❓"}
        for phase, stats in metrics["by_phase"].items():
            if stats["predictions"] > 0:
                p_acc = stats["accuracy"]
                emoji = phase_emojis.get(phase, "❓")
                color = "green" if p_acc > 50 else "yellow" if p_acc > 45 else "red"
                print(
                    f"   {emoji} {phase:>7}: {_c(f'{p_acc:.1f}%', color)} "
                    f"({stats['correct']}/{stats['predictions']})"
                )

    # Por estrategia
    if metrics["by_strategy"]:
        print(f"\n{'─' * 40}")
        print("  Aporte por estrategia (cuando votan):")
        sorted_strats = sorted(
            metrics["by_strategy"].items(), key=lambda x: x[1]["accuracy"], reverse=True
        )
        for name, stats in sorted_strats:
            if stats["used"] >= 3:  # Solo mostrar con suficientes muestras
                s_acc = stats["accuracy"]
                color = "green" if s_acc > 50 else "yellow" if s_acc > 45 else "red"
                print(
                    f"   {name:>25}: {_c(f'{s_acc:.1f}%', color)} ({stats['correct']}/{stats['used']})"
                )

    # Veredicto final
    print(f"\n{'═' * 60}")
    if acc >= 55:
        print(_c("  🎉 VEREDICTO: Las estrategias muestran edge positivo", "green"))
    elif acc >= 50:
        print(_c("  ⚠️  VEREDICTO: Rendimiento cercano al baseline (sin edge claro)", "yellow"))
    else:
        print(_c("  ❌ VEREDICTO: Rendimiento inferior al baseline", "red"))
    print(f"  (Baseline baccarat: ~45.8% Banker, ~44.6% Player sin comisión)")
    print(f"{'═' * 60}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Generador de datos de prueba + backtest offline para baccarat."
    )
    parser.add_argument(
        "--rounds", type=int, default=500, help="Número de rondas a generar (default: 500)"
    )
    parser.add_argument(
        "--shoes", type=int, default=None, help="Generar N zapatos completos (override --rounds)"
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=55.0,
        help="Confianza mínima para contar señal (default: 55)",
    )
    parser.add_argument(
        "--min-strategies",
        type=int,
        default=2,
        help="Mínimo de estrategias alineadas (default: 2)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Mostrar cada predicción individual"
    )
    parser.add_argument(
        "--export-json",
        type=Path,
        default=Path("backtest_metrics.json"),
        help="Guardar métricas en JSON (default: backtest_metrics.json)",
    )
    parser.add_argument(
        "--save-rounds", type=Path, default=None, help="Guardar rondas generadas en JSON"
    )
    parser.add_argument(
        "--load-rounds", type=Path, default=None, help="Cargar rondas desde JSON en vez de generar"
    )
    parser.add_argument("--seed", type=int, default=None, help="Semilla para reproducibilidad")
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Ejecutar N backtests y promediar resultados (default: 1)",
    )
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    if args.load_rounds:
        print(f"📂 Cargando rondas desde {args.load_rounds}...")
        data = json.loads(args.load_rounds.read_text())
        if isinstance(data, dict) and "rounds" in data:
            rounds = data["rounds"]
        elif isinstance(data, list):
            rounds = data
        else:
            print("❌ Formato JSON no reconocido")
            sys.exit(1)
        print(f"   Cargadas {len(rounds)} rondas")

        metrics = backtest(rounds, args.min_confidence, args.min_strategies, args.verbose)
        print_report(metrics, rounds)

        if args.export_json:
            args.export_json.write_text(json.dumps(metrics, indent=2, default=str))
            print(f"💾 Métricas guardadas en {args.export_json}")
        return

    if args.runs > 1:
        print(f"🔄 Ejecutando {args.runs} backtests y promediando...\n")
        all_acc = []
        agg_metrics = None

        for run_i in range(args.runs):
            if args.shoes:
                rounds = generate_rounds(num_shoes=args.shoes)
            else:
                rounds = generate_rounds(num_rounds=args.rounds)

            m = backtest(rounds, args.min_confidence, args.min_strategies, verbose=False)
            all_acc.append(m["accuracy"])

            if agg_metrics is None:
                agg_metrics = m
            else:
                agg_metrics["total_rounds"] += m["total_rounds"]
                agg_metrics["evaluated"] += m["evaluated"]
                agg_metrics["predictions"] += m["predictions"]
                agg_metrics["correct"] += m["correct"]

            print(f"  Run {run_i + 1:3d}: {m['accuracy']:.2f}% ({m['correct']}/{m['predictions']})")

        avg_acc = sum(all_acc) / len(all_acc)
        min_acc = min(all_acc)
        max_acc = max(all_acc)
        agg_metrics["accuracy"] = avg_acc

        print(f"\n{'─' * 40}")
        acc_color = "green" if avg_acc > 50 else "yellow" if avg_acc > 45 else "red"
        print(f"  Promedio: {_c(f'{avg_acc:.2f}%', acc_color)}")
        print(f"  Rango: {min_acc:.2f}% — {max_acc:.2f}%")
        print(
            f"  Total: {agg_metrics['correct']}/{agg_metrics['predictions']} "
            f"en {agg_metrics['total_rounds']} rondas"
        )

        if args.export_json:
            agg_metrics["runs"] = args.runs
            agg_metrics["per_run_accuracy"] = all_acc
            args.export_json.write_text(json.dumps(agg_metrics, indent=2, default=str))
            print(f"\n💾 Métricas agregadas guardadas en {args.export_json}")
        return

    # Single run
    print("🎲 Generando datos de prueba realistas (reglas oficiales de baccarat)...")
    if args.shoes:
        rounds = generate_rounds(num_shoes=args.shoes)
    else:
        rounds = generate_rounds(num_rounds=args.rounds)

    print(f"   Generadas {len(rounds)} rondas\n")

    if args.save_rounds:
        args.save_rounds.parent.mkdir(parents=True, exist_ok=True)
        args.save_rounds.write_text(json.dumps(rounds, indent=2, default=str))
        print(f"💾 Rondas guardadas en {args.save_rounds}\n")

    print("🧪 Ejecutando backtest...")
    metrics = backtest(rounds, args.min_confidence, args.min_strategies, args.verbose)
    print_report(metrics, rounds)

    if args.export_json:
        args.export_json.parent.mkdir(parents=True, exist_ok=True)
        args.export_json.write_text(json.dumps(metrics, indent=2, default=str))
        print(f"💾 Métricas guardadas en {args.export_json}")


if __name__ == "__main__":
    main()
