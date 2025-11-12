#!/usr/bin/env python3
"""
🚀 Bot UpLink - Versão Otimizada para Produção
Sem sincronização automática para builds mais rápidos no Render.
"""

import os
import sys
import logging
import asyncio
from datetime import datetime, timedelta

import discord
from discord.ext import commands, tasks

from config import validate_config, DISCORD_TOKEN, BOT_CONFIG, EMBED_COLORS
from database import DatabaseManager
from modules.ui.views import TicketView, TicketControlView
from modules.commands.ticket_commands import TicketCommands
from utils.helpers import close_ticket_channel
from keep_alive import setup_keep_alive

# Configuração otimizada de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',  # Formato mais simples
    handlers=[
        logging.StreamHandler(sys.stdout)  # Apenas output direto, sem arquivo
    ]
)

# Reduzir logs de bibliotecas externas
logging.getLogger('discord.gateway').setLevel(logging.WARNING)
logging.getLogger('discord.http').setLevel(logging.WARNING)
logging.getLogger('aiohttp').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Intents mínimos necessários
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True


class OptimizedTicketBot(commands.Bot):
    """Bot otimizado para produção no Render."""
    
    def __init__(self):
        super().__init__(
            command_prefix=BOT_CONFIG['command_prefix'],
            intents=intents,
            help_command=None,
            # Otimizações de conexão
            max_messages=100,  # Cache menor de mensagens
            chunk_guilds_at_startup=False  # Não carregar membros na inicialização
        )
        self.db = DatabaseManager()
        self.startup_time = datetime.now()
        
    async def setup_hook(self):
        """Configuração rápida sem sincronização."""
        logger.info("⚡ Configuração rápida iniciada...")
        
        # Banco de dados
        if not self.db.init_database():
            logger.error("❌ Falha no banco de dados!")
            return
            
        # Comandos
        await self.add_cog(TicketCommands(self))
        
        # Views persistentes
        self.add_view(TicketView())
        self.add_view(TicketControlView())
        
        # Tasks
        if not self.auto_close_tickets.is_running():
            self.auto_close_tickets.start()
            
        # Keep-alive
        await setup_keep_alive(self)
        
        logger.info("✅ Bot configurado e pronto!")
    
    async def on_ready(self):
        """Bot pronto - versão otimizada."""
        startup_duration = (datetime.now() - self.startup_time).total_seconds()
        
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="tickets de suporte"
            )
        )
        
        print(f"""
🟢 BOT UPLINK ONLINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 Bot: {self.user}
🌐 Servidores: {len(self.guilds)}
⚡ Tempo de inicialização: {startup_duration:.1f}s
✅ Status: Pronto para receber comandos
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 Use /setup_tickets para configurar canais
💬 Use / no Discord para ver todos os comandos
        """)
    
    async def close_ticket_channel(self, channel: discord.TextChannel, auto_close: bool = False):
        """Wrapper para compatibilidade."""
        await close_ticket_channel(self, channel, auto_close)
    
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
        """Aguarda bot estar pronto."""
        await self.wait_until_ready()


def main():
    """Inicialização otimizada."""
    try:
        # Validações rápidas
        validate_config()
        
        # Log de início
        print("🚀 INICIANDO UPLINK BOT...")
        
        # Criar e iniciar bot
        bot = OptimizedTicketBot()
        
        # Executar
        bot.run(DISCORD_TOKEN, log_handler=None)
        
    except KeyboardInterrupt:
        print("\n👋 Bot finalizado")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()