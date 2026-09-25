from datetime import date
from loguru import logger
from sqlalchemy import text
from src.collectors.db_handler import engine, salvar_tip
from src.engine.poisson_model import calcular_probabilidades
from src.engine.ev_calculator import analisar_mercados
from src.messaging.telegram_sender import enviar_tip_imediata


def buscar_jogos_do_dia() -> list[dict]:
    with engine.connect() as conn:
        resultado = conn.execute(text("""
            SELECT fixture_id, liga, time_casa, time_fora, data_jogo
            FROM jogos
            WHERE DATE(data_jogo) = CURRENT_DATE
              AND status = 'NS'
            ORDER BY data_jogo
        """))
        return [dict(row._mapping) for row in resultado]


def buscar_stats_time(team_name: str, liga: str) -> dict | None:
    with engine.connect() as conn:
        resultado = conn.execute(text("""
            SELECT * FROM stats_times
            WHERE team_name ILIKE :nome AND liga = :liga
            ORDER BY atualizado_em DESC
            LIMIT 1
        """), {"nome": f"%{team_name}%", "liga": liga})
        row = resultado.fetchone()
        return dict(row._mapping) if row else None


def buscar_odds_jogo(fixture_id: int) -> dict:
    """Busca as melhores odds disponíveis para o fixture."""
    with engine.connect() as conn:
        resultado = conn.execute(text("""
            SELECT
                MAX(odd_casa)   AS odd_casa,
                MAX(odd_empate) AS odd_empate,
                MAX(odd_fora)   AS odd_fora
            FROM odds
            WHERE fixture_id = :fixture_id
              AND mercado = '1X2'
        """), {"fixture_id": fixture_id})
        row = resultado.fetchone()
        if row:
            return {
                "odd_casa":    row.odd_casa   or 0,
                "odd_empate":  row.odd_empate or 0,
                "odd_fora":    row.odd_fora   or 0,
                "odd_over25":  1.90,  # fallback — será coletado na Fase seguinte
                "odd_btts_sim": 1.75, # fallback
            }
    return {}


def buscar_h2h_resumo(team_casa: str, team_fora: str) -> dict:
    """Retorna resumo do H2H: % vitórias casa, empates, fora."""
    with engine.connect() as conn:
        resultado = conn.execute(text("""
            SELECT vencedor, COUNT(*) as total
            FROM h2h
            WHERE (team_home_id IN (
                SELECT team_id FROM stats_times WHERE team_name ILIKE :casa
            ))
            GROUP BY vencedor
        """), {"casa": f"%{team_casa}%"})
        rows = resultado.fetchall()

    resumo = {"home": 0, "draw": 0, "away": 0, "total": 0}
    for row in rows:
        resumo[row.vencedor] = row.total
        resumo["total"] += row.total

    return resumo


def gerar_tips_do_dia() -> list[dict]:
    """Pipeline principal: busca jogos → calcula +EV → salva e envia tips."""
    jogos     = buscar_jogos_do_dia()
    tips_geradas = []

    if not jogos:
        logger.info("Nenhum jogo encontrado para hoje.")
        return []

    logger.info(f"{len(jogos)} jogo(s) para analisar hoje.")

    for jogo in jogos:
        fixture_id = jogo["fixture_id"]
        liga       = jogo["liga"]
        time_casa  = jogo["time_casa"]
        time_fora  = jogo["time_fora"]
        partida    = f"{time_casa} vs {time_fora}"

        logger.info(f"Analisando: {partida} [{liga}]")

        stats_casa = buscar_stats_time(time_casa, liga)
        stats_fora = buscar_stats_time(time_fora, liga)

        if not stats_casa or not stats_fora:
            logger.warning(f"  Stats insuficientes para {partida} — pulando.")
            continue

        # Modelo de Poisson
        probs = calcular_probabilidades(
            gols_marcados_casa = stats_casa["gols_marcados"],
            gols_sofridos_casa = stats_casa["gols_sofridos"],
            gols_marcados_fora = stats_fora["gols_marcados"],
            gols_sofridos_fora = stats_fora["gols_sofridos"],
        )

        # Odds do mercado
        odds = buscar_odds_jogo(fixture_id)
        if not odds:
            logger.warning(f"  Sem odds para {partida} — pulando.")
            continue

        # Detecta oportunidades +EV
        oportunidades = analisar_mercados(probs, odds)

        if not oportunidades:
            logger.info(f"  Sem valor em {partida}.")
            continue

        # Ordena por EV decrescente e pega a melhor
        oportunidades.sort(key=lambda x: x["ev_percentual"], reverse=True)
        melhor = oportunidades[0]

        tip = {
            "fixture_id":       fixture_id,
            "partida":          partida,
            "competicao":       liga,
            "data_analise":     date.today().isoformat(),
            "mercado_sugerido": melhor["mercado_sugerido"],
            "odd_sugerida":     melhor["odd_sugerida"],
            "odd_justa":        melhor["odd_justa"],
            "ev_percentual":    melhor["ev_percentual"],
            "stake_unidades":   melhor["stake_unidades"],
            "nivel_risco":      melhor["nivel_risco"],
        }

        salvar_tip(tip)
        tips_geradas.append(tip)

        # Envia alerta imediato no Telegram
        enviar_tip_imediata(tip, probs)

    logger.success(f"{len(tips_geradas)} tip(s) gerada(s) e enviada(s).")
    return tips_geradas
