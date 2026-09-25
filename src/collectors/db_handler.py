from sqlalchemy import create_engine, text
from loguru import logger
from config import DATABASE_URL


engine = create_engine(DATABASE_URL)


def criar_tabelas():
    """Cria as tabelas no Supabase se não existirem."""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS jogos (
                id              SERIAL PRIMARY KEY,
                fixture_id      INTEGER UNIQUE,
                liga            VARCHAR(100),
                liga_id         INTEGER,
                temporada       INTEGER,
                data_jogo       TIMESTAMP,
                time_casa       VARCHAR(100),
                time_fora       VARCHAR(100),
                status          VARCHAR(50),
                gols_casa       INTEGER,
                gols_fora       INTEGER,
                criado_em       TIMESTAMP DEFAULT NOW()
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS odds (
                id              SERIAL PRIMARY KEY,
                fixture_id      INTEGER,
                bookmaker       VARCHAR(100),
                mercado         VARCHAR(100),
                odd_casa        FLOAT,
                odd_empate      FLOAT,
                odd_fora        FLOAT,
                coletado_em     TIMESTAMP DEFAULT NOW(),
                UNIQUE(fixture_id, bookmaker, mercado)
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tips (
                id              SERIAL PRIMARY KEY,
                fixture_id      INTEGER,
                partida         VARCHAR(200),
                competicao      VARCHAR(100),
                data_analise    DATE,
                mercado_sugerido VARCHAR(200),
                odd_sugerida    FLOAT,
                odd_justa       FLOAT,
                ev_percentual   FLOAT,
                stake_unidades  FLOAT,
                nivel_risco     VARCHAR(20),
                resultado       VARCHAR(10),
                enviado_telegram BOOLEAN DEFAULT FALSE,
                criado_em       TIMESTAMP DEFAULT NOW()
            )
        """))

        conn.commit()
    logger.success("Tabelas verificadas/criadas no Supabase.")


def salvar_jogo(jogo: dict):
    """Insere ou atualiza um jogo no banco."""
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO jogos (
                fixture_id, liga, liga_id, temporada, data_jogo,
                time_casa, time_fora, status, gols_casa, gols_fora
            ) VALUES (
                :fixture_id, :liga, :liga_id, :temporada, :data_jogo,
                :time_casa, :time_fora, :status, :gols_casa, :gols_fora
            )
            ON CONFLICT (fixture_id) DO UPDATE SET
                status    = EXCLUDED.status,
                gols_casa = EXCLUDED.gols_casa,
                gols_fora = EXCLUDED.gols_fora
        """), jogo)
        conn.commit()


def salvar_odd(odd: dict):
    """Insere ou atualiza uma odd no banco."""
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO odds (
                fixture_id, bookmaker, mercado,
                odd_casa, odd_empate, odd_fora
            ) VALUES (
                :fixture_id, :bookmaker, :mercado,
                :odd_casa, :odd_empate, :odd_fora
            )
            ON CONFLICT (fixture_id, bookmaker, mercado) DO UPDATE SET
                odd_casa   = EXCLUDED.odd_casa,
                odd_empate = EXCLUDED.odd_empate,
                odd_fora   = EXCLUDED.odd_fora,
                coletado_em = NOW()
        """), odd)
        conn.commit()


def salvar_tip(tip: dict):
    """Salva uma tip gerada pelo engine."""
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO tips (
                fixture_id, partida, competicao, data_analise,
                mercado_sugerido, odd_sugerida, odd_justa,
                ev_percentual, stake_unidades, nivel_risco
            ) VALUES (
                :fixture_id, :partida, :competicao, :data_analise,
                :mercado_sugerido, :odd_sugerida, :odd_justa,
                :ev_percentual, :stake_unidades, :nivel_risco
            )
        """), tip)
        conn.commit()
    logger.success(f"Tip salva: {tip['partida']} | {tip['mercado_sugerido']}")
