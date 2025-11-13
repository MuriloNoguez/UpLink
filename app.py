#!/usr/bin/env python3
"""
🚀 Bot UpLink - Versão Otimizada para BlazeHosting
Arquivo principal app.py para hospedagem.
"""

import sys
import logging
import os
from datetime import datetime, timedelta
from urllib.parse import urlparse
from urllib import request, error

import discord
from discord.ext import commands, tasks

from config import validate_config, DISCORD_TOKEN, BOT_CONFIG
from database import DatabaseManager
from modules.ui.views import TicketView, TicketControlView, ReopenTicketView
from modules.commands.ticket_commands import TicketCommands
from utils.helpers import close_ticket_channel

# Configuração de logging com banner amigável
LOG_FORMAT = "%(levelname)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
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
        self._health_server_started = False
        self.health_server_port = None
        
    async def setup_hook(self):
        """Configuração do bot."""
        try:
            self._print_startup_banner()
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
            
            # Health-check HTTP para BlazeHosting
            self.ensure_health_server()
            
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
    
    def ensure_health_server(self):
        """Inicializa servidor HTTP se configurado."""
        should_enable = os.environ.get("ENABLE_HEALTH_SERVER", "true").lower() in {"1", "true", "yes", "on"}
        if not should_enable:
            logger.info("Servidor HTTP de health-check desabilitado por configuração.")
            return
        if self._health_server_started:
            return
        logger.info("Iniciando servidor HTTP de health-check para BlazeHosting...")
        self.start_health_server()
        self._log_panel_endpoint_response()

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
        
        # Resolver porta que o painel disponibilizou
        port, port_source = self._resolve_health_port()
        allow_fallback = port_source == "default" or os.environ.get("ALLOW_HEALTH_PORT_FALLBACK", "false").lower() in {"1", "true", "yes", "on"}
        port_candidates = [port]
        if allow_fallback:
            port_candidates.append(port + 1)
        
        def run_server():
            started = False
            for idx, candidate in enumerate(port_candidates):
                try:
                    server = HTTPServer(('0.0.0.0', candidate), HealthHandler)
                    self.health_server_port = candidate
                    started = True
                    resolved_msg = f"{candidate} (fonte: {port_source})"
                    if idx > 0:
                        logger.info(f"🌐 Servidor HTTP iniciado na porta alternativa {resolved_msg}")
                    else:
                        logger.info(f"🌐 Servidor HTTP iniciado na porta {resolved_msg}")
                    server.serve_forever()
                    break
                except OSError as e:
                    if "Address already in use" in str(e):
                        if allow_fallback and idx == 0:
                            logger.warning(f"Porta {candidate} em uso - tentando porta alternativa")
                            continue
                        logger.error(f"Porta {candidate} já está em uso e é a esperada pelo painel BlazeHosting.")
                    else:
                        logger.error(f"Erro no servidor HTTP: {e}")
                    break
                except Exception as e:
                    logger.error(f"Erro inesperado no servidor HTTP: {e}")
                    break
            if not started:
                logger.error("❌ Não foi possível iniciar o servidor HTTP de health-check.")
        
        # Executar em thread separada
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        self._health_server_started = True
    
    def _resolve_health_port(self):
        """Obtém a porta de health-check exposta pela BlazeHosting."""
        env_candidates = [
            "HEALTH_SERVER_PORT",
            "BLAZE_HEALTH_PORT",
            "BLAZE_PORT",
            "SERVER_PORT",
            "APP_PORT",
            "HTTP_PORT",
            "PORT",
            "PORT0",
            "PORT_0",
        ]
        for var in env_candidates:
            port = self._parse_port_value(os.environ.get(var))
            if port:
                return port, f"env:{var}"
        
        address_candidates = [
            "SERVER",
            "SERVER_IP",
            "SERVER_ADDR",
            "SERVER_ADDRESS",
            "BLAZE_ENDPOINT",
            "APP_URL",
            "PUBLIC_URL",
            "LISTEN_ADDRESS",
            "HOST",
            "HOSTNAME",
            "IP",
        ]
        for var in address_candidates:
            port = self._extract_port_from_address(os.environ.get(var))
            if port:
                return port, f"env:{var}"
        
        file_candidates = ["PORT_FILE", "BLAZE_PORT_FILE"]
        for var in file_candidates:
            path = os.environ.get(var)
            if path and os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as fh:
                        port = self._parse_port_value(fh.read().strip())
                        if port:
                            return port, f"file:{var}"
                except OSError as e:
                    logger.warning(f"Não foi possível ler {path}: {e}")
        
        fallback_endpoints = [
            os.environ.get("DEFAULT_HEALTH_ENDPOINT"),
            "sd-br2.blazebr.com:26244",
        ]
        for endpoint in fallback_endpoints:
            port = self._extract_port_from_address(endpoint)
            if port:
                source = endpoint if endpoint else "DEFAULT_HEALTH_ENDPOINT"
                return port, f"fallback:{source}"
        
        return 25565, "default"

    @staticmethod
    def _parse_port_value(value):
        """Converte diferentes fontes em porta válida."""
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        try:
            port = int(text)
        except ValueError:
            return None
        if 1 <= port <= 65535:
            return port
        return None
    
    def _log_panel_endpoint_response(self):
        """Consulta o endpoint externo e loga o retorno para depuração."""
        endpoint = os.environ.get("BLAZE_PANEL_ENDPOINT", "http://sd-br2.blazebr.com:26244/")
        endpoint = endpoint.strip() or "http://sd-br2.blazebr.com:26244/"
        if "://" not in endpoint:
            endpoint = f"http://{endpoint}"
        try:
            with request.urlopen(endpoint, timeout=5) as resp:
                body = resp.read(200).decode("utf-8", errors="replace").strip()
                logger.info(f"Painel BlazeHosting respondeu {resp.status} para {endpoint}: {body or '<vazio>'}")
        except error.URLError as e:
            logger.warning(f"Não foi possível acessar {endpoint}: {e}")
        except Exception as e:
            logger.warning(f"Erro ao consultar {endpoint}: {e}")

    @staticmethod
    def _extract_port_from_address(value):
        """Extrai porta de strings como sd-br.host:26244."""
        if not value:
            return None
        text = str(value).strip()
        if not text:
            return None
        try:
            parsed = urlparse(text if "://" in text else f"http://{text}")
            if parsed.port:
                return parsed.port
        except Exception:
            pass
        if ":" in text:
            return OptimizedTicketBot._parse_port_value(text.rsplit(":", 1)[-1])
        return None

    def _print_startup_banner(self):
        """Mostra um banner elegante no terminal durante o boot."""
        border = "═" * 60
        db_status = "Ativo" if os.getenv("DATABASE_URL") else "Desconectado"
        lines = [
            f"🚀 Iniciando Bot UpLink • BlazeHosting",
            f"🕒 {datetime.now():%d/%m/%Y %H:%M:%S}",
            f"💾 Database: {db_status}",
        ]
        print("\n")
        print(f"\033[95m╔{border}╗\033[0m")
        for line in lines:
            print(f"\033[95m║\033[0m {line:<58} \033[95m║\033[0m")
        print(f"\033[95m╚{border}╝\033[0m")


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
