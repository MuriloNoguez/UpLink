"""
Views (botões, menus) para o sistema de tickets.
"""

import logging
import asyncio
from datetime import datetime

import discord

from config import EMBED_COLORS, BOT_CONFIG

logger = logging.getLogger(__name__)


class TicketView(discord.ui.View):
    """View persistente com o botão para abrir tickets."""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(
        label="Abrir Ticket",
        style=discord.ButtonStyle.primary,
        emoji="🎫",
        custom_id="open_ticket_button"
    )
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Callback para o botão de abrir ticket."""
        try:
            from .modals import ReasonSelectView
            
            # Verificar se o usuário já tem um ticket aberto ou pausado
            user_tickets = interaction.client.db.get_user_tickets(interaction.user.id, 5)
            open_tickets = [t for t in user_tickets if t['status'] == 'open']
            paused_tickets = [t for t in user_tickets if t['status'] == 'paused']
            
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
                    return
            
            # Remover verificação de tickets pausados - permitir reabertura direta
            
            # Se chegou até aqui, pode abrir um ticket novo ou reabrir o existente
            # Enviar select menu
            view = ReasonSelectView(interaction.client, interaction.guild)
            await interaction.response.send_message(
                "🎫 **Selecione o motivo do seu chamado:**",
                view=view,
                ephemeral=True,
                delete_after=300
            )
            
        except Exception as e:
            logger.error(f"Erro ao abrir ticket: {e}")
            await interaction.response.send_message(
                "❌ Erro interno. Tente novamente.",
                ephemeral=True
            )


class TicketControlView(discord.ui.View):
    """View com botões para controle administrativo dos tickets."""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Verificar se o usuário tem permissão para usar os botões."""
        # Para o botão de fechar, apenas admins
        user = interaction.user
        has_support_role = discord.utils.get(user.roles, name=BOT_CONFIG['support_role_name']) is not None
        has_manage_channels = user.guild_permissions.manage_channels
        
        if not (has_support_role or has_manage_channels):
            await interaction.response.send_message(
                "❌ Apenas administradores podem usar este botão.",
                ephemeral=True
            )
            return False
        
        return True
    



class ReopenTicketView(discord.ui.View):
    """View com botão para reabrir ticket."""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(
        label="Reabrir Ticket",
        style=discord.ButtonStyle.success,
        emoji="🔄",
        custom_id="reopen_ticket_button"
    )
    async def reopen_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Callback para reabrir ticket."""
        try:
            # Verificar se é canal de ticket
            ticket = interaction.client.db.get_ticket_by_channel(interaction.channel.id)
            if not ticket:
                await interaction.response.send_message(
                    "❌ Este não é um canal de ticket válido.",
                    ephemeral=True
                )
                return
                
            if ticket['status'] != 'closed':
                await interaction.response.send_message(
                    f"❌ Este ticket não está fechado. Status atual: {ticket['status']}",
                    ephemeral=True
                )
                return
            
            # Verificar se é o dono do ticket
            user = interaction.user
            if user.id != ticket['user_id']:
                await interaction.response.send_message(
                    "❌ Apenas o dono do ticket pode reabri-lo.",
                    ephemeral=True
                )
                return
            
            # Abrir seleção de motivo
            from .modals import ReasonSelectView
            
            view = ReasonSelectView(interaction.client, interaction.guild)
            await interaction.response.send_message(
                "🎫 **Selecione o motivo da reabertura:**",
                view=view,
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Erro ao reabrir ticket via botão: {e}")
            await interaction.response.send_message(
                "❌ Erro interno ao reabrir ticket.",
                ephemeral=True
            )

