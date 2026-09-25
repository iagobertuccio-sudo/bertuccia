from loguru import logger


# Thresholds de valor esperado
EV_CONSERVADOR = 0.10   # 10%+ de vantagem
EV_MODERADO    = 0.05   # 5%+
EV_AGRESSIVO   = 0.03   # 3%+


def calcular_ev(prob_real: float, odd_mercado: float) -> float:
    """
    EV = (prob_real * odd_mercado) - 1
    EV > 0 significa aposta com valor positivo.
    """
    return round((prob_real * odd_mercado) - 1, 4)


def classificar_risco(ev: float) -> str | None:
    """Retorna o nível de risco com base no EV calculado."""
    if ev >= EV_CONSERVADOR:
        return "Baixo"
    elif ev >= EV_MODERADO:
        return "Medio"
    elif ev >= EV_AGRESSIVO:
        return "Alto"
    return None  # Sem valor — não entra


def calcular_stake(ev: float, nivel_risco: str) -> float:
    """
    Kelly fracionado simplificado por nível de risco.
    Retorna stake em Unidades (máx 2U).
    """
    if nivel_risco == "Baixo":
        return min(round(ev * 10, 1), 2.0)
    elif nivel_risco == "Medio":
        return min(round(ev * 7,  1), 1.5)
    elif nivel_risco == "Alto":
        return min(round(ev * 5,  1), 1.0)
    return 0.5


def analisar_mercados(probs: dict, odds_mercado: dict) -> list[dict]:
    """
    Analisa todos os mercados disponíveis e retorna
    lista de oportunidades com valor positivo (+EV).

    probs = {
        "prob_casa": 0.55, "prob_empate": 0.25, "prob_fora": 0.20,
        "prob_btts": 0.62, "prob_over25": 0.58
    }
    odds_mercado = {
        "odd_casa": 1.85, "odd_empate": 3.40, "odd_fora": 4.50,
        "odd_over25": 1.90, "odd_btts_sim": 1.75
    }
    """
    oportunidades = []

    mercados = [
        {
            "nome":        "Vitória Casa (1X2)",
            "prob":        probs.get("prob_casa", 0),
            "odd_mercado": odds_mercado.get("odd_casa", 0),
            "odd_justa":   probs.get("odd_justa_casa", 99),
        },
        {
            "nome":        "Empate (1X2)",
            "prob":        probs.get("prob_empate", 0),
            "odd_mercado": odds_mercado.get("odd_empate", 0),
            "odd_justa":   probs.get("odd_justa_empate", 99),
        },
        {
            "nome":        "Vitória Fora (1X2)",
            "prob":        probs.get("prob_fora", 0),
            "odd_mercado": odds_mercado.get("odd_fora", 0),
            "odd_justa":   probs.get("odd_justa_fora", 99),
        },
        {
            "nome":        "Over 2.5 Gols",
            "prob":        probs.get("prob_over25", 0),
            "odd_mercado": odds_mercado.get("odd_over25", 0),
            "odd_justa":   round(1 / probs["prob_over25"], 2) if probs.get("prob_over25", 0) > 0 else 99,
        },
        {
            "nome":        "BTTS - Ambos Marcam",
            "prob":        probs.get("prob_btts", 0),
            "odd_mercado": odds_mercado.get("odd_btts_sim", 0),
            "odd_justa":   round(1 / probs["prob_btts"], 2) if probs.get("prob_btts", 0) > 0 else 99,
        },
    ]

    for m in mercados:
        if m["odd_mercado"] <= 1.0 or m["prob"] <= 0:
            continue

        ev           = calcular_ev(m["prob"], m["odd_mercado"])
        nivel_risco  = classificar_risco(ev)

        if nivel_risco is None:
            continue

        stake = calcular_stake(ev, nivel_risco)

        oportunidade = {
            "mercado_sugerido": m["nome"],
            "odd_sugerida":     m["odd_mercado"],
            "odd_justa":        m["odd_justa"],
            "ev_percentual":    round(ev * 100, 2),
            "stake_unidades":   stake,
            "nivel_risco":      nivel_risco,
        }
        oportunidades.append(oportunidade)
        logger.info(
            f"  +EV encontrado → {m['nome']} | "
            f"Odd: {m['odd_mercado']} | Justa: {m['odd_justa']} | "
            f"EV: {ev*100:.1f}% | Risco: {nivel_risco}"
        )

    return oportunidades
