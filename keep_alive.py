"""
Sistema de Keep-Alive para manter o bot ativo em hospedagens que desligam por inatividade.
Executa pings automáticos a cada 30 minutos.
"""

import logging
import asyncio
import aiohttp
from datetime import datetime
from discord.ext import tasks

logger = logging.getLogger(__name__)


class KeepAliveSystem:
    """Sistema para manter o bot ativo com pings periódicos."""
    
    def __init__(self, bot):
        self.bot = bot
        self.ping_urls = [
            "https://httpbin.org/get",  # Serviço público para teste de ping
            "https://api.github.com/zen",  # API do GitHub (leve)
        ]
        self.session = None
    
    async def start(self):
        """Inicia o sistema de keep-alive."""
        try:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
            
            if not self.keep_alive_task.is_running():
                self.keep_alive_task.start()
                logger.info("🔄 Sistema Keep-Alive iniciado (ping a cada 30 minutos)")
            
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar keep-alive: {e}")
    
    async def stop(self):
        """Para o sistema de keep-alive."""
        try:
            if self.keep_alive_task.is_running():
                self.keep_alive_task.cancel()
            
            if self.session and not self.session.closed:
                await self.session.close()
                
            logger.info("⏸️ Sistema Keep-Alive parado")
            
        except Exception as e:
            logger.error(f"❌ Erro ao parar keep-alive: {e}")
    
    @tasks.loop(minutes=30)
    async def keep_alive_task(self):
        """Task que executa ping a cada 30 minutos."""
        try:
            if not self.session or self.session.closed:
                self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
            
            timestamp = datetime.now().strftime('%H:%M:%S')
            logger.info(f"🏓 Executando keep-alive ping às {timestamp}")
            
            # Fazer ping em uma das URLs
            for url in self.ping_urls:
                try:
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            logger.info(f"✅ Ping bem-sucedido para {url} (status: {response.status})")
                            break
                        else:
                            logger.warning(f"⚠️ Ping retornou status {response.status} para {url}")
                except Exception as url_error:
                    logger.warning(f"❌ Falha no ping para {url}: {url_error}")
                    continue
            else:
                # Se chegou aqui, todos os pings falharam
                logger.error("❌ Todos os pings falharam!")
            
            # Log de status do bot
            if self.bot and hasattr(self.bot, 'guilds'):
                guild_count = len(self.bot.guilds)
                logger.info(f"📊 Bot ativo em {guild_count} servidor(es)")
            
        except Exception as e:
            logger.error(f"❌ Erro na task de keep-alive: {e}")
    
    @keep_alive_task.before_loop
    async def before_keep_alive(self):
        """Espera o bot estar pronto antes de iniciar os pings."""
        if self.bot:
            await self.bot.wait_until_ready()
        
        # Primeiro ping imediato após 5 minutos de inicialização
        await asyncio.sleep(300)  # 5 minutos
        logger.info("🚀 Keep-alive pronto para iniciar pings regulares")


# Função utilitária para integrar facilmente no bot principal
async def setup_keep_alive(bot):
    """
    Configura e inicia o sistema de keep-alive para um bot.
    
    Args:
        bot: Instância do bot Discord
    
    Returns:
        KeepAliveSystem: Instância do sistema para controle manual se necessário
    """
    keep_alive_system = KeepAliveSystem(bot)
    await keep_alive_system.start()
    
    # Adicionar o sistema ao bot para acesso posterior
    bot.keep_alive_system = keep_alive_system
    
    return keep_alive_system


# Exemplo de uso standalone (se necessário executar separadamente)
if __name__ == "__main__":
    import asyncio
    
    async def test_keep_alive():
        """Teste do sistema keep-alive sem bot."""
        system = KeepAliveSystem(None)
        await system.start()
        
        # Manter rodando por alguns ciclos para teste
        await asyncio.sleep(7200)  # 2 horas
        
        await system.stop()
    
    # Executar teste
    asyncio.run(test_keep_alive())