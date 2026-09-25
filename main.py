from loguru import logger
from config import DATABASE_URL, TELEGRAM_BOT_TOKEN

logger.add("logs/bertuccia.log", rotation="1 week")

def main():
    logger.info("BertuccIA iniciando...")

    if not DATABASE_URL:
        logger.error("DATABASE_URL não configurada!")
        return

    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN não configurado!")
        return

    logger.success("Configurações carregadas com sucesso.")
    logger.info("Sistema pronto. Aguardando implementação dos módulos.")

if __name__ == "__main__":
    main()
