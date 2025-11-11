"""
Utilitários e funções auxiliares para o sistema de tickets.
"""

import logging
import asyncio
from datetime import datetime

import discord

from config import EMBED_COLORS, BOT_CONFIG

logger = logging.getLogger(__name__)


def resolve_emoji(bot: discord.Client, emoji_str: str, guild: discord.Guild = None):
    """
    Resolve um emoji string para um objeto emoji do Discord.
    
    Args:
        bot: Cliente do bot
        emoji_str: String do emoji (nome, <:name:id>, ou unicode)
        guild: Guild onde buscar emojis customizados
    
    Returns:
        Objeto emoji válido ou a string original
    """
    # Se já estiver no formato <:name:id> ou <a:name:id>
    try:
        if emoji_str.startswith('<'):
            return discord.PartialEmoji.from_str(emoji_str)
    except Exception:
        pass

    # Tentar achar por nome no guild atual
    if guild:
        e = discord.utils.get(guild.emojis, name=emoji_str)
        if e:
            return e

    # Tentar achar globalmente entre emojis que o bot pode ver
    e = discord.utils.get(bot.emojis, name=emoji_str)
    if e:
        return e

    # Fallback: retornar o próprio string (para emojis unicode)
    return emoji_str


async def close_ticket_channel(bot, channel: discord.TextChannel, auto_close: bool = False):
    """
    Fecha um canal de ticket (mas não o exclui, apenas muda permissões).
    
    Args:
        bot: Instância do bot
        channel: Canal a ser fechado
        auto_close: Se é fechamento automático
    """
    try:
        # Atualizar no banco
        bot.db.close_ticket(channel.id)
        
        # Modificar permissões do canal
        guild = channel.guild
        everyone_role = guild.default_role
        
        # Buscar o dono do ticket
        ticket = bot.db.get_ticket_by_channel(channel.id)
        if ticket:
            ticket_owner = guild.get_member(ticket['user_id'])
            if ticket_owner:
                # Tornar somente leitura para o dono
                await channel.set_permissions(
                    ticket_owner, 
                    send_messages=False,
                    add_reactions=False,
                    view_channel=True
                )
                # Pequeno delay para evitar rate limit
                await asyncio.sleep(0.5)
        
        # Tornar somente leitura para @everyone
        await channel.set_permissions(
            everyone_role, 
            send_messages=False,
            add_reactions=False
        )
        
        # Delay antes de renomear
        await asyncio.sleep(1)
        
        # Renomear canal com emoji de cadeado (apenas se não estiver já fechado)
        if not channel.name.startswith("🔒"):
            new_name = f"🔒{channel.name}"
            try:
                await channel.edit(name=new_name)
            except discord.HTTPException as e:
                if e.status == 429:  # Rate limited
                    logger.warning(f"Rate limited ao renomear canal {channel.name}, pulando renomeação")
                else:
                    raise
        
        # Enviar mensagem de fechamento
        embed = discord.Embed(
            title="🔒 **TICKET FECHADO**",
            description="**Este ticket foi fechado e está agora em modo somente leitura.**\n\n"
                       "**Histórico Preservado:** Todo o histórico foi mantido.\n\n"
                       "**Reabertura:** Use o botão abaixo para reabrir este ticket.",
            color=EMBED_COLORS['closed'],
            timestamp=datetime.now()
        )
        
        if auto_close:
            embed.add_field(
                name="⏰ **Motivo**",
                value=f"**Fechamento automático após {BOT_CONFIG['auto_close_hours']} horas**",
                inline=False
            )
        
        # Importar e usar a view de reabertura
        from modules.ui.views import ReopenTicketView
        reopen_view = ReopenTicketView()
        
        await channel.send(embed=embed, view=reopen_view)
        
    except Exception as e:
        logger.error(f"Erro ao fechar canal {channel.id}: {e}")


async def setup_tickets_in_channel(bot, channel: discord.TextChannel):
    """Configura o sistema de tickets em um canal específico."""
    from modules.ui.views import TicketView
    
    # Criar embed do sistema de tickets
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
        value=(
            "**Segunda a Sexta**\n\n"
            "**08:20 às 12:30**\n\n"
            "**13:30 às 18:20**"
        ),
        inline=False
    )
    
    embed.set_footer(
        text=f"Tickets são fechados automaticamente após {BOT_CONFIG['auto_close_hours']} horas sem atividade."
    )
    
    # Enviar mensagem com view persistente
    view = TicketView()
    await channel.send(embed=embed, view=view)


async def auto_setup_tickets(bot):
    """Configura automaticamente o sistema de tickets em canais específicos."""
    try:
        for guild in bot.guilds:
            # Procurar por canais com nomes relacionados a suporte
            target_channel = None
            
            for channel_name in BOT_CONFIG['channel_names_to_setup']:
                target_channel = discord.utils.get(guild.text_channels, name=channel_name)
                if target_channel:
                    break
            
            # Se não encontrar, criar um canal 'suporte'
            if not target_channel:
                try:
                    target_channel = await guild.create_text_channel(
                        name='suporte',
                        topic='Canal para abertura de tickets de suporte técnico',
                        reason='Canal criado automaticamente pelo bot de tickets'
                    )
                    logger.info(f"Canal 'suporte' criado no servidor {guild.name}")
                except Exception as e:
                    logger.error(f"Não foi possível criar canal no servidor {guild.name}: {e}")
                    continue
            
            if target_channel:
                # Verificar se já existe uma mensagem do bot no canal
                async for message in target_channel.history(limit=50):
                    if message.author == bot.user and message.embeds:
                        embed = message.embeds[0]
                        if "Sistema de Tickets" in str(embed.title):
                            logger.info(f"Sistema já configurado no {target_channel.name} ({guild.name})")
                            return
                
                # Configurar o sistema
                await setup_tickets_in_channel(bot, target_channel)
                logger.info(f"Sistema configurado automaticamente no {target_channel.name} ({guild.name})")
                
    except Exception as e:
        logger.error(f"Erro no auto-setup: {e}")


def format_timestamp(dt):
    """Formata datetime para timestamp do Discord."""
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    return f"<t:{int(dt.timestamp())}:R>"