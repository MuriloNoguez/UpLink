#!/usr/bin/env python3
"""
🚀 Bot UpLink - Versão Otimizada - Arquivo Único
Consolidado para hospedagem que requer um único arquivo.
"""

import sys
import logging
import os
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from urllib.parse import urlparse
from urllib import request, error
from http.server import HTTPServer, BaseHTTPRequestHandler

import discord
from discord.ext import commands, tasks
from discord import app_commands
import psycopg2
from psycopg2 import sql, Error
from psycopg2.extras import DictCursor
from dotenv import load_dotenv

# ==================================================================================================
# CONFIGURAÇÃO (config.py)
# ==================================================================================================

# Carrega variáveis de ambiente
load_dotenv(override=True)

# Configurações do Discord
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Configurações do Banco de Dados PostgreSQL
DATABASE_CONFIG = {
    'url': os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/bot_tickets'),
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', '5432')),
    'database': os.getenv('POSTGRES_DB', 'bot_tickets'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', ''),
    'sslmode': os.getenv('POSTGRES_SSLMODE', 'prefer'),
    'connect_timeout': int(os.getenv('POSTGRES_TIMEOUT', '30'))
}

# Configurações do Bot
BOT_CONFIG = {
    'command_prefix': '/',
    'support_role_name': 'Suporte TI',
    'tickets_category_name': 'Tecnologia',
    'auto_close_hours': 12,
    'auto_close_check_minutes': 30,
    'channel_names_to_setup': ['suporte', 'tickets', 'ajuda', 'support', 'help']
}

# Embeds e Mensagens
EMBED_COLORS = {
    'success': 0x00ff00,    # Verde
    'error': 0xff0000,      # Vermelho  
    'warning': 0xffa500,    # Laranja
    'info': 0x0099ff,       # Azul
    'closed': 0xff0000,     # Vermelho
    'paused': 0xffa500,     # Laranja
    'reopened': 0xffa500    # Laranja
}

# Emoji para status
STATUS_EMOJI = {
    'open': '🟢',
    'closed': '🔴',
    'paused': '⏸️',
    'unknown': '❓'
}

# Opções de motivos para tickets
TICKET_REASONS = [
    {
        'label': 'Arbo',
        'description': 'Problemas relacionados ao Arbo',
        'emoji': '<:arbo:1437860050201874442>'
    },
    {
        'label': 'Lais',
        'description': 'Problemas relacionados ao Lais',
        'emoji': '<:Lais:1437865327001342052>'
    },
    {
        'label': 'SendPulse',
        'description': 'Problemas relacionados ao SendPulse',
        'emoji': '<:SP:1437860450523025459>'
    },
    {
        'label': 'Outros',
        'description': 'Outros tipos de problemas',
        'emoji': '❓'
    }
]

# Validação de configuração
def validate_config():
    """Valida se todas as configurações necessárias estão presentes."""
    if not DISCORD_TOKEN:
        raise ValueError("DISCORD_TOKEN não encontrado nas variáveis de ambiente!")
    return True


# ==================================================================================================
# CONFIGURAÇÃO DE LOGGING
# ==================================================================================================
LOG_FORMAT = "%(levelname)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logging.getLogger('discord').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# ==================================================================================================
# DATABASE (database.py)
# ==================================================================================================

class DatabaseManager:
    """Gerenciador de conexão com PostgreSQL para o bot de tickets."""
    
    def __init__(self):
        """Inicializa o gerenciador com configurações de ambiente."""
        self.database_url = os.getenv('DATABASE_URL') or "postgresql://neondb_owner:npg_FJcdz9Qp6w4HPGJUPBEPHIZhvBBcJhGz@ep-wild-recipe-a5m5vx6y.us-east-2.aws.neon.tech/neondb?sslmode=require"
        
        parsed = urlparse(self.database_url)
        self.config = {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'database': parsed.path[1:],  # Remove a barra inicial
            'user': parsed.username,
            'password': parsed.password,
        }
        
    def get_connection(self) -> Optional[psycopg2.extensions.connection]:
        try:
            connection = psycopg2.connect(
                self.database_url,
                cursor_factory=DictCursor,
                connect_timeout=10
            )
            return connection
        except Error as e:
            logger.error(f"Erro ao conectar com PostgreSQL: {e}")
            return None
    
    def test_connection(self) -> bool:
        try:
            connection = self.get_connection()
            if connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                connection.close()
                logger.info("Conexão com PostgreSQL testada com sucesso")
                return True
            return False
        except Exception as e:
            logger.error(f"Erro ao testar conexão: {e}")
            return False
    
    def init_database(self) -> bool:
        try:
            connection = self.get_connection()
            if not connection:
                logger.error("Não foi possível conectar ao banco")
                return False
            
            logger.info("Conectado ao PostgreSQL com sucesso")
            
            with connection.cursor() as cursor:
                create_table_query = """
                CREATE TABLE IF NOT EXISTS tickets (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    user_name VARCHAR(255) NOT NULL,
                    channel_id BIGINT UNIQUE NOT NULL,
                    reason VARCHAR(255) NOT NULL,
                    description TEXT,
                    status VARCHAR(20) DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    closed_at TIMESTAMP NULL,
                    paused_at TIMESTAMP NULL,
                    paused_by VARCHAR(255) NULL
                );
                """
                cursor.execute(create_table_query)
                
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_tickets_user_id ON tickets(user_id);",
                    "CREATE INDEX IF NOT EXISTS idx_tickets_channel_id ON tickets(channel_id);",
                    "CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);",
                    "CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON tickets(created_at);"
                ]
                for index_query in indexes:
                    cursor.execute(index_query)
                
                connection.commit()
                logger.info("Tabela 'tickets' criada/verificada com sucesso")
                
            connection.close()
            return True
        except Exception as e:
            logger.error(f"Erro ao inicializar banco: {e}")
            return False
    
    def create_ticket(self, user_id: int, user_name: str, channel_id: int, 
                     reason: str, description: str) -> Optional[int]:
        try:
            connection = self.get_connection()
            if not connection:
                return None
            
            with connection.cursor() as cursor:
                insert_query = """
                    INSERT INTO tickets (user_id, user_name, channel_id, reason, description)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id;
                """
                cursor.execute(insert_query, (user_id, user_name, channel_id, reason, description))
                ticket_id = cursor.fetchone()['id']
                connection.commit()
                
                logger.info(f"Ticket {ticket_id} criado para usuário {user_name}")
                connection.close()
                return ticket_id
        except Exception as e:
            logger.error(f"Erro ao criar ticket: {e}")
            return None
    
    def get_ticket_by_channel(self, channel_id: int) -> Optional[Dict[str, Any]]:
        try:
            connection = self.get_connection()
            if not connection:
                return None
            
            with connection.cursor() as cursor:
                query = "SELECT * FROM tickets WHERE channel_id = %s ORDER BY id DESC LIMIT 1;"
                cursor.execute(query, (channel_id,))
                result = cursor.fetchone()
                
            connection.close()
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Erro ao buscar ticket por canal {channel_id}: {e}")
            return None
    
    def get_user_latest_ticket(self, user_id: int) -> Optional[Dict[str, Any]]:
        try:
            connection = self.get_connection()
            if not connection:
                return None
            
            with connection.cursor() as cursor:
                query = """
                    SELECT * FROM tickets 
                    WHERE user_id = %s 
                    ORDER BY id DESC 
                    LIMIT 1;
                """
                cursor.execute(query, (user_id,))
                result = cursor.fetchone()
                
            connection.close()
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Erro ao buscar último ticket do usuário {user_id}: {e}")
            return None
    
    def get_user_tickets(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            connection = self.get_connection()
            if not connection:
                return []
            
            with connection.cursor() as cursor:
                query = """
                    SELECT * FROM tickets 
                    WHERE user_id = %s 
                    ORDER BY id DESC 
                    LIMIT %s;
                """
                cursor.execute(query, (user_id, limit))
                results = cursor.fetchall()
                
            connection.close()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Erro ao buscar tickets do usuário {user_id}: {e}")
            return []
    
    def close_ticket(self, channel_id: int) -> bool:
        try:
            connection = self.get_connection()
            if not connection:
                return False
            
            with connection.cursor() as cursor:
                query = """
                    UPDATE tickets 
                    SET status = 'closed', closed_at = CURRENT_TIMESTAMP
                    WHERE channel_id = %s AND status != 'closed';
                """
                cursor.execute(query, (channel_id,))
                connection.commit()
                success = cursor.rowcount > 0
                
            connection.close()
            logger.info(f"Ticket do canal {channel_id} {'fechado' if success else 'não encontrado/já fechado'}")
            return success
        except Exception as e:
            logger.error(f"Erro ao fechar ticket do canal {channel_id}: {e}")
            return False
    
    def reopen_ticket(self, channel_id: int, reason: str, description: str) -> Optional[int]:
        try:
            connection = self.get_connection()
            if not connection:
                return None
            
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM tickets WHERE channel_id = %s ORDER BY id DESC LIMIT 1;", 
                             (channel_id,))
                result = cursor.fetchone()
                
                if not result:
                    return None
                
                ticket_id = result['id']
                
                update_query = """
                    UPDATE tickets 
                    SET status = 'open', reason = %s, description = %s,
                        closed_at = NULL, paused_at = NULL, paused_by = NULL,
                        created_at = CURRENT_TIMESTAMP
                    WHERE id = %s;
                """
                cursor.execute(update_query, (reason, description, ticket_id))
                connection.commit()
                
            connection.close()
            logger.info(f"Ticket {ticket_id} reaberto com novo motivo: {reason}")
            return ticket_id
        except Exception as e:
            logger.error(f"Erro ao reabrir ticket do canal {channel_id}: {e}")
            return None
    
    def pause_ticket(self, channel_id: int, paused_by: str) -> bool:
        try:
            connection = self.get_connection()
            if not connection:
                return False
            
            with connection.cursor() as cursor:
                query = """
                    UPDATE tickets 
                    SET status = 'paused', paused_at = CURRENT_TIMESTAMP, paused_by = %s
                    WHERE channel_id = %s AND status = 'open';
                """
                cursor.execute(query, (paused_by, channel_id))
                connection.commit()
                success = cursor.rowcount > 0
                
            connection.close()
            return success
        except Exception as e:
            logger.error(f"Erro ao pausar ticket do canal {channel_id}: {e}")
            return False
    
    def unpause_ticket(self, channel_id: int) -> bool:
        try:
            connection = self.get_connection()
            if not connection:
                return False
            
            with connection.cursor() as cursor:
                query = """
                    UPDATE tickets 
                    SET status = 'open', paused_at = NULL, paused_by = NULL
                    WHERE channel_id = %s AND status = 'paused';
                """
                cursor.execute(query, (channel_id,))
                connection.commit()
                success = cursor.rowcount > 0
                
            connection.close()
            return success
        except Exception as e:
            logger.error(f"Erro ao despausar ticket do canal {channel_id}: {e}")
            return False
    
    def get_open_tickets(self) -> List[Dict[str, Any]]:
        try:
            connection = self.get_connection()
            if not connection:
                return []
            
            with connection.cursor() as cursor:
                query = "SELECT * FROM tickets WHERE status = 'open' ORDER BY created_at ASC;"
                cursor.execute(query)
                results = cursor.fetchall()
                
            connection.close()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Erro ao buscar tickets abertos: {e}")
            return []
    
    def get_ticket_stats(self) -> Dict[str, int]:
        try:
            connection = self.get_connection()
            if not connection:
                return {}
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT status, COUNT(*) as count 
                    FROM tickets 
                    GROUP BY status;
                """)
                status_counts = {row['status']: row['count'] for row in cursor.fetchall()}
                
                cursor.execute("SELECT COUNT(*) as total FROM tickets;")
                total = cursor.fetchone()['total']
                
            connection.close()
            
            return {
                'total': total,
                'open': status_counts.get('open', 0),
                'closed': status_counts.get('closed', 0),
                'paused': status_counts.get('paused', 0)
            }
        except Exception as e:
            logger.error(f"Erro ao buscar estatísticas: {e}")
            return {}

# ==================================================================================================
# UTILS (utils/helpers.py)
# ==================================================================================================

def resolve_emoji(bot: discord.Client, emoji_str: str, guild: discord.Guild = None):
    """Resolve um emoji string para um objeto emoji do Discord."""
    try:
        if emoji_str.startswith('<'):
            return discord.PartialEmoji.from_str(emoji_str)
    except Exception:
        pass

    if guild:
        e = discord.utils.get(guild.emojis, name=emoji_str)
        if e:
            return e

    e = discord.utils.get(bot.emojis, name=emoji_str)
    if e:
        return e

    return emoji_str


def schedule_ephemeral_deletion(
    interaction: discord.Interaction,
    message: Optional[discord.Message] = None,
    delay: int = 120,
):
    """Remove mensagens ephemerals após o tempo indicado."""
    async def delete_ephemeral_message():
        try:
            await asyncio.sleep(delay)
            if message is not None:
                await message.delete()
            else:
                await interaction.delete_original_response()
        except (discord.NotFound, discord.HTTPException):
            pass
        except Exception as exc:
            logger.debug("Falha ao remover mensagem ephemeral: %s", exc)

    asyncio.create_task(delete_ephemeral_message())


async def close_ticket_channel(bot, channel: discord.TextChannel, auto_close: bool = False, skip_close_message: bool = False):
    """Fecha um canal de ticket garantindo que a mensagem de fechamento apareça."""
    try:
        ticket = bot.db.get_ticket_by_channel(channel.id)
        bot.db.close_ticket(channel.id)
        
        embed = discord.Embed(
            title="🔒 TICKET FECHADO",
            description="Este ticket foi fechado e está agora em modo somente leitura.\n\n"
                       "**Histórico Preservado:** Todo o histórico foi mantido.\n"
                       "**Reabertura:** Use o botão abaixo para reabrir este ticket.",
            color=EMBED_COLORS['closed'],
            timestamp=datetime.now()
        )
        
        if auto_close:
            embed.add_field(
                name="⏰ Motivo",
                value=f"Fechamento automático após {BOT_CONFIG['auto_close_hours']} horas",
                inline=False
            )
        
        if not skip_close_message:
            reopen_view = ReopenTicketView()
            await channel.send(embed=embed, view=reopen_view)
        else:
            reopen_view = ReopenTicketView()
            await channel.send(view=reopen_view)
        
        async def update_permissions_async():
            try:
                guild = channel.guild
                if ticket:
                    ticket_owner = guild.get_member(ticket['user_id'])
                    if ticket_owner:
                        await channel.set_permissions(
                            ticket_owner, 
                            send_messages=False,
                            add_reactions=False,
                            view_channel=True
                        )
                        await asyncio.sleep(1)
                
                await channel.set_permissions(
                    guild.default_role, 
                    send_messages=False,
                    add_reactions=False,
                    view_channel=False
                )
            except Exception as e:
                logger.warning(f"Erro ao atualizar permissões após fechamento: {e}")
        
        asyncio.create_task(update_permissions_async())
        logger.info(f"Ticket {channel.id} fechado com sucesso")
        
    except Exception as e:
        logger.error(f"Erro ao fechar canal {channel.id}: {e}")
        try:
            await channel.send("❌ Erro ao fechar ticket. Contate um administrador.")
        except:
            pass

def format_timestamp(dt):
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    return f"<t:{int(dt.timestamp())}:R>"

# ==================================================================================================
# UI VIEWS (modules/ui/views.py + modals.py consolidated)
# ==================================================================================================

# Mapeamento de permissões necessárias
REQUIRED_TICKET_PERMISSIONS = {
    "manage_channels": "Manage Channels",
    "send_messages": "Send Messages",
    "embed_links": "Embed Links",
    "attach_files": "Attach Files",
}

@dataclass
class TicketChannelContext:
    channel: discord.TextChannel
    ticket_id: Optional[int]
    is_reopened: bool = False
    skip_intro_embed: bool = False


# Declaração forward para views
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(
        label="Abrir Ticket",
        style=discord.ButtonStyle.primary,
        emoji="🎫",
        custom_id="open_ticket_button"
    )
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Verificar se o usuário já tem um ticket aberto
            user_tickets = interaction.client.db.get_user_tickets(interaction.user.id, 5)
            open_tickets = [t for t in user_tickets if t['status'] == 'open']
            
            if open_tickets:
                ticket = open_tickets[0]
                channel = interaction.guild.get_channel(ticket['channel_id'])
                if channel:
                    await interaction.response.send_message(
                        f"❌ Você já tem um ticket aberto: {channel.mention}\n"
                        f"**Motivo atual:** {ticket['reason']}\n"
                        f"**Criado em:** <t:{int(ticket['created_at'].timestamp())}:R>\n\n"
                        f"💡 **Dica:** Você pode usar o mesmo canal para novos problemas!",
                        ephemeral=True
                    )
                    schedule_ephemeral_deletion(interaction)
                    return
            
            view = ReasonSelectView(interaction.client, interaction.guild)
            await interaction.response.send_message(
                "🎫 **Selecione o motivo do seu chamado:**",
                view=view,
                ephemeral=True
            )
            schedule_ephemeral_deletion(interaction)
            
        except Exception as e:
            logger.error(f"Erro ao abrir ticket: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Erro interno. Tente novamente.", ephemeral=True)
            else:
                await interaction.followup.send("❌ Erro interno. Tente novamente.", ephemeral=True)

class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

class ReopenTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(
        label="Reabrir Ticket",
        style=discord.ButtonStyle.success,
        emoji="🔄",
        custom_id="reopen_ticket_button"
    )
    async def reopen_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            ticket = interaction.client.db.get_ticket_by_channel(interaction.channel.id)
            if not ticket:
                await interaction.response.send_message("❌ Este não é um canal de ticket válido.", ephemeral=True)
                return
                
            if ticket['status'] != 'closed':
                await interaction.response.send_message(f"❌ Este ticket não está fechado. Status atual: {ticket['status']}", ephemeral=True)
                return
            
            user = interaction.user
            if user.id != ticket['user_id']:
                await interaction.response.send_message("❌ Apenas o dono do ticket pode reabri-lo.", ephemeral=True)
                return
            
            view = ReasonSelectView(interaction.client, interaction.guild)
            await interaction.response.send_message("🎫 **Selecione o motivo da reabertura:**", view=view, ephemeral=True)
            schedule_ephemeral_deletion(interaction)
            
        except Exception as e:
            logger.error(f"Erro ao reabrir ticket via botão: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Erro interno ao reabrir ticket.", ephemeral=True)

# Helper para ReasonSelect
def _build_reason_options(bot: Optional[discord.Client], guild: Optional[discord.Guild]) -> List[discord.SelectOption]:
    options: List[discord.SelectOption] = []
    for reason in TICKET_REASONS:
        emoji = resolve_emoji(bot, reason["emoji"], guild) if bot and guild else reason["emoji"]
        options.append(
            discord.SelectOption(
                label=reason["label"],
                description=reason["description"],
                emoji=emoji,
            )
        )
    return options

# Modais e Selects
class ReasonSelect(discord.ui.Select):
    def __init__(self, bot=None, guild=None):
        self.bot = bot
        self.guild = guild
        super().__init__(
            placeholder="Selecione o motivo do seu chamado...",
            options=_build_reason_options(bot, guild),
            custom_id="ticket_reason_select"
        )
    
    async def callback(self, interaction: discord.Interaction):
        try:
            reason = self.values[0]
            modal = DescriptionModal(reason)
            await interaction.response.send_modal(modal)
        except Exception as e:
            logger.error(f"Erro no callback do select: {e}")
            await interaction.response.send_message("❌ Ocorreu um erro. Tente novamente.", ephemeral=True)

class DescriptionModal(discord.ui.Modal):
    def __init__(self, reason: str):
        super().__init__(title=f"Novo Ticket - {reason}")
        self.reason = reason
        self.description = discord.ui.TextInput(
            label="Descrição do Problema",
            placeholder="Descreva o problema com detalhes...",
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True
        )
        self.add_item(self.description)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            guild = interaction.guild
            user = interaction.user
            if not guild: return

            context = await self._prepare_channel(interaction, guild, user)
            if not context or not context.ticket_id:
                if context and not context.is_reopened:
                    await context.channel.delete(reason="Erro ao criar ticket no banco")
                await self._notify_creation_failure(interaction)
                return

            if not context.skip_intro_embed:
                control_view = TicketControlView()
                embed = self._build_ticket_embed(user, self.description.value, context.is_reopened)
                await context.channel.send(
                    content=self._build_ticket_opening_content(user, context.is_reopened),
                    embed=embed,
                    view=control_view,
                )

            await self._send_ephemeral_confirmation(interaction, context.channel, context.is_reopened)
            # Log omission for brevity

        except Exception as exc:
            logger.error(f"Erro no modal submit: {exc}")
            await interaction.followup.send("❌ Ocorreu um erro no processamento.", ephemeral=True)

    async def _prepare_channel(self, interaction, guild, user) -> Optional[TicketChannelContext]:
        latest_ticket = interaction.client.db.get_user_latest_ticket(user.id)
        if latest_ticket:
            channel = guild.get_channel(latest_ticket["channel_id"])
            if channel:
                # Reopen Logic inline
                ticket_id = interaction.client.db.reopen_ticket(channel.id, self.reason, self.description.value)
                if not ticket_id: return None
                
                embed = self._build_reopen_embed(user)
                control_view = TicketControlView()
                await channel.send(
                    content=self._build_ticket_opening_content(user, True),
                    embed=embed,
                    view=control_view,
                )
                
                # Restore permissions
                await channel.set_permissions(user, send_messages=True, add_reactions=True, view_channel=True)
                
                return TicketChannelContext(channel=channel, ticket_id=ticket_id, is_reopened=True, skip_intro_embed=True)

        return await self._create_channel_with_ticket(interaction, guild, user)

    async def _create_channel_with_ticket(self, interaction, guild, user) -> Optional[TicketChannelContext]:
        category = discord.utils.get(guild.categories, name=BOT_CONFIG["tickets_category_name"])
        if not category:
            category = await guild.create_category(name=BOT_CONFIG["tickets_category_name"])

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
        }
        if guild.me:
            overwrites[guild.me] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True, embed_links=True)

        channel_name = f"💻┃{user.name.lower()}"
        channel = await category.create_text_channel(name=channel_name, overwrites=overwrites)
        
        ticket_id = interaction.client.db.create_ticket(
            user_id=user.id, user_name=str(user), channel_id=channel.id,
            reason=self.reason, description=self.description.value,
        )
        return TicketChannelContext(channel=channel, ticket_id=ticket_id)

    def _build_ticket_embed(self, user, description, is_reopened):
        embed = discord.Embed(
            title="🔄 Ticket Reaberto" if is_reopened else "🎫 Novo Ticket de Suporte",
            description="Seu ticket foi reaberto!" if is_reopened else "Seu ticket foi criado com sucesso!",
            color=0xFFA500 if is_reopened else 0x00FF00,
            timestamp=datetime.now()
        )
        embed.add_field(name="👤 Usuário", value=user.mention, inline=True)
        embed.add_field(name="🏷️ Motivo", value=self.reason, inline=True)
        embed.add_field(name="📝 Descrição", value=description, inline=False)
        return embed

    def _build_reopen_embed(self, user):
        return self._build_ticket_embed(user, self.description.value, True)

    def _build_ticket_opening_content(self, user, is_reopened):
        action = "reaberto" if is_reopened else "criado"
        return f"🔔 **{user.mention}, seu ticket foi {action}!**\n📞 <@&1382008028517109832> responderá em breve."

    async def _send_ephemeral_confirmation(self, interaction, channel, is_reopened):
        embed = discord.Embed(
            title="Ticket Criado/Reaberto",
            description=f"Acesse seu ticket em {channel.mention}",
            color=0x00FF00
        )
        message = await interaction.followup.send(embed=embed, ephemeral=True)
        schedule_ephemeral_deletion(interaction, message, delay=120)

    async def _notify_creation_failure(self, interaction):
        await interaction.followup.send("❌ Erro ao criar ticket.", ephemeral=True)

class ReasonSelectView(discord.ui.View):
    def __init__(self, bot=None, guild=None):
        super().__init__(timeout=300)
        self.add_item(ReasonSelect(bot, guild))

class CloseStatusSelect(discord.ui.Select):
    def __init__(self, ticket):
        self.ticket = ticket
        options = [
            discord.SelectOption(label="Resolvido", emoji="✅", value="resolvido"),
            discord.SelectOption(label="Chamado Aberto", emoji="📞", value="chamado_aberto"),
            discord.SelectOption(label="Aguardando Resposta", emoji="⏳", value="aguardando_resposta"),
            discord.SelectOption(label="Em Análise", emoji="🔍", value="em_analise")
        ]
        super().__init__(placeholder="Selecione o status do ticket...", options=options, custom_id="pause_status_select")
    
    async def callback(self, interaction: discord.Interaction):
        try:
            status = self.values[0]
            modal = PauseDescriptionModal(self.ticket, status)
            await interaction.response.send_modal(modal)
        except Exception as e:
            logger.error(f"Erro no select close: {e}")
            await interaction.response.send_message("❌ Erro.", ephemeral=True)

class PauseDescriptionModal(discord.ui.Modal):
    def __init__(self, ticket: dict, status: str):
        self.ticket = ticket
        self.status = status
        title = f"Status: {status.replace('_', ' ').title()}"
        super().__init__(title=title)
        self.description = discord.ui.TextInput(
            label="Detalhes", placeholder="Descreva...", style=discord.TextStyle.paragraph, max_length=1000, required=True
        )
        self.add_item(self.description)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            channel = interaction.channel
            user = interaction.user
            
            embed = discord.Embed(
                title=f"Status: {self.status.upper()}",
                description=self.description.value,
                color=0x00FF00,
                timestamp=datetime.now()
            )
            embed.add_field(name="Responsável", value=user.mention)
            await channel.send(embed=embed)
            
            await asyncio.sleep(2)
            await close_ticket_channel(interaction.client, channel, auto_close=False, skip_close_message=True)
            await interaction.followup.send("✅ Ticket atualizado e fechado.", ephemeral=True)
            
        except Exception as e:
            logger.error(f"Erro no pause modal: {e}")
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)

class CloseStatusView(discord.ui.View):
    def __init__(self, ticket):
        super().__init__(timeout=300)
        self.add_item(CloseStatusSelect(ticket))

# ==================================================================================================
# UTILS DE SETUP (localizados aqui para acessar as Views)
# ==================================================================================================

async def setup_tickets_in_channel(bot, channel: discord.TextChannel):
    """Configura o sistema de tickets em um canal específico."""
    embed = discord.Embed(
        title="🎫 **SISTEMA DE TICKETS DE SUPORTE**",
        description="**PRECISA DE AJUDA DA EQUIPE DE TI?**\n\n**Clique no botão abaixo para abrir um ticket!**",
        color=EMBED_COLORS['info']
    )
    embed.add_field(
        name="📝 **PLATAFORMAS DISPONÍVEIS:**",
        value=(
            "**<:arbo:1437860050201874442> ARBO**\n\n"
            "**<:Lais:1437865327001342052> LAIS**\n\n"
            "**<:SP:1437860450523025459> SENDPULSE**\n\n"
            "**❓ OUTROS**"
        ),
        inline=False
    )
    embed.add_field(
        name="⏰ **HORÁRIO DE ATENDIMENTO**",
        value="**Segunda a Sexta**\n\n**08:20 às 12:30**\n\n**13:30 às 18:20**",
        inline=False
    )
    embed.set_footer(text=f"Tickets são fechados automaticamente após {BOT_CONFIG['auto_close_hours']} horas sem atividade.")
    
    view = TicketView()
    await channel.send(embed=embed, view=view)


# ==================================================================================================
# COMANDOS (modules/commands/ticket_commands.py)
# ==================================================================================================

class TicketCommands(commands.Cog):
    """Cog com os comandos atualmente utilizados: /close e /setup_tickets."""

    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="setup_tickets", description="Configura o sistema de tickets em um canal")
    @discord.app_commands.describe(channel="Canal onde será postado o embed de tickets")
    async def setup_tickets(self, interaction: discord.Interaction, channel: discord.TextChannel):
        try:
            if not interaction.user.guild_permissions.manage_channels:
                await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
                return

            await interaction.response.defer()
            await setup_tickets_in_channel(self.bot, channel)

            await interaction.followup.send(f"✅ Configurado em {channel.mention}", ephemeral=True)

        except Exception as exc:
            logger.error(f"Erro setup_tickets: {exc}")
            await interaction.followup.send("❌ Erro ao configurar.", ephemeral=True)

    @discord.app_commands.command(name="close", description="Fechar ticket com status específico (apenas administradores)")
    async def close_ticket_with_status(self, interaction: discord.Interaction):
        try:
            channel = interaction.channel
            ticket = self.bot.db.get_ticket_by_channel(channel.id)

            if not ticket:
                await interaction.response.send_message("❌ Não é um canal de ticket.", ephemeral=True)
                return

            if ticket["status"] == "closed":
                await interaction.response.send_message("❌ Já fechado.", ephemeral=True)
                return

            user = interaction.user
            has_support_role = discord.utils.get(user.roles, name=BOT_CONFIG["support_role_name"]) is not None
            has_manage_channels = user.guild_permissions.manage_channels

            if not (has_support_role or has_manage_channels):
                await interaction.response.send_message("❌ Apenas administradores.", ephemeral=True)
                return

            view = CloseStatusView(ticket)
            await interaction.response.send_message(
                "📋 **Fechar Ticket**\n\nSelecione o status do ticket:",
                view=view,
                ephemeral=True,
            )
            schedule_ephemeral_deletion(interaction)

        except Exception as exc:
            logger.error(f"Erro close: {exc}")
            await interaction.response.send_message("❌ Erro ao fechar.", ephemeral=True)


# ==================================================================================================
# COMANDOS DE ALERTA (Novo Sistema)
# ==================================================================================================

class AlertModal(discord.ui.Modal):
    def __init__(self, color_code, mention_role, image_url, type_label):
        super().__init__(title="Criar Novo Alerta")
        self.color_code = color_code
        self.mention_role = mention_role
        self.image_url = image_url
        self.type_label = type_label

        self.alert_title = discord.ui.TextInput(
            label="Título do Alerta",
            placeholder="Ex: Instabilidade nos servidores",
            style=discord.TextStyle.short,
            required=True,
            max_length=256
        )
        self.alert_description = discord.ui.TextInput(
            label="Mensagem do Alerta",
            placeholder="Digite a mensagem detalhada...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=4000
        )
        self.add_item(self.alert_title)
        self.add_item(self.alert_description)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            
            embed = discord.Embed(
                title=self.alert_title.value,
                description=self.alert_description.value,
                color=self.color_code,
                timestamp=datetime.now()
            )
            
            if self.image_url:
                embed.set_image(url=self.image_url)
            
            embed.set_footer(text=f"Enviado por {interaction.user.display_name}")
            
            content = None
            if self.mention_role:
                # Menção em spoiler conforme solicitado
                content = f"||{self.mention_role.mention}||"

            await interaction.channel.send(content=content, embed=embed)
            await interaction.followup.send("✅ Alerta enviado com sucesso!", ephemeral=True)
            
        except Exception as e:
            logger.error(f"Erro ao enviar alerta: {e}")
            await interaction.followup.send("❌ Erro ao enviar alerta.", ephemeral=True)


class EditAlertModal(discord.ui.Modal):
    def __init__(self, message: discord.Message, current_color):
        super().__init__(title="Editar Alerta")
        self.message = message
        self.current_color = current_color
        
        current_embed = message.embeds[0]
        
        self.alert_title = discord.ui.TextInput(
            label="Título",
            default=current_embed.title,
            style=discord.TextStyle.short,
            required=True,
            max_length=256
        )
        self.alert_description = discord.ui.TextInput(
            label="Descrição",
            default=current_embed.description,
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=4000
        )
        self.add_item(self.alert_title)
        self.add_item(self.alert_description)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            
            # Criar novo embed baseado na edição
            embed = self.message.embeds[0]
            embed.title = self.alert_title.value
            embed.description = self.alert_description.value
            if self.current_color:
                embed.color = self.current_color
            embed.timestamp = datetime.now()  # Atualiza o horário para o do repost
            
            # Preservar o conteúdo da mensagem original (menção)
            content = self.message.content
            
            # Enviar NOVA mensagem (Repost)
            await interaction.channel.send(content=content, embed=embed)
            
            # Apagar a mensagem antiga
            await self.message.delete()
            
            await interaction.followup.send("✅ Alerta atualizado e reenviado!", ephemeral=True)
            
        except Exception as e:
            logger.error(f"Erro ao editar alerta: {e}")
            await interaction.followup.send("❌ Erro ao editar alerta.", ephemeral=True)


class AlertCommands(commands.Cog):
    """Comandos para gerenciamento de alertas e avisos."""

    def __init__(self, bot):
        self.bot = bot

    def _get_color_code(self, color_name: str) -> int:
        colors = {
            "🔴 Crítico/Erro": 0xff0000,
            "🟡 Aviso/Instabilidade": 0xffa500,
            "🟢 Resolvido": 0x00ff00,
            "🔵 Informativo": 0x0099ff,
            "⚪ Neutro": 0xffffff
        }
        return colors.get(color_name, 0x0099ff)

    @discord.app_commands.command(name="alert", description="Envia um embed de alerta customizado")
    @discord.app_commands.describe(
        cor="Cor da lateral do embed",
        mencao="Cargo ou usuário para mencionar (opcional)",
        imagem="URL de uma imagem para o embed (opcional)"
    )
    @discord.app_commands.choices(cor=[
        discord.app_commands.Choice(name="🔴 Crítico/Erro", value="🔴 Crítico/Erro"),
        discord.app_commands.Choice(name="🟡 Aviso/Instabilidade", value="🟡 Aviso/Instabilidade"),
        discord.app_commands.Choice(name="🟢 Resolvido", value="🟢 Resolvido"),
        discord.app_commands.Choice(name="🔵 Informativo", value="🔵 Informativo"),
        discord.app_commands.Choice(name="⚪ Neutro", value="⚪ Neutro")
    ])
    async def alert(self, interaction: discord.Interaction, cor: str, mencao: discord.Role = None, imagem: str = None):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ Apenas moderadores podem usar este comando.", ephemeral=True)
            return

        color_code = self._get_color_code(cor)
        modal = AlertModal(color_code, mencao, imagem, cor)
        await interaction.response.send_modal(modal)

    @discord.app_commands.command(name="update_alert", description="Edita um alerta existente")
    @discord.app_commands.describe(
        mensagem_id="ID da mensagem do alerta a ser editado",
        nova_cor="Alterar a cor do alerta (opcional)"
    )
    @discord.app_commands.choices(nova_cor=[
        discord.app_commands.Choice(name="🔴 Crítico/Erro", value="🔴 Crítico/Erro"),
        discord.app_commands.Choice(name="🟡 Aviso/Instabilidade", value="🟡 Aviso/Instabilidade"),
        discord.app_commands.Choice(name="🟢 Resolvido", value="🟢 Resolvido"),
        discord.app_commands.Choice(name="🔵 Informativo", value="🔵 Informativo")
    ])
    async def update_alert(self, interaction: discord.Interaction, mensagem_id: str, nova_cor: str = None):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ Apenas moderadores podem usar este comando.", ephemeral=True)
            return

        try:
            # Tentar converter ID
            try:
                msg_id = int(mensagem_id)
            except ValueError:
                await interaction.response.send_message("❌ ID inválido. Cole apenas o número do ID.", ephemeral=True)
                return

            # Buscar mensagem no canal atual
            try:
                message = await interaction.channel.fetch_message(msg_id)
            except discord.NotFound:
                await interaction.response.send_message("❌ Mensagem não encontrada neste canal.", ephemeral=True)
                return

            # Verificar se é mensagem do próprio bot e se tem embed
            if message.author != self.bot.user or not message.embeds:
                await interaction.response.send_message("❌ Essa mensagem não é um alerta válido do bot.", ephemeral=True)
                return

            color_code = self._get_color_code(nova_cor) if nova_cor else None
            modal = EditAlertModal(message, color_code)
            await interaction.response.send_modal(modal)

        except Exception as e:
            logger.error(f"Erro no update_alert: {e}")
            await interaction.response.send_message("❌ Erro interno.", ephemeral=True)

# ==================================================================================================
# BOT PRINCIPAL (app.py)
# ==================================================================================================

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
            logger.info("Iniciando setup...")
            
            if not self.db.init_database():
                logger.error("Falha na conexão com banco - continuando sem DB")
            else:
                logger.info("Banco conectado")
            
            await self.add_cog(TicketCommands(self))
            await self.add_cog(AlertCommands(self))
            
            logger.info("Sincronizando comandos...")
            try:
                synced = await self.tree.sync()
                logger.info(f"{len(synced)} comandos sincronizados")
            except Exception as e:
                logger.warning(f"Erro sync: {e}")
            
            logger.info("Adicionando views persistentes...")
            self.add_view(TicketView())
            self.add_view(TicketControlView())
            self.add_view(ReopenTicketView())
            
            self.auto_close_tickets.start()
            self.ensure_health_server()
            logger.info("✅ Setup concluído!")
            
        except Exception as e:
            logger.error(f"Erro setup: {e}")
    
    async def on_ready(self):
        try:
            startup_duration = (datetime.now() - self.startup_time).total_seconds()
            await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="tickets de suporte"))
            print(f"🟢 Bot {self.user} online - {startup_duration:.1f}s")
        except Exception as e:
            logger.error(f"Erro on_ready: {e}")
    
    @tasks.loop(minutes=BOT_CONFIG['auto_close_check_minutes'])
    async def auto_close_tickets(self):
        try:
            open_tickets = self.db.get_open_tickets()
            if not open_tickets: return
                
            now = datetime.now()
            auto_close_time = timedelta(hours=BOT_CONFIG['auto_close_hours'])
            
            for ticket in open_tickets:
                created_at = ticket['created_at']
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at)
                
                if now - created_at >= auto_close_time:
                    channel = self.get_channel(ticket['channel_id'])
                    if channel:
                        await close_ticket_channel(self, channel, auto_close=True)
                        
        except Exception as e:
            logger.error(f"Erro auto_close: {e}")
    
    @auto_close_tickets.before_loop
    async def before_auto_close(self):
        await self.wait_until_ready()
    
    def ensure_health_server(self):
        should_enable = os.environ.get("ENABLE_HEALTH_SERVER", "true").lower() in {"1", "true", "yes", "on"}
        if not should_enable: return
        if self._health_server_started: return
        self.start_health_server()
        self._log_panel_endpoint_response()

    def start_health_server(self):
        class HealthHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                try:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'OK')
                except Exception: pass
            def do_HEAD(self):
                try:
                    self.send_response(200)
                    self.end_headers()
                except Exception: pass
            def log_message(self, format, *args): pass
        
        port, port_source = self._resolve_health_port()
        port_candidates = [port, port + 1]
        
        def run_server():
            started = False
            for candidate in port_candidates:
                try:
                    server = HTTPServer(('0.0.0.0', candidate), HealthHandler)
                    self.health_server_port = candidate
                    started = True
                    logger.info(f"🌐 Server HTTP porta {candidate}")
                    server.serve_forever()
                    break
                except Exception: continue
            if not started: logger.error("❌ Falha ao iniciar server HTTP")
        
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        self._health_server_started = True
    
    def _resolve_health_port(self):
        env_candidates = ["HEALTH_SERVER_PORT", "BLAZE_HEALTH_PORT", "BLAZE_PORT", "PORT", "PORT0"]
        for var in env_candidates:
            if os.environ.get(var): return int(os.environ.get(var)), "env"
        return 25565, "default"
    
    def _log_panel_endpoint_response(self):
        endpoint = os.environ.get("BLAZE_PANEL_ENDPOINT", "http://sd-br2.blazebr.com:26244/")
        try:
            with request.urlopen(endpoint, timeout=5) as resp:
                logger.info(f"Painel respondeu {resp.status}")
        except Exception as e:
            logger.warning(f"Erro painel: {e}")

    def _print_startup_banner(self):
        print(f"\n🚀 Bot UpLink - Consolidated Startup\nTimestamp: {datetime.now()}")


def main():
    try:
        logger.info("Validando configuração...")
        validate_config()
        
        logger.info("Criando instância...")
        bot = OptimizedTicketBot()
        
        logger.info("Iniciando bot...")
        bot.run(DISCORD_TOKEN, log_handler=None)
        
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
