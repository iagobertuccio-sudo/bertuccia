import requests
from datetime import date
from loguru import logger
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from sqlalchemy import text
from src.collectors.db_handler import engine


TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

EMOJI_RISCO = {
    "Baixo": "🟢",
    "Medio": "🟡",
    "Alto":  "🔴",
}

EMOJI_MERCADO = {
    "Vitória Casa":  "🏠",
    "Empate":        "🤝",
    "Vitória Fora":  "✈️",
    "Over 2.5 Gols": "⚽",
    "BTTS":          "🎯",
}


def _get_emoji_mercado(mercado: str) -> str:
    for key, emoji in EMOJI_MERCADO.items():
        if key.lower() in mercado.lower():
            return emoji
    return "📌"


def formatar_tip(tip: dict, probs: dict) -> str:
    """Formata a mensagem da tip para o Telegram."""
    emoji_risco   = EMOJI_RISCO.get(tip["nivel_risco"], "⚪")
    emoji_mercado = _get_emoji_mercado(tip["mercado_sugerido"])

    # Barra de confiança visual
    ev = tip["ev_percentual"]
    barras = min(int(ev / 2), 10)
    barra_visual = "█" * barras + "░" * (10 - barras)

    msg = f"""
🤖 *BertuccIA — Tip Identificada*
━━━━━━━━━━━━━━━━━━━━━━
⚽ *{tip['partida']}*
🏆 {tip['competicao']}
📅 {tip['data_analise']}

{emoji_mercado} *Mercado:* {tip['mercado_sugerido']}
💰 *Odd Sugerida:* `{tip['odd_sugerida']}`
📐 *Odd Justa (modelo):* `{tip['odd_justa']}`
📈 *Valor Esperado (+EV):* `+{tip['ev_percentual']}%`
🎲 *Stake:* `{tip['stake_unidades']}U`
{emoji_risco} *Risco:* {tip['nivel_risco']}

📊 *Probabilidades (Poisson):*
├ 🏠 Casa:   `{probs['prob_casa']*100:.1f}%`
├ 🤝 Empate: `{probs['prob_empate']*100:.1f}%`
├ ✈️ Fora:   `{probs['prob_fora']*100:.1f}%`
├ ⚽ Over2.5:`{probs['prob_over25']*100:.1f}%`
└ 🎯 BTTS:   `{probs['prob_btts']*100:.1f}%`

🔥 Confiança: [{barra_visual}] {ev:.1f}%
━━━━━━━━━━━━━━━━━━━━━━
⚠️ _Aposte com responsabilidade. Gestão de banca é fundamental._
""".strip()

    return msg


def enviar_mensagem(texto: str) -> bool:
    """Envia uma mensagem ao grupo do Telegram."""
    if not TELEGRAM_CHAT_ID:
        logger.warning("TELEGRAM_CHAT_ID não configurado — mensagem não enviada.")
        return False
    try:
        resp = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id":    TELEGRAM_CHAT_ID,
                "text":       texto,
                "parse_mode": "Markdown",
            },
            timeout=15
        )
        resp.raise_for_status()
        logger.success("Mensagem enviada ao Telegram.")
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar Telegram: {e}")
        return False


def enviar_tip_imediata(tip: dict, probs: dict):
    """Envia alerta imediato quando uma tip é identificada."""
    msg = formatar_tip(tip, probs)
    enviado = enviar_mensagem(msg)

    if enviado:
        # Marca como enviado no banco
        with engine.connect() as conn:
            conn.execute(text("""
                UPDATE tips SET enviado_telegram = TRUE
                WHERE fixture_id = :fixture_id
                  AND mercado_sugerido = :mercado
            """), {
                "fixture_id": tip["fixture_id"],
                "mercado":    tip["mercado_sugerido"],
            })
            conn.commit()


def enviar_resumo_diario():
    """Envia resumo das tips do dia às 10h."""
    hoje = date.today().isoformat()

    with engine.connect() as conn:
        resultado = conn.execute(text("""
            SELECT partida, competicao, mercado_sugerido,
                   odd_sugerida, stake_unidades, nivel_risco, ev_percentual
            FROM tips
            WHERE data_analise = :hoje
            ORDER BY ev_percentual DESC
        """), {"hoje": hoje})
        tips = [dict(row._mapping) for row in resultado]

    if not tips:
        enviar_mensagem(
            f"📋 *Resumo BertuccIA — {hoje}*\n\n"
            "Nenhuma oportunidade +EV identificada hoje.\n"
            "O sistema continua monitorando... 🔍"
        )
        return

    linhas = [f"📋 *Resumo BertuccIA — {hoje}*\n{'━'*22}"]
    for i, t in enumerate(tips, 1):
        emoji = EMOJI_RISCO.get(t["nivel_risco"], "⚪")
        linhas.append(
            f"\n*{i}. {t['partida']}*\n"
            f"🏆 {t['competicao']}\n"
            f"📌 {t['mercado_sugerido']}\n"
            f"💰 Odd: `{t['odd_sugerida']}` | "
            f"🎲 Stake: `{t['stake_unidades']}U` | "
            f"{emoji} {t['nivel_risco']}\n"
            f"📈 EV: `+{t['ev_percentual']}%`"
        )

    linhas.append(f"\n{'━'*22}")
    linhas.append(f"_Total: {len(tips)} tip(s) identificada(s) hoje_")

    enviar_mensagem("\n".join(linhas))
    logger.success(f"Resumo diário enviado — {len(tips)} tip(s).")
