import requests
from loguru import logger
from config import ODDS_API_KEY
from src.collectors.db_handler import salvar_odd


# Mapeamento das ligas para o formato da The Odds API
LIGAS_ODDS = {
    "Brasileirão Série A": "soccer_brazil_campeonato",
    "Brasileirão Série B": "soccer_brazil_serie_b",
    "Premier League":      "soccer_epl",
    "Champions League":    "soccer_uefa_champs_league",
    "Bundesliga":          "soccer_germany_bundesliga",
}

BASE_URL  = "https://api.the-odds-api.com/v4/sports"
MERCADOS  = "h2h"          # 1X2 (resultado final)
REGIOES   = "eu"           # odds europeias
BOOKMAKER = "betfair"      # bookmaker de referência


def coletar_odds():
    """Busca odds das ligas monitoradas e salva no banco."""
    total_salvos = 0

    for nome_liga, sport_key in LIGAS_ODDS.items():
        logger.info(f"Coletando odds — {nome_liga}")

        try:
            resp = requests.get(
                f"{BASE_URL}/{sport_key}/odds",
                params={
                    "apiKey":  ODDS_API_KEY,
                    "regions": REGIOES,
                    "markets": MERCADOS,
                    "oddsFormat": "decimal",
                },
                timeout=15
            )
            resp.raise_for_status()
            jogos = resp.json()

            logger.info(f"  → {len(jogos)} jogo(s) com odds disponíveis")

            for jogo in jogos:
                fixture_id = abs(hash(jogo["id"])) % (10**9)

                for bookmaker in jogo.get("bookmakers", []):
                    for market in bookmaker.get("markets", []):
                        if market["key"] != "h2h":
                            continue

                        outcomes = market["outcomes"]
                        odd_casa = odd_empate = odd_fora = None

                        for o in outcomes:
                            if o["name"] == jogo["home_team"]:
                                odd_casa = o["price"]
                            elif o["name"] == jogo["away_team"]:
                                odd_fora = o["price"]
                            else:
                                odd_empate = o["price"]

                        odd = {
                            "fixture_id": fixture_id,
                            "bookmaker":  bookmaker["title"],
                            "mercado":    "1X2",
                            "odd_casa":   odd_casa,
                            "odd_empate": odd_empate,
                            "odd_fora":   odd_fora,
                        }
                        salvar_odd(odd)
                        total_salvos += 1

        except Exception as e:
            logger.error(f"Erro ao coletar odds de {nome_liga}: {e}")

    logger.success(f"Odds coletadas — {total_salvos} registro(s) salvos.")
    return total_salvos


if __name__ == "__main__":
    coletar_odds()
