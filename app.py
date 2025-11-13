#!/usr/bin/env python3
"""
🚀 Bot UpLink - Versão Otimizada para BlazeHosting
Arquivo principal app.py para hospedagem.
"""

import sys
import logging
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
        # Banco de dados
        self.db.init_database()
        
        # Comandos e views
        await self.add_cog(TicketCommands(self))
        await self.tree.sync()
        
        self.add_view(TicketView())
        self.add_view(TicketControlView())
        self.add_view(ReopenTicketView())
        
        # Task de fechamento automático
        self.auto_close_tickets.start()
    
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
        await self.wait_until_ready()


def main():
    validate_config()
    bot = OptimizedTicketBot()
    bot.run(DISCORD_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
