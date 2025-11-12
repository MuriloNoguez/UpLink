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
            "https://discord.com/api/v10/gateway",  # Discord API (leve e confiável)
            "https://jsonplaceholder.typicode.com/posts/1",  # JSONPlaceholder (muito confiável)
            "https://httpstat.us/200",  # HTTP status service (simples e confiável)
            "https://www.google.com",  # Google (backup confiável)
        ]
        self.successful_pings = 0
        self.failed_pings = 0
    
    async def start(self):
        """Inicia o sistema de keep-alive."""
        try:
            if not self.keep_alive_task.is_running():
                self.keep_alive_task.start()
                logger.info("🔄 Sistema Keep-Alive iniciado (ping a cada 30 minutos)")
            else:
                logger.info("⚠️ Keep-alive já está em execução")
            
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar keep-alive: {e}")
            # Tentar reiniciar após 5 minutos se falhar
            await asyncio.sleep(300)
            try:
                if not self.keep_alive_task.is_running():
                    self.keep_alive_task.start()
                    logger.info("🔄 Keep-alive reiniciado após falha")
            except Exception as retry_error:
                logger.error(f"❌ Falha ao reiniciar keep-alive: {retry_error}")
    
    async def stop(self):
        """Para o sistema de keep-alive."""
        try:
            if self.keep_alive_task.is_running():
                self.keep_alive_task.cancel()
                logger.info("⏸️ Sistema Keep-Alive parado")
            else:
                logger.info("ℹ️ Keep-alive já estava parado")
            
        except Exception as e:
            logger.error(f"❌ Erro ao parar keep-alive: {e}")
    
    def get_stats(self) -> dict:
        """Retorna estatísticas do keep-alive."""
        total_pings = self.successful_pings + self.failed_pings
        success_rate = (self.successful_pings / total_pings * 100) if total_pings > 0 else 0
        
        return {
            'successful_pings': self.successful_pings,
            'failed_pings': self.failed_pings,
            'total_pings': total_pings,
            'success_rate': round(success_rate, 2),
            'is_running': self.keep_alive_task.is_running()
        }
    
    @tasks.loop(minutes=30)
    async def keep_alive_task(self):
        """Task que executa ping a cada 30 minutos."""
        session = None
        ping_successful = False
        
        try:
            # Criar sessão temporária para este ping com headers mais realistas
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            timeout = aiohttp.ClientTimeout(total=15)
            session = aiohttp.ClientSession(timeout=timeout, headers=headers)
            
            timestamp = datetime.now().strftime('%H:%M:%S')
            logger.info(f"🏓 Executando keep-alive ping às {timestamp}")
            
            # Tentar fazer ping em todas as URLs até uma funcionar
            for i, url in enumerate(self.ping_urls, 1):
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            logger.info(f"✅ Ping {i}/{len(self.ping_urls)} bem-sucedido para {url} (status: {response.status})")
                            ping_successful = True
                            self.successful_pings += 1
                            break
                        elif response.status == 403:
                            logger.warning(f"⚠️ Ping {i}/{len(self.ping_urls)} bloqueado (403) para {url} - tentando próximo")
                        elif response.status == 503:
                            logger.warning(f"⚠️ Ping {i}/{len(self.ping_urls)} indisponível (503) para {url} - tentando próximo")
                        else:
                            logger.warning(f"⚠️ Ping {i}/{len(self.ping_urls)} retornou status {response.status} para {url}")
                            
                except asyncio.TimeoutError:
                    logger.warning(f"⏱️ Ping {i}/{len(self.ping_urls)} timeout para {url}")
                except Exception as url_error:
                    logger.warning(f"❌ Ping {i}/{len(self.ping_urls)} falhou para {url}: {type(url_error).__name__}")
                
                # Pequena pausa entre tentativas
                if i < len(self.ping_urls):
                    await asyncio.sleep(2)
            
            # Resultado final
            if ping_successful:
                logger.info(f"🎯 Keep-alive executado com sucesso! (Total: {self.successful_pings} sucessos)")
            else:
                self.failed_pings += 1
                logger.error(f"❌ Todos os {len(self.ping_urls)} pings falharam! (Total falhas: {self.failed_pings})")
                
                # Se muitas falhas consecutivas, logar aviso
                if self.failed_pings >= 3:
                    logger.warning("🚨 Muitas falhas consecutivas no keep-alive. Verifique a conectividade de rede.")
            
            # Log de status do bot
            if self.bot and hasattr(self.bot, 'guilds'):
                guild_count = len(self.bot.guilds)
                logger.info(f"📊 Bot ativo em {guild_count} servidor(es) - Pings: ✅{self.successful_pings} ❌{self.failed_pings}")
            
        except Exception as e:
            self.failed_pings += 1
            logger.error(f"❌ Erro crítico na task de keep-alive: {e}")
        finally:
            # Sempre fechar a sessão no final
            if session and not session.closed:
                try:
                    await session.close()
                except:
                    pass  # Ignora erros ao fechar sessão
    
    @keep_alive_task.before_loop
    async def before_keep_alive(self):
        """Espera o bot estar pronto antes de iniciar os pings."""
        if self.bot:
            await self.bot.wait_until_ready()
        
        # Primeiro ping após 5 minutos para dar tempo do bot estabilizar
        await asyncio.sleep(300)  # 5 minutos
        logger.info("🚀 Keep-alive pronto para iniciar pings regulares a cada 30 minutos")
        
        # Reset contadores quando reinicia
        self.successful_pings = 0
        self.failed_pings = 0


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
    
    # Registrar limpeza quando o bot for fechado
    @bot.event
    async def on_close():
        """Limpa recursos quando o bot é fechado."""
        if hasattr(bot, 'keep_alive_system'):
            await bot.keep_alive_system.stop()
            logger.info("🧹 Keep-alive limpo no fechamento do bot")
    
    return keep_alive_system


async def simple_ping_test():
    """
    Função simples para testar conectividade sem bot.
    Útil para diagnóstico de problemas de rede.
    """
    urls = [
        "https://discord.com/api/v10/gateway",
        "https://jsonplaceholder.typicode.com/posts/1",
        "https://httpstat.us/200",
        "https://www.google.com"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    logger.info("🧪 Iniciando teste de conectividade...")
    
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10), headers=headers) as session:
        for i, url in enumerate(urls, 1):
            try:
                async with session.get(url) as response:
                    status = "✅ SUCESSO" if response.status == 200 else f"⚠️ STATUS {response.status}"
                    logger.info(f"  {i}. {url} - {status}")
            except Exception as e:
                logger.error(f"  {i}. {url} - ❌ FALHA: {type(e).__name__}")
    
    logger.info("🧪 Teste de conectividade concluído")


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