import requests
from datetime import datetime, date
from loguru import logger
from config import API_FOOTBALL_KEY
from src.collectors.db_handler import salvar_jogo


# IDs das ligas monitoradas
LIGAS = {
    "Brasileirão Série A": {"id": 71, "season": 2026},
    "Brasileirão Série B": {"id": 72, "season": 2026},
    "Premier League":      {"id": 39, "season": 2025},
    "Champions League":    {"id": 2,  "season": 2025},
    "Bundesliga":          {"id": 78, "season": 2025},

}

BASE_URL = "https://v3.football.api-sports.io"
HEADERS  = {
    "x-apisports-key": API_FOOTBALL_KEY
}


def coletar_jogos_do_dia():
    """Busca todos os jogos do dia nas ligas monitoradas e salva no banco."""
    hoje = date.today().strftime("%Y-%m-%d")
    total_salvos = 0

    for nome_liga, liga_id in LIGAS.items():
        logger.info(f"Coletando jogos de hoje — {nome_liga} (ID {liga_id})")

        try:
            resp = requests.get(
                f"{BASE_URL}/fixtures",
                headers=HEADERS,
                params={"league": liga_id, "date": hoje, "season": 2025},
                timeout=15
            )
            resp.raise_for_status()
            dados = resp.json()

            fixtures = dados.get("response", [])
            logger.info(f"  → {len(fixtures)} jogo(s) encontrado(s)")

            for f in fixtures:
                fixture  = f["fixture"]
                teams    = f["teams"]
                goals    = f["goals"]
                league   = f["league"]

                jogo = {
                    "fixture_id": fixture["id"],
                    "liga":       nome_liga,
                    "liga_id":    liga_id,
                    "temporada":  league["season"],
                    "data_jogo":  fixture["date"],
                    "time_casa":  teams["home"]["name"],
                    "time_fora":  teams["away"]["name"],
                    "status":     fixture["status"]["short"],
                    "gols_casa":  goals["home"],
                    "gols_fora":  goals["away"],
                }
                salvar_jogo(jogo)
                total_salvos += 1
                logger.debug(f"  Salvo: {jogo['time_casa']} x {jogo['time_fora']}")

        except Exception as e:
            logger.error(f"Erro ao coletar {nome_liga}: {e}")

    logger.success(f"Coleta concluída — {total_salvos} jogo(s) salvos no Supabase.")
    return total_salvos


if __name__ == "__main__":
    coletar_jogos_do_dia()
