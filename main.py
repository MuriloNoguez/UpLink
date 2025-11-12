"""
Bot de Discord para gestão de chamados de TI - Versão Refatorada.
Criado para facilitar a criação e gestão de tickets de suporte.

Estrutura modular:
- config.py: Configurações e constantes
- database.py: Gerenciamento do banco de dados
- modules/ui/: Interfaces (Views, Modals)
- modules/commands/: Comandos (Cogs)
- utils/: Utilitários e helpers
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta

import discord
from discord.ext import commands, tasks

from config import validate_config, DISCORD_TOKEN, BOT_CONFIG, EMBED_COLORS
from database import DatabaseManager
from modules.ui.views import TicketView, TicketControlView
from utils.helpers import close_ticket_channel, auto_setup_tickets
from keep_alive import setup_keep_alive

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Intents necessários
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True


class TicketBot(commands.Bot):
    """Bot principal para gestão de tickets."""
    
    def __init__(self):
        super().__init__(
            command_prefix=BOT_CONFIG['command_prefix'],
            intents=intents,
            help_command=None
        )
        self.db = DatabaseManager()
        self.persistent_views_added = False
        
    async def setup_hook(self):
        """Configurações iniciais do bot."""
        logger.info("Iniciando configuração do bot...")
        
        # Inicializar banco de dados
        if not self.db.init_database():
            logger.error("Falha ao inicializar banco de dados!")
            return
            
        # Carregar comandos (cogs)
        try:
            await self.load_extension('modules.commands.ticket_commands')
            logger.info("Comandos carregados com sucesso")
        except Exception as e:
            logger.error(f"Erro ao carregar comandos: {e}")
            return
            
        # Adicionar views persistentes
        if not self.persistent_views_added:
            self.add_view(TicketView())
            self.add_view(TicketControlView())
            # Importar e adicionar a nova view de reabertura
            from modules.ui.views import ReopenTicketView
            self.add_view(ReopenTicketView())
            self.persistent_views_added = True
            logger.info("Views persistentes adicionadas")
            
        # Sincronizar comandos slash
        try:
            logger.info("Iniciando sincronização de comandos...")
            synced = await self.tree.sync()
            logger.info(f"Sincronizados {len(synced)} comandos slash")
            
            # Listar comandos sincronizados
            for cmd in synced:
                logger.info(f"  - /{cmd.name}: {cmd.description}")
            
            # Forçar cache dos comandos
            await asyncio.sleep(1)  # Pequena pausa para garantir sincronização
            
            # Exibir mensagem de bot pronto logo após sincronização
            print("\n" + "="*50)
            print("🟢 BOT LIGADO - COMANDOS SINCRONIZADOS")
            print("="*50)
            print(f"⚡ {len(synced)} slash commands prontos:")
            for cmd in synced:
                print(f"  - /{cmd.name}")
            print("💬 Digite / no Discord para ver os comandos")
            print("="*50 + "\n")
            
        except Exception as e:
            logger.error(f"Falha ao sincronizar comandos: {e}")
            print(f"\n❌ ERRO na sincronização: {e}\n")
            
        # Iniciar task de fechamento automático
        if not self.auto_close_tickets.is_running():
            self.auto_close_tickets.start()
            logger.info("Task de fechamento automático iniciada")
            
        # Iniciar sistema keep-alive para manter bot ativo no Render
        try:
            await setup_keep_alive(self)
            logger.info("Sistema Keep-Alive iniciado")
        except Exception as e:
            logger.error(f"Erro ao iniciar Keep-Alive: {e}")
    
    async def on_ready(self):
        """Evento disparado quando o bot está pronto."""
        logger.info(f"Bot logado como {self.user}")
        logger.info(f"Conectado a {len(self.guilds)} servidor(es)")
        
        # Definir status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="tickets de suporte"
            )
        )
        
        # Exibir mensagem de bot pronto
        print("\n" + "="*50)
        print("🟢 BOT PRONTO PARA RECEBER COMANDOS")
        print("="*50)
        print(f"📱 Bot: {self.user}")
        print(f"🌐 Servidores: {len(self.guilds)}")
        print("✅ Status: Online e funcionando")
        print("💬 Digite / no Discord para ver os comandos")
        print("="*50 + "\n")
    
    async def close_ticket_channel(self, channel: discord.TextChannel, auto_close: bool = False):
        """
        Wrapper para função de fechar ticket.
        Mantém compatibilidade com código existente.
        """
        await close_ticket_channel(self, channel, auto_close)
    
    async def close(self):
        """Override do método close para limpeza adequada."""
        # Parar tasks
        if hasattr(self, 'auto_close_tickets') and self.auto_close_tickets.is_running():
            self.auto_close_tickets.cancel()
        
        # Parar keep-alive
        if hasattr(self, 'keep_alive_system'):
            await self.keep_alive_system.stop()
        
        # Fechar conexão do bot
        await super().close()
        logger.info("🔚 Bot fechado corretamente")
    
    async def on_error(self, event_method: str, *args, **kwargs):
        """Handler global de erros."""
        logger.error(f"Erro no evento {event_method}", exc_info=True)
        
    @tasks.loop(minutes=BOT_CONFIG['auto_close_check_minutes'])
    async def auto_close_tickets(self):
        """Task para fechar tickets automaticamente após X horas."""
        try:
            open_tickets = self.db.get_open_tickets()
            now = datetime.now()
            auto_close_time = timedelta(hours=BOT_CONFIG['auto_close_hours'])
            
            for ticket in open_tickets:
                created_at = ticket['created_at']
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at)
                
                # Verifica se passou o tempo configurado
                if now - created_at >= auto_close_time:
                    channel = self.get_channel(ticket['channel_id'])
                    if channel:
                        await self.close_ticket_channel(channel, auto_close=True)
                        logger.info(f"Ticket {ticket['id']} fechado automaticamente (canal mantido)")
                        
        except Exception as e:
            logger.error(f"Erro na task de fechamento automático: {e}")
    
    @auto_close_tickets.before_loop
    async def before_auto_close(self):
        """Espera o bot estar pronto antes de iniciar a task."""
        await self.wait_until_ready()


# Comandos de texto para compatibilidade
@commands.has_permissions(administrator=True)
@commands.command(name='sync')
async def sync_commands(ctx):
    """Comando para forçar sincronização dos comandos slash."""
    try:
        await ctx.message.delete()  # Remove a mensagem do comando
        bot = ctx.bot
        synced = await bot.tree.sync()
        embed = discord.Embed(
            title="✅ Comandos Sincronizados",
            description=f"Sincronizados {len(synced)} comandos slash com sucesso!",
            color=EMBED_COLORS['success']
        )
        embed.add_field(
            name="📝 Como usar:",
            value="Digite `/setup_tickets` no chat e selecione um canal",
            inline=False
        )
        await ctx.send(embed=embed, delete_after=10)
        logger.info(f"Comandos sincronizados manualmente por {ctx.author}")
    except Exception as e:
        await ctx.send(f"❌ Erro ao sincronizar: {e}", delete_after=5)


@commands.has_permissions(manage_channels=True)
@commands.command(name='setup')
async def setup_command(ctx, channel: discord.TextChannel = None):
    """Comando de texto para configurar tickets em um canal."""
    try:
        from utils.helpers import setup_tickets_in_channel
        
        await ctx.message.delete()
        
        if not channel:
            channel = ctx.channel
        
        await setup_tickets_in_channel(ctx.bot, channel)
        
        embed = discord.Embed(
            title="✅ Sistema Configurado",
            description=f"Sistema de tickets configurado no canal {channel.mention}",
            color=EMBED_COLORS['success']
        )
        await ctx.send(embed=embed, delete_after=10)
        
    except Exception as e:
        await ctx.send(f"❌ Erro: {e}", delete_after=5)


async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """Handler de erros para comandos slash."""
    logger.error(f"Erro no comando {interaction.command}: {error}")
    
    if not interaction.response.is_done():
        await interaction.response.send_message(
            "❌ Ocorreu um erro interno. Tente novamente.",
            ephemeral=True
        )


def main():
    """Função principal para iniciar o bot."""
    try:
        # Validar configuração
        validate_config()
        
        # Criar e configurar bot
        bot = TicketBot()
        
        # Adicionar comandos de texto
        bot.add_command(sync_commands)
        bot.add_command(setup_command)
        
        # Adicionar handler de erro para comandos slash
        bot.tree.on_error = on_app_command_error
        
        logger.info("Iniciando bot de tickets...")
        
        # Executar bot
        bot.run(DISCORD_TOKEN, log_handler=None)  # Usar nosso próprio logging
        
    except ValueError as e:
        logger.error(f"Erro de configuração: {e}")
    except Exception as e:
        logger.error(f"Erro ao iniciar bot: {e}")


if __name__ == "__main__":
    main()