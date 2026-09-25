import math
from loguru import logger


def fatorial(n: int) -> int:
    return math.factorial(n)


def poisson_prob(lam: float, k: int) -> float:
    """P(X=k) para distribuição de Poisson com média lam."""
    if lam <= 0:
        return 0.0
    return (math.exp(-lam) * (lam ** k)) / fatorial(k)


def calcular_matriz_gols(
    ataque_casa: float,
    defesa_casa: float,
    ataque_fora: float,
    defesa_fora: float,
    media_liga:  float = 1.35,
    max_gols:    int   = 6,
) -> list[list[float]]:
    """
    Retorna matriz [i][j] = P(casa=i, fora=j).
    lambda_casa = ataque_casa * defesa_fora * media_liga
    lambda_fora = ataque_fora * defesa_casa * media_liga
    """
    lam_casa = ataque_casa * defesa_fora * media_liga
    lam_fora = ataque_fora * defesa_casa * media_liga

    matriz = []
    for i in range(max_gols + 1):
        linha = []
        for j in range(max_gols + 1):
            p = poisson_prob(lam_casa, i) * poisson_prob(lam_fora, j)
            linha.append(p)
        matriz.append(linha)

    return matriz


def calcular_probabilidades(
    gols_marcados_casa: float,
    gols_sofridos_casa: float,
    gols_marcados_fora: float,
    gols_sofridos_fora: float,
    media_liga: float = 1.35,
) -> dict:
    """
    Calcula probabilidades de vitória casa, empate e vitória fora
    usando modelo de Poisson bivariado.
    Retorna também probabilidades de Over/Under e BTTS.
    """
    # Força relativa (normalizada pela média da liga)
    ataque_casa = gols_marcados_casa / media_liga
    defesa_casa = gols_sofridos_casa / media_liga
    ataque_fora = gols_marcados_fora / media_liga
    defesa_fora = gols_sofridos_fora / media_liga

    matriz = calcular_matriz_gols(
        ataque_casa, defesa_casa,
        ataque_fora, defesa_fora,
        media_liga
    )

    prob_casa   = 0.0
    prob_empate = 0.0
    prob_fora   = 0.0
    prob_btts   = 0.0
    prob_over25 = 0.0

    max_gols = len(matriz) - 1

    for i in range(max_gols + 1):
        for j in range(max_gols + 1):
            p = matriz[i][j]
            if i > j:
                prob_casa   += p
            elif i == j:
                prob_empate += p
            else:
                prob_fora   += p

            if i > 0 and j > 0:
                prob_btts += p

            if i + j > 2:
                prob_over25 += p

    # Normaliza para garantir soma = 1
    total = prob_casa + prob_empate + prob_fora
    if total > 0:
        prob_casa   /= total
        prob_empate /= total
        prob_fora   /= total

    resultado = {
        "prob_casa":    round(prob_casa,   4),
        "prob_empate":  round(prob_empate, 4),
        "prob_fora":    round(prob_fora,   4),
        "odd_justa_casa":   round(1 / prob_casa,   2) if prob_casa   > 0 else 99,
        "odd_justa_empate": round(1 / prob_empate, 2) if prob_empate > 0 else 99,
        "odd_justa_fora":   round(1 / prob_fora,   2) if prob_fora   > 0 else 99,
        "prob_btts":    round(prob_btts,   4),
        "prob_over25":  round(prob_over25, 4),
    }

    logger.debug(
        f"Poisson → Casa:{resultado['prob_casa']:.1%} "
        f"Emp:{resultado['prob_empate']:.1%} "
        f"Fora:{resultado['prob_fora']:.1%}"
    )
    return resultado
