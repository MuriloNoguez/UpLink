#!/usr/bin/env python3
"""
🚀 Bot UpLink - Versão Otimizada para BlazeHosting
Arquivo principal app.py para hospedagem.
"""

import sys
import logging
import os
from datetime import datetime, timedelta

import discord
from discord.ext import commands, tasks

from config import validate_config, DISCORD_TOKEN, BOT_CONFIG
from database import DatabaseManager
from modules.ui.views import TicketView, TicketControlView, ReopenTicketView
from modules.commands.ticket_commands import TicketCommands
from utils.helpers import close_ticket_channel

# Configuração simples de logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logging.getLogger('discord').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Intents necessários
intents = discord.Intents.default()
intents.message_content = True


class OptimizedTicketBot(commands.Bot):
    """Bot otimizado para hospedagem dedicada no BlazeHosting."""
    
    def __init__(self):
        super().__init__(
            command_prefix=BOT_CONFIG['command_prefix'],
            intents=intents,
            help_command=None
        )
        self.db = DatabaseManager()
        self.startup_time = datetime.now()
        
    async def setup_hook(self):
        """Configuração do bot."""
        try:
            logger.info("Iniciando configuração do bot...")
            
            # Banco de dados com timeout
            logger.info("Conectando ao banco de dados...")
            if not self.db.init_database():
                logger.error("Falha na conexão com banco - continuando sem DB")
            else:
                logger.info("Banco conectado com sucesso")
            
            # Comandos e views
            logger.info("Carregando comandos...")
            await self.add_cog(TicketCommands(self))
            
            logger.info("Sincronizando comandos...")
            try:
                synced = await self.tree.sync()
                logger.info(f"{len(synced)} comandos sincronizados")
            except Exception as e:
                logger.warning(f"Erro ao sincronizar comandos: {e}")
            
            logger.info("Adicionando views persistentes...")
            self.add_view(TicketView())
            self.add_view(TicketControlView())
            self.add_view(ReopenTicketView())
            
            # Task de fechamento automático
            logger.info("Iniciando task de fechamento...")
            self.auto_close_tickets.start()
            
            # Servidor HTTP desabilitado para teste
            logger.info("Servidor HTTP desabilitado - testando estabilidade")
            
            logger.info("✅ Setup concluído com sucesso!")
            
        except Exception as e:
            logger.error(f"Erro durante setup: {e}")
            # Não fazer raise - deixar o bot continuar
    
    async def on_ready(self):
        """Bot pronto."""
        try:
            startup_duration = (datetime.now() - self.startup_time).total_seconds()
            
            await self.change_presence(activity=discord.Activity(
                type=discord.ActivityType.watching, name="tickets de suporte"))
            
            print(f"🟢 Bot {self.user} online em {len(self.guilds)} servidor(es) - {startup_duration:.1f}s")
            logger.info(f"Bot {self.user} pronto após {startup_duration:.1f}s")
            
        except Exception as e:
            logger.error(f"Erro em on_ready: {e}")
    
    async def close_ticket_channel(self, channel: discord.TextChannel, auto_close: bool = False):
        """Wrapper para compatibilidade."""
        await close_ticket_channel(self, channel, auto_close, skip_close_message=False)
    
    @tasks.loop(minutes=BOT_CONFIG['auto_close_check_minutes'])
    async def auto_close_tickets(self):
        """Task otimizada de fechamento automático."""
        try:
            open_tickets = self.db.get_open_tickets()
            if not open_tickets:
                return
                
            now = datetime.now()
            auto_close_time = timedelta(hours=BOT_CONFIG['auto_close_hours'])
            
            for ticket in open_tickets:
                created_at = ticket['created_at']
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at)
                
                if now - created_at >= auto_close_time:
                    channel = self.get_channel(ticket['channel_id'])
                    if channel:
                        await self.close_ticket_channel(channel, auto_close=True)
                        
        except Exception as e:
            logger.error(f"❌ Erro no fechamento automático: {e}")
    
    @auto_close_tickets.before_loop
    async def before_auto_close(self):
        await self.wait_until_ready()
    
    def start_health_server(self):
        """Inicia servidor HTTP para health check do BlazeHosting."""
        import threading
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import os
        
        class HealthHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                try:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b'OK')
                except Exception:
                    pass
            
            def do_HEAD(self):
                try:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                except Exception:
                    pass
            
            def log_message(self, format, *args):
                # Silenciar logs HTTP
                pass
        
        # BlazeHosting geralmente usa porta específica
        port = int(os.environ.get('PORT', 25565))  # Porta comum para BlazeHosting
        
        def run_server():
            try:
                server = HTTPServer(('0.0.0.0', port), HealthHandler)
                logger.info(f"🌐 Servidor HTTP iniciado na porta {port}")
                server.serve_forever()
            except OSError as e:
                if "Address already in use" in str(e):
                    logger.warning(f"Porta {port} já em uso - tentando porta alternativa")
                    # Tentar porta alternativa
                    try:
                        alt_port = port + 1
                        server = HTTPServer(('0.0.0.0', alt_port), HealthHandler)
                        logger.info(f"🌐 Servidor HTTP iniciado na porta alternativa {alt_port}")
                        server.serve_forever()
                    except Exception as alt_e:
                        logger.error(f"Erro na porta alternativa: {alt_e}")
                else:
                    logger.error(f"Erro no servidor HTTP: {e}")
            except Exception as e:
                logger.error(f"Erro inesperado no servidor HTTP: {e}")
        
        # Executar em thread separada
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()


def main():
    try:
        logger.info("Validando configuração...")
        validate_config()
        
        logger.info("Criando instância do bot...")
        bot = OptimizedTicketBot()
        
        logger.info("Iniciando bot...")
        bot.run(DISCORD_TOKEN, log_handler=None)
        
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()
