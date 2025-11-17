"""
Comandos essenciais do sistema de tickets organizados em Cogs.
"""

import logging

import discord
from discord.ext import commands

from config import EMBED_COLORS, BOT_CONFIG
from modules.ui.views import TicketView
from utils.helpers import schedule_ephemeral_deletion

logger = logging.getLogger(__name__)


class TicketCommands(commands.Cog):
    """Cog com os comandos atualmente utilizados: /close e /setup_tickets."""

    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="setup_tickets", description="Configura o sistema de tickets em um canal")
    @discord.app_commands.describe(channel="Canal onde será postado o embed de tickets")
    async def setup_tickets(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Publica o painel de tickets no canal escolhido."""
        try:
            if not interaction.user.guild_permissions.manage_channels:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para usar este comando.",
                    ephemeral=True,
                )
                return

            await interaction.response.defer()
            await self._setup_tickets_in_channel(channel)

            await interaction.followup.send(
                f"✅ Sistema de tickets configurado no canal {channel.mention}",
                ephemeral=True,
            )
            logger.info(
                "Sistema de tickets configurado por %s no canal %s",
                interaction.user,
                channel.name,
            )

        except Exception as exc:
            logger.error("Erro no comando setup_tickets: %s", exc)
            await interaction.followup.send(
                "❌ Erro ao configurar sistema de tickets.",
                ephemeral=True,
            )

    @discord.app_commands.command(name="close", description="Fechar ticket com status específico (apenas administradores)")
    async def close_ticket_with_status(self, interaction: discord.Interaction):
        """Abre o seletor de status para encerrar o ticket atual."""
        try:
            channel = interaction.channel
            ticket = self.bot.db.get_ticket_by_channel(channel.id)

            if not ticket:
                await interaction.response.send_message(
                    "❌ Este comando só pode ser usado em canais de ticket.",
                    ephemeral=True,
                )
                return

            if ticket["status"] == "closed":
                await interaction.response.send_message(
                    "❌ Este ticket já está fechado.",
                    ephemeral=True,
                )
                return

            user = interaction.user
            has_support_role = (
                discord.utils.get(user.roles, name=BOT_CONFIG["support_role_name"]) is not None
            )
            has_manage_channels = user.guild_permissions.manage_channels

            if not (has_support_role or has_manage_channels):
                await interaction.response.send_message(
                    "❌ Apenas administradores podem usar este comando.",
                    ephemeral=True,
                )
                return

            from modules.ui.modals import CloseStatusView

            view = CloseStatusView(ticket)
            await interaction.response.send_message(
                "📋 **Fechar Ticket**\n\nSelecione o status do ticket:",
                view=view,
                ephemeral=True,
            )
            schedule_ephemeral_deletion(interaction)

        except Exception as exc:
            logger.error("Erro no comando close: %s", exc)
            await interaction.response.send_message(
                "❌ Erro ao fechar ticket.",
                ephemeral=True,
            )
            schedule_ephemeral_deletion(interaction)

    async def _setup_tickets_in_channel(self, channel: discord.TextChannel):
        """Configura o embed e a view persistente do painel de tickets."""
        embed = discord.Embed(
            title="🎫 **SISTEMA DE TICKETS DE SUPORTE**",
            description="**PRECISA DE AJUDA DA EQUIPE DE TI?**\n\n**Clique no botão abaixo para abrir um ticket!**",
            color=EMBED_COLORS["info"],
        )

        embed.add_field(
            name="📝 **PLATAFORMAS DISPONÍVEIS**",
            value=(
                "**<:arbo:1437860050201874442> ARBO**\n\n"
                "**<:Lais:1437865327001342052> LAIS**\n\n"
                "**<:SP:1437860450523025459> SENDPULSE**\n\n"
                "**❓ OUTROS**"
            ),
            inline=False,
        )

        embed.add_field(
            name="⏰ **HORÁRIO DE ATENDIMENTO**",
            value="**Segunda a Sexta**\n\n**08:20 às 12:30**\n\n**13:30 às 18:20**",
            inline=False,
        )

        embed.set_footer(
            text=f"Tickets são fechados automaticamente após {BOT_CONFIG['auto_close_hours']} horas sem atividade.",
        )

        view = TicketView()
        await channel.send(embed=embed, view=view)


async def setup(bot):
    """Adiciona o cog ao bot."""
    await bot.add_cog(TicketCommands(bot))
