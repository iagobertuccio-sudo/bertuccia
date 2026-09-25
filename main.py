import schedule
import time
from loguru import logger
from config import DATABASE_URL, TELEGRAM_BOT_TOKEN
from src.collectors.db_handler import criar_tabelas
from src.collectors.football_collector import coletar_jogos_do_dia
from src.collectors.odds_collector import coletar_odds
from src.collectors.stats_collector import criar_tabela_stats
from src.engine.tip_generator import gerar_tips_do_dia
from src.messaging.telegram_sender import enviar_resumo_diario

logger.add("logs/bertuccia.log", rotation="1 week")


def pipeline_coleta():
    """Coleta jogos + odds + stats e roda a engine +EV."""
    logger.info("=" * 50)
    logger.info("Iniciando pipeline completa...")
    coletar_jogos_do_dia()
    coletar_odds()
    gerar_tips_do_dia()
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

    # Cria todas as tabelas
    criar_tabelas()
    criar_tabela_stats()

    # Executa imediatamente ao iniciar
    pipeline_coleta()

    # Resumo diário às 10:00
    schedule.every().day.at("10:00").do(enviar_resumo_diario)

    # Coleta + análise às 09:00 e 18:00
    schedule.every().day.at("09:00").do(pipeline_coleta)
    schedule.every().day.at("18:00").do(pipeline_coleta)

    logger.info("Agendamentos ativos: 09:00, 10:00 (resumo), 18:00")

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
