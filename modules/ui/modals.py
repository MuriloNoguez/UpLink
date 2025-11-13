"""
Modais para interação com o usuário no sistema de tickets.
"""

import logging
import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import discord

from config import TICKET_REASONS, BOT_CONFIG
from .views import TicketControlView
from utils.helpers import resolve_emoji, schedule_ephemeral_deletion

logger = logging.getLogger(__name__)

# Mapeamento entre permissões do Discord e o nome legível que repassamos ao usuário.
REQUIRED_TICKET_PERMISSIONS = {
    "manage_channels": "Manage Channels",
    "send_messages": "Send Messages",
    "embed_links": "Embed Links",
    "attach_files": "Attach Files",
}


def _build_reason_options(bot: Optional[discord.Client], guild: Optional[discord.Guild]) -> List[discord.SelectOption]:
    """Cria a lista de opções do select a partir das razões configuradas."""
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


@dataclass
class TicketChannelContext:
    """Representa o resultado da preparação do canal de ticket."""

    channel: discord.TextChannel
    ticket_id: Optional[int]
    is_reopened: bool = False
    skip_intro_embed: bool = False


class ReasonSelect(discord.ui.Select):
    """Select menu para escolha do motivo do ticket."""
    
    def __init__(self, bot=None, guild=None):
        self.bot = bot
        self.guild = guild
        
        super().__init__(
            placeholder="Selecione o motivo do seu chamado...",
            options=_build_reason_options(bot, guild),
            custom_id="ticket_reason_select"
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Callback executado quando uma opção é selecionada."""
        try:
            reason = self.values[0]
            modal = DescriptionModal(reason)
            await interaction.response.send_modal(modal)
            
        except Exception as e:
            logger.error(f"Erro no callback do select: {e}")
            message = await interaction.followup.send(
                "❌ Ocorreu um erro. Tente novamente.",
                ephemeral=True
            )
            schedule_ephemeral_deletion(interaction, message)


class DescriptionModal(discord.ui.Modal):
    """Modal para capturar a descrição do problema."""
    
    def __init__(self, reason: str):
        super().__init__(title=f"Novo Ticket - {reason}")
        self.reason = reason
        
        self.description = discord.ui.TextInput(
            label="Descrição do Problema",
            placeholder="Descreva o problema com detalhes (passos, erros). Após criar, anexe prints/arquivos no canal.",
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True
        )
        self.add_item(self.description)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Callback executado quando o modal é enviado."""
        try:
            await interaction.response.defer(ephemeral=True)
            guild = interaction.guild
            user = interaction.user

            if not guild:
                await interaction.followup.send(
                    "❌ Este recurso só pode ser usado dentro de um servidor.",
                    ephemeral=True,
                )
                return

            missing_permissions = self._collect_missing_permissions(guild)
            if missing_permissions:
                await self._notify_missing_permissions(interaction, guild, missing_permissions)
                return

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
            self._log_ticket_creation(context, user)

        except Exception as exc:
            await self._handle_creation_error(interaction, exc)

    def _collect_missing_permissions(self, guild: discord.Guild) -> List[str]:
        """Retorna a lista de permissões faltantes para o bot."""
        try:
            bot_member = guild.me
            bot_perms = bot_member.guild_permissions if bot_member else None
        except Exception:
            bot_perms = None

        missing: List[str] = []
        for attr, label in REQUIRED_TICKET_PERMISSIONS.items():
            if not bot_perms or not getattr(bot_perms, attr, False):
                missing.append(label)
        return missing

    async def _notify_missing_permissions(
        self,
        interaction: discord.Interaction,
        guild: discord.Guild,
        missing: List[str],
    ) -> None:
        perms_list = ", ".join(missing)
        logger.error("Bot sem permissões necessárias no servidor %s: %s", guild.name, perms_list)
        message = await interaction.followup.send(
            f"❌ O bot não possui permissões necessárias neste servidor: {perms_list}. "
            "Peça a um administrador para conceder essas permissões ao cargo do bot e tente novamente.",
            ephemeral=True,
        )
        schedule_ephemeral_deletion(interaction, message)

    async def _prepare_channel(
        self,
        interaction: discord.Interaction,
        guild: discord.Guild,
        user: discord.Member,
    ) -> Optional[TicketChannelContext]:
        """Decide se o ticket deve ser reaberto ou criado e retorna o contexto do canal."""
        latest_ticket = interaction.client.db.get_user_latest_ticket(user.id)
        if latest_ticket:
            channel = guild.get_channel(latest_ticket["channel_id"])
            if channel:
                return await self._reopen_existing_ticket(interaction, user, channel)

        return await self._create_channel_with_ticket(interaction, guild, user)

    async def _reopen_existing_ticket(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        channel: discord.TextChannel,
    ) -> Optional[TicketChannelContext]:
        """Reabre um ticket existente e envia a mensagem informativa."""
        ticket_id = interaction.client.db.reopen_ticket(
            channel.id,
            self.reason,
            self.description.value,
        )
        if not ticket_id:
            return None

        logger.info("Reabrindo ticket existente para %s no canal %s", user, channel.name)
        embed = self._build_reopen_embed(user)
        control_view = TicketControlView()

        await channel.send(
            content=self._build_ticket_opening_content(user, True),
            embed=embed,
            view=control_view,
        )
        self._restore_user_permissions(channel, user)

        return TicketChannelContext(
            channel=channel,
            ticket_id=ticket_id,
            is_reopened=True,
            skip_intro_embed=True,
        )

    async def _create_channel_with_ticket(
        self,
        interaction: discord.Interaction,
        guild: discord.Guild,
        user: discord.Member,
    ) -> Optional[TicketChannelContext]:
        """Cria um novo canal de ticket e registra no banco."""
        category = discord.utils.get(guild.categories, name=BOT_CONFIG["tickets_category_name"])
        if not category:
            category = await guild.create_category(
                name=BOT_CONFIG["tickets_category_name"],
                reason="Categoria criada automaticamente pelo bot de tickets",
            )
            logger.info(
                "Categoria '%s' criada no servidor %s",
                BOT_CONFIG["tickets_category_name"],
                guild.name,
            )

        overwrites = self._build_channel_overwrites(guild, user)
        channel_name = f"💻┃{user.name.lower()}"
        channel = await category.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            reason=f"Ticket criado por {user}",
        )

        ticket_id = interaction.client.db.create_ticket(
            user_id=user.id,
            user_name=str(user),
            channel_id=channel.id,
            reason=self.reason,
            description=self.description.value,
        )

        return TicketChannelContext(channel=channel, ticket_id=ticket_id)

    def _build_channel_overwrites(
        self,
        guild: discord.Guild,
        user: discord.Member,
    ) -> dict:
        """Monta as permissões padrão do canal do ticket."""
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                attach_files=True,
                embed_links=True,
            ),
        }

        if guild.me:
            overwrites[guild.me] = discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                manage_messages=True,
                embed_links=True,
            )

        for member in guild.members:
            if member.guild_permissions.administrator and not member.bot:
                overwrites[member] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                    embed_links=True,
                )

        return overwrites

    def _build_reopen_embed(self, user: discord.Member) -> discord.Embed:
        """Cria o embed específico para reaberturas."""
        embed = discord.Embed(
            title="🔄 Ticket Reaberto",
            description="Seu ticket foi reaberto com uma nova solicitação!",
            color=0xFFA500,
            timestamp=datetime.now(),
        )
        embed.add_field(name="👤 Usuário", value=user.mention, inline=True)
        embed.add_field(name="🏷️ Motivo", value=self.reason, inline=True)
        embed.add_field(
            name="📅 Data",
            value=f"`{datetime.now().strftime('%d/%m/%Y %H:%M')}`",
            inline=True,
        )
        embed.add_field(name="📝 Nova Descrição:", value=self.description.value, inline=False)
        embed.add_field(
            name="📜 Histórico Preservado",
            value="Todo o histórico anterior foi mantido. Scroll para cima para ver conversas anteriores.",
            inline=False,
        )
        return embed

    @staticmethod
    def _restore_user_permissions(channel: discord.TextChannel, user: discord.Member) -> None:
        """Restaura permissões de envio para o usuário após reabrir o ticket."""

        async def update_channel_async():
            try:
                await channel.set_permissions(
                    user,
                    send_messages=True,
                    add_reactions=True,
                    view_channel=True,
                )
            except Exception as exc:
                logger.warning("Erro ao atualizar canal após reabertura: %s", exc)

        asyncio.create_task(update_channel_async())

    def _build_ticket_embed(
        self,
        user: discord.Member,
        description: str,
        is_reopened: bool,
    ) -> discord.Embed:
        """Gera o embed padrão com as informações do ticket."""
        if is_reopened:
            embed = discord.Embed(
                title="🔄 Ticket Reaberto",
                description="Seu ticket foi reaberto com uma nova solicitação!",
                color=0xFFA500,
                timestamp=datetime.now(),
            )
            embed.add_field(
                name="📜 Histórico Preservado",
                value="Este é seu canal de ticket pessoal. Todo o histórico anterior foi mantido.",
                inline=False,
            )
        else:
            embed = discord.Embed(
                title="🎫 Novo Ticket de Suporte",
                description="Seu ticket foi criado com sucesso!",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

        embed.add_field(name="👤 Usuário", value=user.mention, inline=True)
        embed.add_field(name="🏷️ Motivo", value=self.reason, inline=True)
        embed.add_field(
            name="📅 Data",
            value=f"`{datetime.now().strftime('%d/%m/%Y %H:%M')}`",
            inline=True,
        )
        embed.add_field(name="📝 Descrição:", value=description, inline=False)
        embed.add_field(
            name="📎 Anexos e Arquivos",
            value="💡 Adicione anexos abaixo para ajudar na resolução do problema, links, fotos...",
            inline=False,
        )
        if is_reopened:
            embed.add_field(
                name="⚠️ Importante",
                value="Este ticket foi reaberto. Scroll para cima para ver conversas anteriores.",
                inline=False,
            )
            embed.set_footer(
                text="Este é seu canal pessoal de ticket. Será fechado automaticamente em 12 horas se não houver atividade.",
            )
        else:
            embed.set_footer(
                text="Este ticket será fechado automaticamente em 12 horas se não houver atividade.",
            )
        return embed

    @staticmethod
    def _build_ticket_opening_content(user: discord.Member, is_reopened: bool) -> str:
        """Mensagem textual enviada junto do embed no canal do ticket."""
        action = "reaberto" if is_reopened else "criado"
        return (
            f"🔔 **{user.mention}, seu ticket foi {action}!**\n"
            "📞 <@&1382008028517109832> responderá em breve."
        )

    async def _send_ephemeral_confirmation(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        is_reopened: bool,
    ) -> None:
        """Responde ao usuário em DM com o link do ticket."""
        embed = self._build_ephemeral_embed(channel, is_reopened)
        message = await interaction.followup.send(embed=embed, ephemeral=True)
        schedule_ephemeral_deletion(interaction, message, delay=120)

    def _build_ephemeral_embed(self, channel: discord.TextChannel, is_reopened: bool) -> discord.Embed:
        """Cria o embed de confirmação usado nas respostas ephemerals."""
        if is_reopened:
            embed = discord.Embed(
                title="🔄 Ticket Reaberto com Sucesso!",
                description=f"Seu ticket foi reaberto no canal {channel.mention}",
                color=0xFFA500,
            )
            embed.add_field(
                name="📜 Histórico Mantido:",
                value="Todas as conversas anteriores foram preservadas no canal.",
                inline=False,
            )
        else:
            embed = discord.Embed(
                title="🎫 Ticket Criado com Sucesso!",
                description=f"Seu ticket foi criado no canal {channel.mention}",
                color=0x00FF00,
            )

        embed.add_field(
            name="📍 Próximo passo:",
            value=f"**[Clique aqui para acessar seu ticket](<https://discord.com/channels/{channel.guild.id}/{channel.id}>)**",
            inline=False,
        )
        embed.add_field(
            name="💡 Dica:",
            value="Você também pode acessar através da lista de canais na lateral esquerda",
            inline=False,
        )
        return embed

    async def _notify_creation_failure(self, interaction: discord.Interaction) -> None:
        """Envia uma mensagem amigável quando não foi possível criar o ticket."""
        message = await interaction.followup.send("❌ Erro ao criar ticket. Tente novamente.", ephemeral=True)
        schedule_ephemeral_deletion(interaction, message)

    def _log_ticket_creation(self, context: TicketChannelContext, user: discord.Member) -> None:
        """Registra no log o resultado da criação do ticket."""
        action = "reaberto" if context.is_reopened else "criado"
        logger.info("Ticket %s %s por %s no canal %s", context.ticket_id, action, user, context.channel.name)

    async def _handle_creation_error(self, interaction: discord.Interaction, error: Exception) -> None:
        """Garante que o usuário seja notificado caso algo falhe inesperadamente."""
        logger.error("Erro ao criar ticket: %s", error)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Ocorreu um erro. Tente novamente.", ephemeral=True)
                schedule_ephemeral_deletion(interaction)
            else:
                message = await interaction.followup.send("❌ Ocorreu um erro. Tente novamente.", ephemeral=True)
                schedule_ephemeral_deletion(interaction, message)
        except Exception:
            logger.exception("Falha ao notificar usuário sobre erro no select")


class ReasonSelectView(discord.ui.View):
    """View temporária para seleção do motivo."""
    
    def __init__(self, bot=None, guild=None):
        super().__init__(timeout=300)  # 5 minutos
        self.add_item(ReasonSelect(bot, guild))


class CloseStatusSelect(discord.ui.Select):
    """Select menu para escolha do status do ticket fechado."""
    
    def __init__(self, ticket):
        self.ticket = ticket
        
        options = [
            discord.SelectOption(
                label="Resolvido",
                description="Problema foi resolvido",
                emoji="✅",
                value="resolvido"
            ),
            discord.SelectOption(
                label="Chamado Aberto",
                description="Chamado foi aberto em sistema externo",
                emoji="📞",
                value="chamado_aberto"
            ),
            discord.SelectOption(
                label="Aguardando Resposta",
                description="Aguardando resposta do usuário",
                emoji="⏳",
                value="aguardando_resposta"
            ),
            discord.SelectOption(
                label="Em Análise",
                description="Problema está sendo analisado",
                emoji="🔍",
                value="em_analise"
            )
        ]
        
        super().__init__(
            placeholder="Selecione o status do ticket...",
            options=options,
            custom_id="pause_status_select"
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Callback executado quando uma opção é selecionada."""
        try:
            status = self.values[0]
            modal = PauseDescriptionModal(self.ticket, status)
            await interaction.response.send_modal(modal)
            
        except Exception as e:
            logger.error(f"Erro no callback do pause select: {e}")
            message = await interaction.followup.send(
                "❌ Ocorreu um erro. Tente novamente.",
                ephemeral=True
            )
            schedule_ephemeral_deletion(interaction, message)


class PauseDescriptionModal(discord.ui.Modal):
    """Modal para capturar a descrição do status fechado."""
    
    def __init__(self, ticket: dict, status: str):
        self.ticket = ticket
        self.status = status
        
        # Definir títulos e labels baseados no status
        status_info = {
            "resolvido": {
                "title": "✅ Ticket Resolvido",
                "label": "Descrição da Resolução",
                "placeholder": "Descreva como o problema foi resolvido..."
            },
            "chamado_aberto": {
                "title": "📞 Chamado Aberto",
                "label": "Informações do Chamado",
                "placeholder": "Número do chamado, sistema utilizado, previsão..."
            },
            "aguardando_resposta": {
                "title": "⏳ Aguardando Resposta",
                "label": "O que está aguardando",
                "placeholder": "Descreva o que foi solicitado ao usuário..."
            },
            "em_analise": {
                "title": "🔍 Em Análise",
                "label": "Status da Análise",
                "placeholder": "Descreva o que está sendo analisado..."
            }
        }
        
        info = status_info.get(status, status_info["resolvido"])
        super().__init__(title=info["title"])
        
        self.description = discord.ui.TextInput(
            label=info["label"],
            placeholder=info["placeholder"],
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True
        )
        self.add_item(self.description)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Callback executado quando o modal é enviado."""
        try:
            await interaction.response.defer()
            
            channel = interaction.channel
            user = interaction.user
            
            # Definir cores e emojis baseados no status
            status_config = {
                "resolvido": {"color": 0x00ff00, "emoji": "✅", "title": "🎯 PROBLEMA RESOLVIDO"},
                "chamado_aberto": {"color": 0x0099ff, "emoji": "📞", "title": "📞 CHAMADO ABERTO"},
                "aguardando_resposta": {"color": 0xffa500, "emoji": "⏳", "title": "⏳ AGUARDANDO RESPOSTA"},
                "em_analise": {"color": 0x9932cc, "emoji": "🔍", "title": "🔍 EM ANÁLISE"}
            }
            
            config = status_config.get(self.status, status_config["resolvido"])
            
            # Enviar embed com status PRIMEIRO
            embed = discord.Embed(
                title=f"{config['emoji']} {config['title']}",
                description=self.description.value,
                color=config['color'],
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="👤 Responsável",
                value=user.mention,
                inline=True
            )
            
            embed.add_field(
                name="📅 Concluído em",
                value=f"<t:{int(datetime.now().timestamp())}:f>",
                inline=True
            )
            
            # Adicionar campo específico para status resolvido
            if self.status == "resolvido":
                embed.add_field(
                    name="🎉 Status Final",
                    value="**PROBLEMA RESOLVIDO COM SUCESSO!**\n"
                         "Este ticket foi concluído e pode ser fechado.",
                    inline=False
                )
            
            # Enviar mensagem de status PRIMEIRO (antes de qualquer alteração)
            status_message = await channel.send(embed=embed)
            
            # Aguardar um momento para garantir que a mensagem foi enviada e processada
            import asyncio
            await asyncio.sleep(2)
            
            # Usar a função helper otimizada para fechar (pulando mensagem padrão)
            from utils.helpers import close_ticket_channel
            await close_ticket_channel(interaction.client, channel, auto_close=False, skip_close_message=True)
            
            logger.info(f"Ticket {self.ticket['id']} fechado por {user} com status: {self.status}")
            
            # Confirmar para o usuário que o status foi definido
            message = await interaction.followup.send(
                f"✅ Ticket fechado com status: **{config['title']}**",
                ephemeral=True
            )
            schedule_ephemeral_deletion(interaction, message)
            
        except Exception as e:
            logger.error(f"Erro ao fechar ticket: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            await interaction.followup.send(
                f"❌ Erro ao fechar ticket: {str(e)}"
            )


class CloseStatusView(discord.ui.View):
    """View temporária para seleção do status de fechamento."""
    
    def __init__(self, ticket):
        super().__init__(timeout=300)  # 5 minutos
        self.add_item(CloseStatusSelect(ticket))



