import schedule
import time
from loguru import logger
from config import DATABASE_URL, TELEGRAM_BOT_TOKEN
from src.collectors.db_handler import criar_tabelas
from src.collectors.football_collector import coletar_jogos_do_dia
from src.collectors.odds_collector import coletar_odds


logger.add("logs/bertuccia.log", rotation="1 week")


def pipeline_coleta():
    """Executa a coleta completa: jogos + odds."""
    logger.info("=" * 50)
    logger.info("Iniciando pipeline de coleta...")
    coletar_jogos_do_dia()
    coletar_odds()
    logger.info("Pipeline concluída.")
    logger.info("=" * 50)


def main():
    logger.info("BertuccIA iniciando...")

    if not DATABASE_URL:
        logger.error("DATABASE_URL não configurada!")
        return

    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN não configurado!")
        return

    logger.success("Configurações carregadas.")

    # Cria as tabelas no Supabase na primeira execução
    criar_tabelas()

    # Executa imediatamente ao iniciar
    pipeline_coleta()

    # Agenda coleta automática todo dia às 09:00 e 18:00
    schedule.every().day.at("09:00").do(pipeline_coleta)
    schedule.every().day.at("18:00").do(pipeline_coleta)

    logger.info("Agendamento ativo: coletas às 09:00 e 18:00 diariamente.")

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
