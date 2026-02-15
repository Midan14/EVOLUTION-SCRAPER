"""
Backtesting offline para estrategias de baccarat sin tocar producción.
Lee rondas desde SQLite (data/results.db) o JSON y evalúa las señales de BaccaratStrategies/RoadAnalyzer.
"""
import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from baccarat_strategies import BaccaratStrategies
from road_analyzer import RoadAnalyzer


def load_rounds_from_sqlite(db_path: Path, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    # Intentar tabla estándar; fallback a baccarat_results
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "baccarat_rounds" in tables:
        query = """
            SELECT game_id, game_number, winner, player_score, banker_score,
                   player_pair, banker_pair, is_natural, with_lightning,
                   shoe_cards_out, total_winners, total_amount, timestamp
            FROM baccarat_rounds
            ORDER BY rowid ASC
        """
    elif "baccarat_results" in tables:
        query = """
            SELECT 
                round_id AS game_id,
                round_id AS game_number,
                result AS winner,
                player_score,
                banker_score,
                0 AS player_pair,
                0 AS banker_pair,
                is_natural,
                0 AS with_lightning,
                NULL AS shoe_cards_out,
                NULL AS total_winners,
                NULL AS total_amount,
                timestamp
            FROM baccarat_results
            ORDER BY rowid ASC
        """
    else:
        conn.close()
        raise RuntimeError("No se encontró tabla baccarat_rounds ni baccarat_results en SQLite")
    if limit:
        query = f"{query} LIMIT {int(limit)}"
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def load_rounds_from_json(json_path: Path, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    data = json.loads(json_path.read_text())
    if isinstance(data, dict) and "rounds" in data:
        data = data["rounds"]
    if not isinstance(data, list):
        raise ValueError("JSON debe ser lista de rondas o tener clave 'rounds'")
    return data[:limit] if limit else data


def backtest(rounds: List[Dict[str, Any]], min_confidence: float, min_strategies: int) -> Dict[str, Any]:
    road_analyzer = RoadAnalyzer()
    strategies = BaccaratStrategies(road_analyzer=road_analyzer)

    history_winners: List[str] = []
    prev_shoe_cards = None

    metrics = {
        "total_rounds": len(rounds),
        "evaluated": 0,
        "predictions": 0,
        "correct": 0,
        "accuracy": 0.0,
        "by_strategy": {},  # name -> {used, correct}
        "by_phase": {},      # early/middle/late -> {predictions, correct}
    }

    for r in rounds:
        winner = r.get("winner")
        if winner not in ("Banker", "Player", "Tie"):
            continue

        shoe_cards_out = r.get("shoe_cards_out") or r.get("shoeCardsOut") or 0
        if prev_shoe_cards is not None and shoe_cards_out < prev_shoe_cards:
            # Nuevo zapato: reset suave
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
            if consensus.get("confidence", 0) >= min_confidence and total_strats >= min_strategies:
                predicted = consensus.get("predicted")
                metrics["predictions"] += 1
                if predicted == winner:
                    metrics["correct"] += 1

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
                if predicted == winner:
                    pstats["correct"] += 1

        # Alimentar histórico después de evaluar
        strategies.add_round(
            winner,
            r.get("player_score") or r.get("playerScore") or 0,
            r.get("banker_score") or r.get("bankerScore") or 0,
            r.get("player_pair") or r.get("playerPair") or False,
            r.get("banker_pair") or r.get("bankerPair") or False,
            r.get("with_lightning") or r.get("withLightning") or False,
        )
        history_winners.append(winner)

    metrics["accuracy"] = (metrics["correct"] / metrics["predictions"] * 100) if metrics["predictions"] else 0.0
    for name, stats in metrics["by_strategy"].items():
        stats["accuracy"] = (stats["correct"] / stats["used"] * 100) if stats["used"] else 0.0
    for phase, stats in metrics["by_phase"].items():
        stats["accuracy"] = (stats["correct"] / stats["predictions"] * 100) if stats["predictions"] else 0.0
    return metrics


def main():
    parser = argparse.ArgumentParser(description="Backtesting offline de estrategias Baccarat.")
    parser.add_argument("--db-path", type=Path, default=Path("data/results.db"), help="Ruta a SQLite con baccarat_rounds")
    parser.add_argument("--json", type=Path, help="Ruta a archivo JSON de rondas (opcional)")
    parser.add_argument("--limit", type=int, help="Límite de rondas a leer (orden ASC)")
    parser.add_argument("--min-confidence", type=float, default=60.0, help="Confianza mínima para contar señal")
    parser.add_argument("--min-strategies", type=int, default=2, help="Mínimo de estrategias alineadas")
    parser.add_argument("--export-json", type=Path, help="Guardar métricas en JSON")
    args = parser.parse_args()

    if args.json:
        rounds = load_rounds_from_json(args.json, args.limit)
    else:
        rounds = load_rounds_from_sqlite(args.db_path, args.limit)

    metrics = backtest(rounds, args.min_confidence, args.min_strategies)

    print("\n=== RESULTADOS BACKTEST OFFLINE ===")
    print(f"Rondas totales: {metrics['total_rounds']} | Evaluadas: {metrics['evaluated']}")
    print(f"Señales emitidas: {metrics['predictions']} | Aciertos: {metrics['correct']} | Accuracy: {metrics['accuracy']:.2f}%")

    if metrics["by_phase"]:
        print("\nPrecisión por fase de zapato:")
        for phase, stats in metrics["by_phase"].items():
            print(f" - {phase}: {stats['accuracy']:.2f}% ({stats['correct']}/{stats['predictions']})")

    if metrics["by_strategy"]:
        print("\nAporte por estrategia (cuando votan):")
        for name, stats in metrics["by_strategy"].items():
            print(f" - {name}: {stats['accuracy']:.2f}% ({stats['correct']}/{stats['used']})")

    if args.export_json:
        args.export_json.write_text(json.dumps(metrics, indent=2))
        print(f"\nMétricas guardadas en {args.export_json}")


if __name__ == "__main__":
    main()
