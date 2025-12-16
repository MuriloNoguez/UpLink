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
from dotenv import load_dotenv
from prisma import Prisma
import io
import random



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

# ==================================================================================================
# ==================================================================================================
# ==================================================================================================
# CONFIGURAÇÃO DE ANIVERSÁRIOS
# ==================================================================================================
BIRTHDAY_GIFS = [
    "https://i.pinimg.com/originals/a0/05/0b/a0050b555e8bc803006d64998df96102.gif",
    "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExbnZ4cmk1ZmV4eG14eG14eG14eG14eG14eG14eG14eG14eC9lcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/LvtKSk01C8m4/giphy.gif",
    "https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExb3NqM3NqM3NqM3NqM3NqM3NqM3NqM3NqM3NqM3NqM3M9Zw/SwIMZUJE3ZPpHAfTC4/giphy.gif",
    "https://media.tenor.com/P0G_M0s0d8oAAAAC/happy-birthday.gif",
    "https://media.tenor.com/I2C36531QzYAAAAC/happy-birthday-to-you.gif"
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
    def __init__(self, prisma: Prisma):
        self.prisma = prisma

    async def init_database(self):
        # Prisma handles schema via 'prisma db push' or migrations.
        # This is kept for compatibility flow, but does nothing or just logs.
        logger.info("Prisma ORM active.")
        return True

    def get_connection(self):
        # Not needed with Prisma
        return None

    async def add_ticket(self, user_id: int, user_name: str, channel_id: int, reason: str, description: str) -> Optional[int]:
        try:
            ticket = await self.prisma.tickets.create(
                data={
                    'user_id': user_id,
                    'user_name': user_name,
                    'channel_id': channel_id,
                    'reason': reason,
                    'description': description,
                    'status': 'open'
                }
            )
            logger.info(f"Ticket criado: {ticket.id} para {user_name}")
            return ticket.id
        except Exception as e:
            logger.error(f"Erro ao criar ticket: {e}")
            return None

    async def create_ticket(self, user_id: int, user_name: str, channel_id: int, reason: str, description: str) -> Optional[int]:
        # Alias for add_ticket to match usage
        return await self.add_ticket(user_id, user_name, channel_id, reason, description)

    async def get_ticket(self, ticket_id: int) -> Optional[Dict[str, Any]]:
        try:
            ticket = await self.prisma.tickets.find_unique(where={'id': ticket_id})
            return ticket.model_dump() if ticket else None
        except Exception as e:
            logger.error(f"Erro ao buscar ticket {ticket_id}: {e}")
            return None

    async def get_ticket_by_channel(self, channel_id: int) -> Optional[Dict[str, Any]]:
        try:
            ticket = await self.prisma.tickets.find_first(
                where={'channel_id': channel_id},
                order={'id': 'desc'}
            )
            return ticket.model_dump() if ticket else None
        except Exception as e:
            logger.error(f"Erro ao buscar ticket do canal {channel_id}: {e}")
            return None
    
    async def get_user_tickets(self, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        try:
             tickets = await self.prisma.tickets.find_many(
                 where={'user_id': user_id},
                 order={'created_at': 'desc'},
                 take=limit
             )
             return [t.model_dump() for t in tickets]
        except Exception as e:
            logger.error(f"Erro ao buscar tickets do usuário {user_id}: {e}")
            return []

    async def get_user_latest_ticket(self, user_id: int) -> Optional[Dict[str, Any]]:
        try:
            ticket = await self.prisma.tickets.find_first(
                where={'user_id': user_id},
                order={'id': 'desc'}
            )
            return ticket.model_dump() if ticket else None
        except Exception as e:
             logger.error(f"Erro ao buscar ultimo ticket do usuario {user_id}: {e}")
             return None

    async def close_ticket(self, channel_id: int) -> bool:
         # Custom method to match the logic of just changing status?
         try:
             # Find ticket by channel first
             ticket = await self.get_ticket_by_channel(channel_id)
             if not ticket: return False
             
             await self.prisma.tickets.update(
                 where={'id': ticket['id']},
                 data={'status': 'closed', 'closed_at': datetime.now()}
             )
             logger.info(f"Ticket do canal {channel_id} fechado.")
             return True
         except Exception as e:
             logger.error(f"Erro ao fechar ticket (status) channel {channel_id}: {e}")
             return False

    async def reopen_ticket(self, channel_id: int, reason: str, description: str) -> Optional[int]:
        try:
             # Find latest ticket for channel
             ticket = await self.get_ticket_by_channel(channel_id)
             if not ticket: return None
             
             updated = await self.prisma.tickets.update(
                 where={'id': ticket['id']},
                 data={
                     'status': 'open',
                     'reason': reason,
                     'description': description,
                     'closed_at': None,
                     'paused_at': None,
                     'paused_by': None,
                     'created_at': datetime.now() # Reset created_at? Original did this.
                 }
             )
             logger.info(f"Ticket {ticket['id']} reaberto.")
             return updated.id
        except Exception as e:
            logger.error(f"Erro ao reabrir ticket do canal {channel_id}: {e}")
            return None

    async def pause_ticket(self, channel_id: int, paused_by: str) -> bool:
        try:
             ticket = await self.get_ticket_by_channel(channel_id)
             if not ticket or ticket['status'] != 'open': return False
             
             await self.prisma.tickets.update(
                 where={'id': ticket['id']},
                 data={
                     'status': 'paused',
                     'paused_at': datetime.now(),
                     'paused_by': paused_by
                 }
             )
             return True
        except Exception as e:
            logger.error(f"Erro ao pausar ticket do canal {channel_id}: {e}")
            return False

    async def unpause_ticket(self, channel_id: int) -> bool:
        try:
             ticket = await self.get_ticket_by_channel(channel_id)
             if not ticket or ticket['status'] != 'paused': return False
             
             await self.prisma.tickets.update(
                 where={'id': ticket['id']},
                 data={
                     'status': 'open',
                     'paused_at': None,
                     'paused_by': None
                 }
             )
             return True
        except Exception as e:
             logger.error(f"Erro ao despausar ticket do canal {channel_id}: {e}")
             return False

    async def get_open_tickets(self) -> List[Dict[str, Any]]:
        try:
            tickets = await self.prisma.tickets.find_many(
                where={'status': 'open'},
                order={'created_at': 'asc'}
            )
            return [t.model_dump() for t in tickets]
        except Exception as e:
            logger.error(f"Erro ao buscar tickets abertos: {e}")
            return []

    async def get_ticket_stats(self) -> Dict[str, int]:
        try:
            total = await self.prisma.tickets.count()
            open_count = await self.prisma.tickets.count(where={'status': 'open'})
            closed_count = await self.prisma.tickets.count(where={'status': 'closed'})
            paused_count = await self.prisma.tickets.count(where={'status': 'paused'})
            return {"total": total, "open": open_count, "closed": closed_count, "paused": paused_count}
        except Exception as e:
            logger.error(f"Erro ao buscar stats: {e}")
            return {"total": 0, "open": 0, "closed": 0, "paused": 0}

    async def add_birthday(self, user_id: int, day: int, month: int) -> bool:
        try:
            await self.prisma.birthday.upsert(
                where={'user_id': user_id},
                data={
                    'create': {'user_id': user_id, 'day': day, 'month': month},
                    'update': {'day': day, 'month': month}
                }
            )
            return True
        except Exception as e:
            logger.error(f"Erro ao adicionar aniversario: {e}")
            return False

    async def remove_birthday(self, user_id: int) -> bool:
        try:
            await self.prisma.birthday.delete(where={'user_id': user_id})
            return True
        except Exception as e:
            return False

    async def get_birthdays_by_date(self, day: int, month: int) -> List[int]:
        try:
            birthdays = await self.prisma.birthday.find_many(
                where={'day': day, 'month': month}
            )
            return [int(b.user_id) for b in birthdays]
        except Exception as e:
            logger.error(f"Erro ao buscar aniversariantes: {e}")
            return []
    
    async def get_all_birthdays(self) -> List[Dict[str, Any]]:
        try:
            birthdays = await self.prisma.birthday.find_many()
            return [{'user_id': int(b.user_id), 'day': b.day, 'month': b.month} for b in birthdays]
        except Exception as e:
             logger.error(f"Erro ao listar todos aniversarios: {e}")
             return []

    async def get_birthday(self, user_id: int) -> Optional[Dict[str, Any]]:
        try:
            birthday = await self.prisma.birthday.find_unique(where={'user_id': user_id})
            if birthday:
                return {'user_id': int(birthday.user_id), 'day': birthday.day, 'month': birthday.month}
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar aniversario do usuario {user_id}: {e}")
            return None


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
        ticket = await bot.db.get_ticket_by_channel(channel.id)
        await bot.db.close_ticket(channel.id)
        
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
            user_tickets = await interaction.client.db.get_user_tickets(interaction.user.id, 5)
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
            ticket = await interaction.client.db.get_ticket_by_channel(interaction.channel.id)
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
        latest_ticket = await interaction.client.db.get_user_latest_ticket(user.id)
        if latest_ticket:
            channel = guild.get_channel(latest_ticket["channel_id"])
            if channel:
                # Reopen Logic inline
                ticket_id = await interaction.client.db.reopen_ticket(channel.id, self.reason, self.description.value)
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
        
        ticket_id = await interaction.client.db.create_ticket(
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
# =================================================================================================G

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
            ticket = await self.bot.db.get_ticket_by_channel(channel.id)

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

class BirthdayCommands(commands.Cog):
    """Comandos para gerenciamento de Aniversários."""
    
    def __init__(self, bot):
        self.bot = bot
        self.check_birthdays.start()
        self.last_check_date = None

    def cog_unload(self):
        self.check_birthdays.cancel()

    @discord.app_commands.command(name="niver", description="Gerenciar aniversários")
    @discord.app_commands.describe(
        acao="Ação a realizar: cadastrar, remover, ver",
        dia="Dia do nascimento (1-31)",
        mes="Mês do nascimento (1-12)",
        usuario="Usuário alvo (Opcional - Apenas Moderadores)"
    )
    @discord.app_commands.choices(acao=[
        discord.app_commands.Choice(name="Cadastrar", value="cadastrar"),
        discord.app_commands.Choice(name="Remover", value="remover"),
        discord.app_commands.Choice(name="Ver", value="ver")
    ])
    async def niver(self, interaction: discord.Interaction, acao: str, dia: int = None, mes: int = None, usuario: discord.User = None):
        target_user = usuario or interaction.user
        
        # Verificar permissão se for para outro usuário
        if usuario and usuario != interaction.user:
             if not interaction.user.guild_permissions.manage_messages:
                 await interaction.response.send_message("❌ Apenas moderadores podem gerenciar aniversários de outros.", ephemeral=True)
                 return

        if acao == "cadastrar":
            if not dia or not mes:
                await interaction.response.send_message("❌ Informe o dia e o mês!", ephemeral=True)
                return
            
            try:
                datetime(2024, mes, dia) # Validação simples
            except ValueError:
                await interaction.response.send_message("❌ Data incorreta!", ephemeral=True)
                return

            success = await self.bot.db.add_birthday(target_user.id, dia, mes)
            
            if success:
                msg = f"✅ Aniversário cadastrado para **{dia:02d}/{mes:02d}**"
                if target_user.id != interaction.user.id:
                    msg += f" (Usuário: {target_user.mention})"
                
                # Try/Except para lidar com interação já respondida (caso raro, mas preventivo)
                try:
                    await interaction.response.send_message(msg, ephemeral=True)
                except discord.InteractionResponded:
                    await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message("❌ Erro ao salvar no banco.", ephemeral=True)

        elif acao == "remover":
            await self.bot.db.remove_birthday(target_user.id)
            msg = "✅ Aniversário removido."
            if target_user.id != interaction.user.id:
                msg = f"✅ Aniversário de {target_user.mention} removido."
            await interaction.response.send_message(msg, ephemeral=True)

        elif acao == "ver":
             bday = await self.bot.db.get_birthday(target_user.id)
             if bday:
                 if target_user.id == interaction.user.id:
                     msg = f"🎂 Seu aniversário é dia **{bday['day']:02d}/{bday['month']:02d}**."
                 else:
                     msg = f"🎂 O aniversário de {target_user.mention} é dia **{bday['day']:02d}/{bday['month']:02d}**."
                 
                 await interaction.response.send_message(msg, ephemeral=True)
             else:
                 msg = "❌ Você não tem aniversário cadastrado."
                 if target_user.id != interaction.user.id:
                     msg = f"❌ {target_user.mention} não tem aniversário cadastrado."
                 await interaction.response.send_message(msg, ephemeral=True)

    @discord.app_commands.command(name="simular_niver", description="Simula um anúncio de aniversário (Admin)")
    @discord.app_commands.describe(usuario="Usuário para simular (Opcional)")
    async def simular_niver(self, interaction: discord.Interaction, usuario: discord.User = None):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Apenas administradores.", ephemeral=True)
            return

        target = usuario or interaction.user
        
        # Escolher GIF
        gif_url = random.choice(BIRTHDAY_GIFS) if BIRTHDAY_GIFS else None
        
        embed = discord.Embed(
            title=f"🎉 Feliz Aniversário, {target.display_name}! 🎂",
                description=f"Hoje é o dia de celebrar mais um ano de vida de {target.mention}!\n\n**Parabéns! Que seu dia seja incrível!** 🥳🎈",
                color=0xFFD700
        )
        if gif_url:
            embed.set_image(url=gif_url)
        
        # Envia no canal onde o comando foi usado
        await interaction.response.send_message(content=f"@everyone Hoje é o dia de {target.mention}! 🎉", embed=embed)

    @tasks.loop(minutes=1)
    async def check_birthdays(self):
        # A cada minuto, verifica se é 08:30 (horario local do servidor)
        now = datetime.now()
        
        # Evitar múltiplas execuções no mesmo dia/horário se o loop correr rápido (improvável com minutes=1, mas seguro)
        if self.last_check_date == now.date() and getattr(self, "last_check_hour", -1) == 8:
             # Já rodou hoje às 8?
             # Se rodou às 8:30, não roda mais.
             # Mas precisamos garantir que é exatamente 8:30
             pass
        
        if now.hour == 8 and now.minute == 30:
            if self.last_check_date == now.date():
                return
            
            self.last_check_date = now.date()
            await self.announce_birthdays(now.day, now.month)

    async def announce_birthdays(self, day, month):
        user_ids = await self.bot.db.get_birthdays_by_date(day, month)
        if not user_ids: return

        # Escolher GIF
        gif_url = random.choice(BIRTHDAY_GIFS) if BIRTHDAY_GIFS else None
        
        for guild in self.bot.guilds:
            # Encontrar canal
            target_channel = discord.utils.get(guild.text_channels, name="aniversários")
            if not target_channel:
                 target_channel = discord.utils.get(guild.text_channels, name="chat-geral")
            if not target_channel:
                 target_channel = discord.utils.get(guild.text_channels, name="geral")
            if not target_channel:
                continue # Sem canal, sem anúncio
            
            for uid in user_ids:
                member = guild.get_member(uid)
                if member:
                    embed = discord.Embed(
                        title=f"🎉 Feliz Aniversário, {member.display_name}! 🎂",
                         description=f"Hoje é o dia de celebrar mais um ano de vida de {member.mention}!\n\n**Parabéns! Que seu dia seja incrível!** 🥳🎈",
                         color=0xFFD700
                    )
                    if gif_url:
                        embed.set_image(url=gif_url)
                    
                    await target_channel.send(content=f"@everyone Hoje é o dia de {member.mention}! 🎉", embed=embed)
                    await asyncio.sleep(1) # Delay leve


# ==================================================================================================
# BOT PRINCIPAL (app.py)
# ==================================================================================================

class OptimizedTicketBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True  # Ensure guild intents are enabled
        
        super().__init__(command_prefix=BOT_CONFIG['command_prefix'], intents=intents)
        
        self.prisma = Prisma() # Instancia cliente Prisma
        self.db = DatabaseManager(self.prisma) # Passa para o Manager
        self.startup_time = datetime.now()
        self._health_server_started = False
        self.health_server_port = None
        
    async def setup_hook(self):
        try:
            # Conexão Prisma
            await self.prisma.connect()
            logger.info("Prisma conectado.")
            
            # Cogs
            await self.add_cog(TicketCommands(self))
            await self.add_cog(AlertCommands(self))
            await self.add_cog(BirthdayCommands(self))

            # Sync Comandos
            logger.info("Sincronizando comandos...")
            await self.tree.sync()
            
            # Views
            logger.info("Adicionando views persistentes...")
            self.add_view(TicketView())
            self.add_view(TicketControlView())
            self.add_view(ReopenTicketView())
            
            # Tasks e Servidor
            self.auto_close_tickets.start()
            self.ensure_health_server()
            logger.info("✅ Setup concluído!")
            
        except Exception as e:
            logger.error(f"Erro setup: {e}")

    async def close(self):
        if self.prisma.is_connected():
            await self.prisma.disconnect()
            logger.info("Prisma desconectado.")
        await super().close()
    
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
            open_tickets = await self.db.get_open_tickets()
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
