# telegram_notifier.py
import asyncio
import html
import logging

from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


def _safe_html(text):
    """Escape text for Telegram HTML parse mode, preserving intentional HTML tags."""
    if not isinstance(text, str):
        return str(text)
    # Escape everything first
    escaped = html.escape(str(text))
    # Restore intentional Telegram-supported HTML tags
    restore_tags = ["b", "i", "u", "s", "code", "pre"]
    for tag in restore_tags:
        escaped = escaped.replace(f"&lt;{tag}&gt;", f"<{tag}>")
        escaped = escaped.replace(f"&lt;/{tag}&gt;", f"</{tag}>")
    return escaped


class TelegramNotifier:
    def __init__(self, token, chat_id):
        self.bot = Bot(token=token)
        self.chat_id = chat_id
        logger.info(f"✅ TelegramNotifier inicializado - Chat ID: {chat_id}")

    async def send_message(self, text, parse_mode="HTML"):
        """Enviar mensaje a Telegram con sanitización HTML automática."""
        try:
            safe_text = _safe_html(text) if parse_mode == "HTML" else text

            # Telegram limit is 4096 chars; truncate gracefully
            if len(safe_text) > 4090:
                safe_text = safe_text[:4087] + "..."

            await self.bot.send_message(chat_id=self.chat_id, text=safe_text, parse_mode=parse_mode)
            logger.info("✅ Mensaje enviado a Telegram")
            return True
        except TelegramError as e:
            logger.error(f"❌ Error enviando mensaje a Telegram: {e}")
            # Fallback: try without parse_mode if HTML failed
            if parse_mode == "HTML":
                try:
                    await self.bot.send_message(chat_id=self.chat_id, text=text, parse_mode=None)
                    logger.info("✅ Mensaje enviado a Telegram (sin formato HTML)")
                    return True
                except Exception as e2:
                    logger.error(f"❌ Fallback sin HTML también falló: {e2}")
            return False
        except Exception as e:
            logger.error(f"❌ Error inesperado en Telegram: {e}")
            return False

    async def send_prediction(self, prediction_data):
        """Enviar predicción ANTES de que termine la ronda"""
        try:
            predicted = prediction_data.get("predicted")
            confidence = prediction_data.get("confidence", 0)
            game_id = prediction_data.get("game_id", "N/A")

            recent_stats = prediction_data.get("recent_stats", {})
            player_count = recent_stats.get("player", 0)
            banker_count = recent_stats.get("banker", 0)
            tie_count = recent_stats.get("tie", 0)

            shoe_cards_out = prediction_data.get("shoe_cards_out", 0)
            shoe_pct = (shoe_cards_out / 416 * 100) if shoe_cards_out else 0

            total_stats = prediction_data.get("total_stats", {})
            total_correct = total_stats.get("correct", 0)
            total_predictions = total_stats.get("total", 0)
            accuracy = (total_correct / total_predictions * 100) if total_predictions > 0 else 0

            if predicted == "Banker":
                emoji = "🔴"
            elif predicted == "Player":
                emoji = "🔵"
            else:
                emoji = "🟢"

            safe_game_id = html.escape(str(game_id))
            safe_predicted = html.escape(str(predicted).upper())

            message = f"""🎯 <b>PREDICCIÓN PRÓXIMA RONDA</b>

━━━━━━━━━━━━━━━━━━━━
{emoji} <b>{safe_predicted}</b> {emoji}
━━━━━━━━━━━━━━━━━━━━

💪 Confianza: <b>{confidence:.1f}%</b>
🆔 Mano: <code>{safe_game_id}</code>

📊 Mesa: 🔵P:{player_count} 🔴B:{banker_count} 🟢T:{tie_count}
🃏 Zapato: {shoe_cards_out}/416 ({shoe_pct:.0f}%)

📈 Precisión Global: {accuracy:.1f}% ({total_correct}/{total_predictions})"""

            result = await self.send_message(message)
            if result:
                logger.info("✅ Predicción enviada a Telegram")
            return result
        except Exception as e:
            logger.error(f"❌ Error en send_prediction: {e}")
            return False

    def _format_cards(self, cards):
        """Formatear cartas para mostrar"""
        if not cards:
            return "?"

        suits_map = {
            "h": "♥",
            "hearts": "♥",
            "♥": "♥",
            "d": "♦",
            "diamonds": "♦",
            "♦": "♦",
            "c": "♣",
            "clubs": "♣",
            "♣": "♣",
            "s": "♠",
            "spades": "♠",
            "♠": "♠",
        }

        ranks_map = {"1": "A", "11": "J", "12": "Q", "13": "K"}

        def format_card(card):
            if isinstance(card, dict):
                rank_raw = str(card.get("rank", "?"))
                suit_raw = str(card.get("suit", "")).lower()
            elif isinstance(card, str):
                raw = card.strip()
                if not raw:
                    return "?"
                # Separar rango y palo usando el último caracter
                suit_raw = raw[-1]
                rank_raw = raw[:-1] if len(raw) > 1 else raw
                suit_raw = suit_raw.lower()
            else:
                return "?"

            rank_norm = rank_raw.upper()
            rank_display = ranks_map.get(rank_norm, rank_norm)
            suit_display = suits_map.get(suit_raw, suit_raw)

            return f"{rank_display}{suit_display}".strip()

        formatted = [format_card(card) for card in cards]
        return " ".join(formatted)

    async def send_result(self, result_data):
        """Enviar resultado detallado"""
        try:
            logger.info("📤 Preparando mensaje de resultado...")

            predicted = result_data.get("predicted")
            actual = result_data.get("actual")
            was_correct = result_data.get("was_correct", False)
            confidence = result_data.get("confidence", 0)
            game_id = result_data.get("game_id", "N/A")
            game_number = result_data.get("game_number", "N/A")

            player_cards = result_data.get("player_cards", [])
            banker_cards = result_data.get("banker_cards", [])
            player_score = result_data.get("player_score", 0)
            banker_score = result_data.get("banker_score", 0)

            recent_stats = result_data.get("recent_stats", {})
            player_count = recent_stats.get("player", 0)
            banker_count = recent_stats.get("banker", 0)
            tie_count = recent_stats.get("tie", 0)

            shoe_cards_out = result_data.get("shoe_cards_out", 0)
            shoe_pct = (shoe_cards_out / 416 * 100) if shoe_cards_out else 0

            total_stats = result_data.get("total_stats", {})
            total_correct = total_stats.get("correct", 0)
            total_predictions = total_stats.get("total", 0)
            total_wrong = total_predictions - total_correct
            accuracy = (total_correct / total_predictions * 100) if total_predictions > 0 else 0

            if was_correct:
                status = "✅✅✅ GANASTE ✅✅✅"
            else:
                status = "❌❌❌ PERDISTE ❌❌❌"

            pred_emoji = "🔴" if predicted == "Banker" else "🔵" if predicted == "Player" else "🟢"
            actual_emoji = "🔴" if actual == "Banker" else "🔵" if actual == "Player" else "🟢"

            player_cards_str = html.escape(self._format_cards(player_cards))
            banker_cards_str = html.escape(self._format_cards(banker_cards))
            safe_game_id = html.escape(str(game_id))
            safe_predicted = html.escape(str(predicted).upper()) if predicted else "N/A"
            safe_actual = html.escape(str(actual).upper()) if actual else "N/A"

            message = f"""{status}

🆔 Mano: <code>{safe_game_id}</code>

🔵 PLAYER: {player_cards_str} = {player_score}
🔴 BANKER: {banker_cards_str} = {banker_score}

Predije: {pred_emoji} <b>{safe_predicted}</b>
Salió: {actual_emoji} <b>{safe_actual}</b>

📊 Mesa: 🔵P:{player_count} 🔴B:{banker_count} 🟢T:{tie_count}
🃏 Zapato: {shoe_cards_out}/416 ({shoe_pct:.0f}%)

📊 REGISTRO TOTAL:
✅ Ganadas: {total_correct}
❌ Perdidas: {total_wrong}
📈 Precisión: {accuracy:.1f}%"""

            result = await self.send_message(message)
            if result:
                logger.info("✅ Resultado enviado correctamente")
            return result
        except Exception as e:
            logger.error(f"❌ Error en send_result: {e}")
            import traceback

            logger.error(traceback.format_exc())
            return False

    async def send_advanced_prediction(self, strategies_data):
        """Enviar predicción avanzada (Gemelos, Memoria, etc)"""
        try:
            consensus = strategies_data.get("consensus")

            if not consensus:
                logger.warning("⚠️ No hay consenso para enviar")
                return False

            predicted = consensus["predicted"]
            confidence = consensus["confidence"]
            unanimous = consensus["unanimous"]

            if predicted == "Banker":
                emoji = "🔴"
            elif predicted == "Player":
                emoji = "🔵"
            else:
                emoji = "🟢"

            twins = strategies_data.get("twins")
            memory = strategies_data.get("memory")
            streak = strategies_data.get("streak")

            details = []
            if twins:
                details.append("• Gemelos: ✅ Detectado")
            else:
                details.append("• Gemelos: ❌")

            if memory:
                details.append(
                    f"• Memoria: Visto {memory['times_seen']}x ({memory['confidence']:.0f}%)"
                )
            else:
                details.append("• Memoria: Sin datos")

            if streak:
                details.append(f"• Racha: {html.escape(str(streak['type']))}")
            else:
                details.append("• Racha: Normal")

            safe_predicted = html.escape(str(predicted).upper())

            message = f"""🧠 <b>ESTRATEGIA AVANZADA</b>

━━━━━━━━━━━━━━━━━━━━
{emoji} <b>{safe_predicted}</b> {emoji}
━━━━━━━━━━━━━━━━━━━━

💪 Confianza: <b>{confidence:.0f}%</b>
🎯 Consenso: <b>{"UNÁNIME" if unanimous else "MAYORÍA"}</b>

<b>DETALLES:</b>
{chr(10).join(details)}"""

            result = await self.send_message(message)
            return result
        except Exception as e:
            logger.error(f"❌ Error en send_advanced_prediction: {e}")
            return False

    async def send_roads_analysis(self, roads_text):
        """Análisis de roads deshabilitado"""
        logger.info("ℹ️ Análisis de roads deshabilitado (formato eliminado)")
        return False

    async def send_lightning_prediction(self, data):
        """Enviar predicción Lightning Baccarat con EV, señal, multiplicadores y Kelly"""
        try:
            predicted = data.get("predicted")
            confidence = data.get("confidence", 0)
            game_id = data.get("game_id", "N/A")
            
            # Lightning data
            lightning_data = data.get("lightning_data", {})
            avg_multiplier = lightning_data.get("avg_multiplier", 1.0)
            distribution = lightning_data.get("distribution", "No data")
            hot_table = lightning_data.get("hot_table", False)
            
            # Bankroll & EV data
            signal_data = data.get("signal_data", {})
            signal = signal_data.get("signal", "SALTAR")
            ev_formatted = signal_data.get("ev_formatted", "+0.00")
            kelly_pct = signal_data.get("kelly_pct", 0.0)
            recommended_amount = signal_data.get("recommended_amount", 0.0)
            reason = signal_data.get("reason", "")
            
            # Session stats
            session_stats = data.get("session_stats", {})
            bankroll = session_stats.get("bankroll", 0.0)
            session_pnl = session_stats.get("session_pnl", 0.0)
            wins = session_stats.get("wins", 0)
            losses = session_stats.get("losses", 0)
            
            # Recent stats
            recent_stats = data.get("recent_stats", {})
            player_count = recent_stats.get("player", 0)
            banker_count = recent_stats.get("banker", 0)
            tie_count = recent_stats.get("tie", 0)
            
            if predicted == "Banker":
                emoji = "🔴"
            elif predicted == "Player":
                emoji = "🔵"
            else:
                emoji = "🟢"
            
            signal_emoji = "🟢" if signal == "APOSTAR" else "🔴"
            hot_emoji = "🔥" if hot_table else "❄️"
            
            safe_game_id = html.escape(str(game_id))
            safe_predicted = html.escape(str(predicted).upper())
            
            message = f"""⚡ <b>LIGHTNING BACCARAT PREDICCIÓN</b>
            
━━━━━━━━━━━━━━━━━━━━
{emoji} <b>{safe_predicted}</b> {emoji}
━━━━━━━━━━━━━━━━━━━━

💪 Confianza: <b>{confidence:.1f}%</b>
🆔 Mano: <code>{safe_game_id}</code>

⚡ <b>LIGHTNING MULTIPLIERS</b>
📊 Promedio: <b>{avg_multiplier:.2f}x</b>
📈 Distribución: {html.escape(str(distribution))}
{hot_emoji} Mesa: <b>{"CALIENTE" if hot_table else "NORMAL"}</b>

💰 <b>SEÑAL DE APUESTA</b>
{signal_emoji} <b>{signal}</b>
📊 EV: <b>{ev_formatted}</b>
🎯 Kelly: <b>{kelly_pct:.1f}%</b>
💵 Cantidad: <b>${recommended_amount:.2f}</b>

<i>{html.escape(reason)}</i>

💼 <b>BANKROLL</b>
💰 Actual: ${bankroll:.2f}
📊 Sesión P&L: {'+' if session_pnl >= 0 else ''}{session_pnl:.2f}
✅ Ganadas: {wins} | ❌ Perdidas: {losses}

📊 Mesa: 🔵P:{player_count} 🔴B:{banker_count} 🟢T:{tie_count}"""
            
            result = await self.send_message(message)
            if result:
                logger.info("✅ Predicción Lightning enviada a Telegram")
            return result
        except Exception as e:
            logger.error(f"❌ Error en send_lightning_prediction: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def send_comprehensive_prediction(self, data):
        """Enviar predicción comprehensiva con todas las estrategias"""
        try:
            predicted = data.get("predicted")
            confidence = data.get("confidence", 0)
            game_id = data.get("game_id", "N/A")
            game_number = data.get("game_number", "N/A")
            game_name = data.get("game_name", "Baccarat")
            
            strategies_data = data.get("strategies_data", {})
            deep_analysis = data.get("deep_analysis", {})
            consensus = strategies_data.get("consensus", {})
            
            recent_stats = data.get("recent_stats", {})
            player_count = recent_stats.get("player", 0)
            banker_count = recent_stats.get("banker", 0)
            tie_count = recent_stats.get("tie", 0)
            
            pairs_data = data.get("pairs_data", {})
            player_pairs = pairs_data.get("player_pairs", 0)
            banker_pairs = pairs_data.get("banker_pairs", 0)
            
            shoe_cards_out = data.get("shoe_cards_out", 0)
            shoe_pct = (shoe_cards_out / 416 * 100) if shoe_cards_out else 0
            
            big_road_data = data.get("big_road", [])
            score_grid_data = data.get("score_grid", [])
            last_results = data.get("last_results", "")
            
            total_stats = data.get("total_stats", {})
            total_correct = total_stats.get("correct", 0)
            total_predictions = total_stats.get("total", 0)
            accuracy = (total_correct / total_predictions * 100) if total_predictions > 0 else 0
            
            if predicted == "Banker":
                emoji = "🔴"
            elif predicted == "Player":
                emoji = "🔵"
            else:
                emoji = "🟢"
            
            conf_level = "⭐ EXCELENTE" if confidence >= 70 else "✅ BUENA" if confidence >= 60 else "⚠️ MODERADA" if confidence >= 50 else "❌ BAJA"
            
            bars = int(confidence / 10)
            conf_bar = "🟩" * bars + "⬜" * (10 - bars)
            
            strategies_votes = consensus.get("total_strategies", 0) if consensus else 0
            unanimous = consensus.get("unanimous", False) if consensus else False
            
            msg = f"""🎯🧠 PREDICCIÓN - PATTERN MEMORY + GEMELOS + 4 ROADS

📊 MESA #{game_number} {game_name}
🔵P:{player_count} 🔴B:{banker_count} 🟢T:{tie_count} | Pairs - P:{player_pairs} B:{banker_pairs}

🆔 Mano: <code>{html.escape(str(game_id))}</code>
📌 Apuesta: PRÓXIMA mano

━━━━━━━━━━━━━━━━━━━━
{emoji} → {predicted.upper()} ← {emoji}
━━━━━━━━━━━━━━━━━━━━

💪 Confianza: {confidence:.0f}% ({conf_level})
{conf_bar}

📋 ✅ Consenso: {strategies_votes}/6 estrategias

🎯 Últimos: {last_results}

🛣️ BIG ROAD (Principal)
{big_road_data}

━━━━━━━━━━━━━━━━━━━━
📊 Scores: 🔵P:{player_count} 🔴B:{banker_count} 🟢T:{tie_count} | Pairs - P:{player_pairs} B:{banker_pairs}
{score_grid_data}

ESTRATEGIAS ACTIVAS:
"""
            
            all_strategies = strategies_data.get("all_strategies", {})
            
            # 1. Score-Combo (60-87% combos exactos de scores)
            score_combo = all_strategies.get("score_combo")
            if score_combo:
                msg += f"  • 🎯 Score-Combo: ✅ {score_combo.get('trigger_name', '')} ({score_combo.get('confidence', 0):.0f}%)\n"
            else:
                msg += "  • 🎯 Score-Combo: ❌ Sin match\n"
            
            # 2. Memory-3 (67.6% accuracy real)
            mem3 = all_strategies.get("memory_3")
            if mem3:
                msg += f"  • 🧠 Memory-3: ✅ '{mem3.get('pattern', '')}' → {mem3.get('predicted', '')} ({mem3.get('confidence', 0):.0f}%)\n"
            else:
                msg += "  • 🧠 Memory-3: ❌ Sin patrón\n"
            
            # 3. Sequence (55-76% secuencias de resultados)
            sequence = all_strategies.get("sequence")
            if sequence:
                msg += f"  • 🔗 Sequence: ✅ {sequence.get('trigger_name', '')} ({sequence.get('confidence', 0):.0f}%)\n"
            else:
                msg += "  • 🔗 Sequence: ❌ Sin secuencia\n"
            
            # 4. Score-Color (55-62% validada con 1438 rondas)
            score_color = all_strategies.get("score_color")
            if score_color:
                msg += f"  • 🎨 Score-Color: ✅ {score_color.get('trigger_name', '')} ({score_color.get('confidence', 0):.0f}%)\n"
            else:
                msg += "  • 🎨 Score-Color: ❌ Sin trigger\n"
            
            # 5. Memory-4 (58.8% accuracy real)
            mem4 = all_strategies.get("memory_4")
            if mem4:
                msg += f"  • 🧠 Memory-4: ✅ '{mem4.get('pattern', '')}' → {mem4.get('predicted', '')} ({mem4.get('confidence', 0):.0f}%)\n"
            else:
                msg += "  • 🧠 Memory-4: ❌ Sin patrón\n"
            
            # 6. Score-Diff (54.1% accuracy real)
            score_diff = all_strategies.get("score_diff")
            if score_diff:
                msg += f"  • 📐 Score-Diff: ✅ → {score_diff.get('predicted', '')} ({score_diff.get('confidence', 0):.0f}%)\n"
            else:
                msg += "  • 📐 Score-Diff: ❌ Sin señal\n"
            
            msg += f"""
━━━━━━━━━━━━━━━━━━━━
👁️ ANÁLISIS PROFUNDO DE MESA


"""
            
            if deep_analysis:
                momentum = deep_analysis.get("momentum", {})
                msg += f"➡️ Momento: {momentum.get('direction', 'NEUTRAL')}\n"
                msg += f"📊 Volatilidad: {deep_analysis.get('volatility', 'N/A')}\n"
                msg += f"🔄 Dominancia: {deep_analysis.get('dominance', 'N/A')}\n"
            
            msg += f"""
━━━━━━━━━━━━━━━━━━━━
📊 MÉTRICAS AVANZADAS

"""
            
            if deep_analysis:
                active_streak = deep_analysis.get("active_streak")
                if active_streak:
                    msg += f"🔥 Racha activa: {active_streak}\n"
                
                tie_pct = deep_analysis.get("tie_pct", 0)
                msg += f"🟢 Empates: {deep_analysis.get('tie_status', 'NORMAL')} ({tie_pct:.1f}% - {deep_analysis.get('tie_count', 0)}/{deep_analysis.get('player_count', 0) + deep_analysis.get('banker_count', 0)})\n"
                
                hot_numbers = deep_analysis.get("hot_numbers", [])
                if hot_numbers:
                    hot_str = ", ".join([f"{n[0]} {n[1]*100/(deep_analysis.get('player_count', 1)+deep_analysis.get('banker_count', 1)):.0f}%" for n in hot_numbers])
                    msg += f"🔥 Números calientes: {hot_str}\n"
                
                changes = deep_analysis.get("changes", 0)
                msg += f"🎢 Volatilidad: {deep_analysis.get('volatility', 'N/A')} ({changes} cambios en 20 rondas)\n"
            
            msg += f"""
🎴 Zapato: {shoe_cards_out}/416 ({shoe_pct:.0f}%)
📊 Precisión Global: {accuracy:.1f}% ({total_correct}/{total_predictions})"""
            
            result = await self.send_message(msg)
            return result
        except Exception as e:
            logger.error(f"❌ Error en send_comprehensive_prediction: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
