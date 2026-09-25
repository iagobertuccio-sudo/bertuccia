import requests
from loguru import logger
from config import API_FOOTBALL_KEY
from src.collectors.db_handler import engine
from sqlalchemy import text

BASE_URL = "https://v3.football.api-sports.io"
HEADERS  = {"x-apisports-key": API_FOOTBALL_KEY}

LIGAS = {
    "Brasileirão Série A": {"id": 71,  "season": 2025},
    "Premier League":      {"id": 39,  "season": 2025},
    "Champions League":    {"id": 2,   "season": 2025},
}


def criar_tabela_stats():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS stats_times (
                id              SERIAL PRIMARY KEY,
                team_id         INTEGER,
                team_name       VARCHAR(100),
                liga            VARCHAR(100),
                temporada       INTEGER,
                jogos           INTEGER,
                vitorias        INTEGER,
                empates         INTEGER,
                derrotas        INTEGER,
                gols_marcados   FLOAT,
                gols_sofridos   FLOAT,
                xg_marcados     FLOAT,
                xg_sofridos     FLOAT,
                posse_media     FLOAT,
                chutes_gol      FLOAT,
                escanteios      FLOAT,
                cartoes_amarelos FLOAT,
                cartoes_vermelhos FLOAT,
                btts_pct        FLOAT,
                over25_pct      FLOAT,
                atualizado_em   TIMESTAMP DEFAULT NOW(),
                UNIQUE(team_id, liga, temporada)
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS h2h (
                id              SERIAL PRIMARY KEY,
                team_home_id    INTEGER,
                team_away_id    INTEGER,
                fixture_id      INTEGER,
                data_jogo       TIMESTAMP,
                gols_home       INTEGER,
                gols_away       INTEGER,
                vencedor        VARCHAR(10),
                criado_em       TIMESTAMP DEFAULT NOW(),
                UNIQUE(fixture_id)
            )
        """))
        conn.commit()
    logger.success("Tabelas stats_times e h2h verificadas.")


def coletar_stats_time(team_id: int, liga_id: int, liga_nome: str, season: int):
    """Coleta estatísticas agregadas de um time na temporada."""
    try:
        resp = requests.get(
            f"{BASE_URL}/teams/statistics",
            headers=HEADERS,
            params={"team": team_id, "league": liga_id, "season": season},
            timeout=15
        )
        resp.raise_for_status()
        d = resp.json().get("response", {})
        if not d:
            return

        fixtures = d.get("fixtures", {})
        goals    = d.get("goals", {})
        cards    = d.get("cards", {})

        jogos    = fixtures.get("played", {}).get("total", 0) or 0
        vitorias = fixtures.get("wins",   {}).get("total", 0) or 0
        empates  = fixtures.get("draws",  {}).get("total", 0) or 0
        derrotas = fixtures.get("loses",  {}).get("total", 0) or 0

        gm = goals.get("for",     {}).get("total", {}).get("total", 0) or 0
        gs = goals.get("against", {}).get("total", {}).get("total", 0) or 0

        gm_media = round(gm / jogos, 2) if jogos else 0
        gs_media = round(gs / jogos, 2) if jogos else 0

        # BTTS e Over 2.5 — calculados a partir dos totais
        btts  = d.get("clean_sheet", {}).get("total", 0) or 0
        btts_pct  = round((1 - btts / jogos) * 100, 1) if jogos else 0
        over25_pct = round(
            (d.get("goals", {})
               .get("for", {})
               .get("minute", {})
               .get("76-90", {})
               .get("total", 0) or 0) / max(jogos, 1) * 100, 1
        )

        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO stats_times (
                    team_id, team_name, liga, temporada,
                    jogos, vitorias, empates, derrotas,
                    gols_marcados, gols_sofridos,
                    xg_marcados, xg_sofridos,
                    btts_pct, over25_pct
                ) VALUES (
                    :team_id, :team_name, :liga, :temporada,
                    :jogos, :vitorias, :empates, :derrotas,
                    :gols_marcados, :gols_sofridos,
                    :xg_marcados, :xg_sofridos,
                    :btts_pct, :over25_pct
                )
                ON CONFLICT (team_id, liga, temporada) DO UPDATE SET
                    jogos          = EXCLUDED.jogos,
                    vitorias       = EXCLUDED.vitorias,
                    empates        = EXCLUDED.empates,
                    derrotas       = EXCLUDED.derrotas,
                    gols_marcados  = EXCLUDED.gols_marcados,
                    gols_sofridos  = EXCLUDED.gols_sofridos,
                    btts_pct       = EXCLUDED.btts_pct,
                    over25_pct     = EXCLUDED.over25_pct,
                    atualizado_em  = NOW()
            """), {
                "team_id":      team_id,
                "team_name":    d.get("team", {}).get("name", ""),
                "liga":         liga_nome,
                "temporada":    season,
                "jogos":        jogos,
                "vitorias":     vitorias,
                "empates":      empates,
                "derrotas":     derrotas,
                "gols_marcados": gm_media,
                "gols_sofridos": gs_media,
                "xg_marcados":  0.0,
                "xg_sofridos":  0.0,
                "btts_pct":     btts_pct,
                "over25_pct":   over25_pct,
            })
            conn.commit()
        logger.debug(f"Stats salvas: {d.get('team', {}).get('name', team_id)}")

    except Exception as e:
        logger.error(f"Erro ao coletar stats do time {team_id}: {e}")


def coletar_h2h(team1_id: int, team2_id: int, last: int = 10):
    """Coleta últimos confrontos diretos entre dois times."""
    try:
        resp = requests.get(
            f"{BASE_URL}/fixtures/headtohead",
            headers=HEADERS,
            params={"h2h": f"{team1_id}-{team2_id}", "last": last},
            timeout=15
        )
        resp.raise_for_status()
        jogos = resp.json().get("response", [])

        with engine.connect() as conn:
            for j in jogos:
                fx     = j["fixture"]
                teams  = j["teams"]
                goals  = j["goals"]
                home_w = teams["home"].get("winner")
                vencedor = "home" if home_w else ("away" if home_w is False else "draw")

                conn.execute(text("""
                    INSERT INTO h2h (
                        team_home_id, team_away_id, fixture_id,
                        data_jogo, gols_home, gols_away, vencedor
                    ) VALUES (
                        :team_home_id, :team_away_id, :fixture_id,
                        :data_jogo, :gols_home, :gols_away, :vencedor
                    )
                    ON CONFLICT (fixture_id) DO NOTHING
                """), {
                    "team_home_id": teams["home"]["id"],
                    "team_away_id": teams["away"]["id"],
                    "fixture_id":   fx["id"],
                    "data_jogo":    fx["date"],
                    "gols_home":    goals["home"] or 0,
                    "gols_away":    goals["away"] or 0,
                    "vencedor":     vencedor,
                })
            conn.commit()
        logger.debug(f"H2H salvo: {team1_id} vs {team2_id} — {len(jogos)} jogos")

    except Exception as e:
        logger.error(f"Erro ao coletar H2H {team1_id} vs {team2_id}: {e}")
