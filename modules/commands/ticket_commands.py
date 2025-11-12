"""
Comandos do sistema de tickets organizados em Cogs.
"""

import logging
from datetime import datetime

import discord
from discord.ext import commands

from config import EMBED_COLORS, BOT_CONFIG, STATUS_EMOJI
from modules.ui.views import TicketView

logger = logging.getLogger(__name__)


class TicketCommands(commands.Cog):
    """Cog com todos os comandos relacionados a tickets."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @discord.app_commands.command(name="ticket", description="🎫 Abrir um novo ticket de suporte")
    async def ticket(self, interaction: discord.Interaction):
        """
        Comando simples para abrir um ticket.
        """
        try:
            await interaction.response.send_message(
                "🎫 **Sistema de Tickets**\n"
                "Para abrir um ticket, use o sistema configurado no canal de suporte.\n"
                "Ou aguarde, estamos preparando a interface...",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Erro no comando ticket: {e}")
    
    @discord.app_commands.command(name="keepalive_status", description="📊 Verifica o status do sistema keep-alive")
    async def keepalive_status(self, interaction: discord.Interaction):
        """
        Comando para verificar estatísticas do keep-alive.
        Apenas administradores podem usar.
        """
        try:
            # Verificar se o usuário tem permissão
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    "❌ Apenas administradores podem verificar o status do keep-alive.",
                    ephemeral=True
                )
                return
            
            # Verificar se o sistema keep-alive existe
            if not hasattr(self.bot, 'keep_alive_system'):
                await interaction.response.send_message(
                    "⚠️ Sistema keep-alive não está inicializado.",
                    ephemeral=True
                )
                return
            
            # Obter estatísticas
            stats = self.bot.keep_alive_system.get_stats()
            
            # Criar embed com estatísticas
            embed = discord.Embed(
                title="📊 Status do Keep-Alive",
                color=EMBED_COLORS['info'],
                timestamp=datetime.now()
            )
            
            # Status principal
            status_icon = "🟢" if stats['is_running'] else "🔴"
            embed.add_field(
                name="Status",
                value=f"{status_icon} {'Ativo' if stats['is_running'] else 'Inativo'}",
                inline=True
            )
            
            # Estatísticas
            embed.add_field(
                name="Pings Bem-sucedidos",
                value=f"✅ {stats['successful_pings']}",
                inline=True
            )
            
            embed.add_field(
                name="Pings Falharam",
                value=f"❌ {stats['failed_pings']}",
                inline=True
            )
            
            embed.add_field(
                name="Taxa de Sucesso",
                value=f"📈 {stats['success_rate']}%",
                inline=True
            )
            
            embed.add_field(
                name="Total de Pings",
                value=f"📊 {stats['total_pings']}",
                inline=True
            )
            
            # Servidores conectados
            embed.add_field(
                name="Servidores Conectados",
                value=f"🌐 {len(self.bot.guilds)}",
                inline=True
            )
            
            embed.set_footer(text="Sistema mantém o bot ativo a cada 30 minutos")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Erro no comando keepalive_status: {e}")
            await interaction.response.send_message(
                "❌ Erro ao obter status do keep-alive.",
                ephemeral=True
            )
    
    @discord.app_commands.command(name="setup_tickets", description="Configura o sistema de tickets em um canal")
    @discord.app_commands.describe(channel="Canal onde será postado o embed de tickets")
    async def setup_tickets(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """
        Comando para configurar o sistema de tickets.
        
        Args:
            interaction: Interação do Discord
            channel: Canal onde será postado o embed
        """
        try:
            # Verificar se o usuário tem permissão
            if not interaction.user.guild_permissions.manage_channels:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para usar este comando.",
                    ephemeral=True
                )
                return
            
            await interaction.response.defer()
            
            # Configurar sistema de tickets no canal
            await self._setup_tickets_in_channel(channel)
            
            await interaction.followup.send(
                f"✅ Sistema de tickets configurado no canal {channel.mention}",
                ephemeral=True
            )
            
            logger.info(f"Sistema de tickets configurado por {interaction.user} no canal {channel.name}")
            
        except Exception as e:
            logger.error(f"Erro no comando setup_tickets: {e}")
            await interaction.followup.send(
                "❌ Erro ao configurar sistema de tickets.",
                ephemeral=True
            )
    
    @discord.app_commands.command(name="ticket_close", description="Fecha o ticket atual manualmente")
    async def ticket_close(self, interaction: discord.Interaction):
        """
        Comando para fechar um ticket manualmente.
        
        Args:
            interaction: Interação do Discord
        """
        try:
            # Verificar se o comando foi usado em um canal de ticket
            channel = interaction.channel
            ticket = self.bot.db.get_ticket_by_channel(channel.id)
            
            if not ticket:
                await interaction.response.send_message(
                    "❌ Este comando só pode ser usado em canais de ticket.",
                    ephemeral=True
                )
                return
            
            if ticket['status'] == 'closed':
                await interaction.response.send_message(
                    "❌ Este ticket já está fechado.",
                    ephemeral=True
                )
                return
            
            # Verificar permissões
            user = interaction.user
            is_ticket_owner = user.id == ticket['user_id']
            has_support_role = discord.utils.get(user.roles, name=BOT_CONFIG['support_role_name']) is not None
            has_manage_channels = user.guild_permissions.manage_channels
            
            if not (is_ticket_owner or has_support_role or has_manage_channels):
                await interaction.response.send_message(
                    "❌ Você não tem permissão para fechar este ticket.",
                    ephemeral=True
                )
                return
            
            await interaction.response.defer()
            
            # Fechar o ticket
            await self.bot.close_ticket_channel(channel)
            
            await interaction.followup.send(
                "✅ Ticket fechado com sucesso."
            )
            
            logger.info(f"Ticket {ticket['id']} fechado manualmente por {user}")
            
        except Exception as e:
            logger.error(f"Erro no comando ticket_close: {e}")
            await interaction.followup.send(
                "❌ Erro ao fechar ticket."
            )
    
    @discord.app_commands.command(name="pause", description="Pausar ticket com status específico (apenas administradores)")
    async def pause_ticket(self, interaction: discord.Interaction):
        """
        Comando para pausar um ticket com select de status.
        
        Args:
            interaction: Interação do Discord
        """
        try:
            # Verificar se o comando foi usado em um canal de ticket
            channel = interaction.channel
            ticket = self.bot.db.get_ticket_by_channel(channel.id)
            
            if not ticket:
                await interaction.response.send_message(
                    "❌ Este comando só pode ser usado em canais de ticket.",
                    ephemeral=True
                )
                return
            
            if ticket['status'] == 'closed':
                await interaction.response.send_message(
                    "❌ Este ticket já está fechado.",
                    ephemeral=True
                )
                return
                
            if ticket['status'] == 'paused':
                await interaction.response.send_message(
                    "❌ Este ticket já está pausado.",
                    ephemeral=True
                )
                return
            
            # Verificar permissões (apenas admins)
            user = interaction.user
            has_support_role = discord.utils.get(user.roles, name=BOT_CONFIG['support_role_name']) is not None
            has_manage_channels = user.guild_permissions.manage_channels
            
            if not (has_support_role or has_manage_channels):
                await interaction.response.send_message(
                    "❌ Apenas administradores podem usar este comando.",
                    ephemeral=True
                )
                return
            
            # Criar view com select de status
            from modules.ui.modals import PauseStatusView
            view = PauseStatusView(ticket)
            
            await interaction.response.send_message(
                "📋 **Pausar Ticket**\n\nSelecione o status do ticket:",
                view=view,
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Erro no comando pause: {e}")
            await interaction.response.send_message(
                "❌ Erro ao pausar ticket.",
                ephemeral=True
            )
    
    @discord.app_commands.command(name="ticket_unpause", description="Despausa o ticket atual (apenas administradores)")
    async def ticket_unpause(self, interaction: discord.Interaction):
        """
        Comando para despausar um ticket (apenas administradores).
        
        Args:
            interaction: Interação do Discord
        """
        try:
            # Verificar se o comando foi usado em um canal de ticket
            channel = interaction.channel
            ticket = self.bot.db.get_ticket_by_channel(channel.id)
            
            if not ticket:
                await interaction.response.send_message(
                    "❌ Este comando só pode ser usado em canais de ticket.",
                    ephemeral=True
                )
                return
            
            if ticket['status'] != 'paused':
                await interaction.response.send_message(
                    "❌ Este ticket não está pausado.",
                    ephemeral=True
                )
                return
            
            # Verificar permissões (apenas admins)
            user = interaction.user
            has_support_role = discord.utils.get(user.roles, name=BOT_CONFIG['support_role_name']) is not None
            has_manage_channels = user.guild_permissions.manage_channels
            
            if not (has_support_role or has_manage_channels):
                await interaction.response.send_message(
                    "❌ Apenas administradores podem despausar tickets.",
                    ephemeral=True
                )
                return
            
            await interaction.response.defer()
            
            # Despausar o ticket no banco
            if self.bot.db.unpause_ticket(channel.id):
                # Restaurar permissões do canal
                ticket_owner_id = ticket['user_id']
                ticket_owner = interaction.guild.get_member(ticket_owner_id)
                
                if ticket_owner:
                    await channel.set_permissions(
                        ticket_owner,
                        send_messages=True,
                        add_reactions=True,
                        view_channel=True
                    )
                
                # Renomear canal removendo emoji de pausa
                new_name = channel.name.replace("⏸️", "")
                if channel.name.startswith("⏸️"):
                    await channel.edit(name=new_name)
                
                # Enviar mensagem de despause
                embed = discord.Embed(
                    title="▶️ Ticket Despausado",
                    description="Este ticket foi despausado e está ativo novamente.",
                    color=EMBED_COLORS['success'],
                    timestamp=datetime.now()
                )
                
                embed.add_field(
                    name="👤 Despausado por",
                    value=user.mention,
                    inline=True
                )
                
                await channel.send(embed=embed)
                
                await interaction.followup.send(
                    "✅ Ticket despausado com sucesso."
                )
                
                logger.info(f"Ticket {ticket['id']} despausado por {user}")
            else:
                await interaction.followup.send(
                    "❌ Erro ao despausar ticket."
                )
            
        except Exception as e:
            logger.error(f"Erro no comando ticket_unpause: {e}")
            await interaction.followup.send(
                "❌ Erro ao despausar ticket."
            )
    
    @discord.app_commands.command(name="ticket_history", description="Ver histórico de tickets do usuário")
    @discord.app_commands.describe(user="Usuário para ver o histórico (apenas administradores)")
    async def ticket_history(self, interaction: discord.Interaction, user: discord.Member = None):
        """
        Comando para ver histórico de tickets.
        
        Args:
            interaction: Interação do Discord
            user: Usuário para ver histórico (opcional, apenas admins)
        """
        try:
            # Verificar se está especificando outro usuário
            target_user = user or interaction.user
            
            # Se está especificando outro usuário, verificar permissões
            if user and user != interaction.user:
                has_support_role = discord.utils.get(interaction.user.roles, name=BOT_CONFIG['support_role_name']) is not None
                has_manage_channels = interaction.user.guild_permissions.manage_channels
                
                if not (has_support_role or has_manage_channels):
                    await interaction.response.send_message(
                        "❌ Apenas administradores podem ver o histórico de outros usuários.",
                        ephemeral=True
                    )
                    return
            
            await interaction.response.defer(ephemeral=True)
            
            # Buscar tickets do usuário
            tickets = self.bot.db.get_user_tickets(target_user.id, 10)
            
            if not tickets:
                await interaction.followup.send(
                    f"📋 **{target_user.display_name}** não possui tickets registrados.",
                    ephemeral=True
                )
                return
            
            # Criar embed com histórico
            embed = discord.Embed(
                title=f"📋 Histórico de Tickets - {target_user.display_name}",
                color=EMBED_COLORS['info'],
                timestamp=datetime.now()
            )
            
            for i, ticket in enumerate(tickets[:5]):  # Mostrar apenas os 5 mais recentes
                channel = interaction.guild.get_channel(ticket['channel_id'])
                channel_info = channel.mention if channel else f"Canal removido ({ticket['channel_id']})"
                
                created_at = ticket['created_at']
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at)
                
                field_value = (
                    f"**Status:** {STATUS_EMOJI.get(ticket['status'], '❓')} {ticket['status'].title()}\n"
                    f"**Motivo:** {ticket['reason']}\n"
                    f"**Canal:** {channel_info}\n"
                    f"**Criado:** <t:{int(created_at.timestamp())}:R>\n"
                )
                
                if ticket['status'] == 'closed' and ticket['closed_at']:
                    closed_at = ticket['closed_at']
                    if isinstance(closed_at, str):
                        closed_at = datetime.fromisoformat(closed_at)
                    field_value += f"**Fechado:** <t:{int(closed_at.timestamp())}:R>\n"
                
                embed.add_field(
                    name=f"🎫 Ticket #{ticket['id']}",
                    value=field_value,
                    inline=False
                )
            
            if len(tickets) > 5:
                embed.set_footer(text=f"Mostrando 5 de {len(tickets)} tickets")
            else:
                embed.set_footer(text=f"Total: {len(tickets)} tickets")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Erro no comando ticket_history: {e}")
            await interaction.followup.send(
                "❌ Erro ao buscar histórico de tickets.",
                ephemeral=True
            )
    
    @discord.app_commands.command(name="ticket_force_close", description="Força o fechamento de um ticket (apenas administradores)")
    @discord.app_commands.describe(channel="Canal do ticket para forçar o fechamento")
    async def ticket_force_close(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        """
        Comando para forçar o fechamento de um ticket problemático.
        
        Args:
            interaction: Interação do Discord
            channel: Canal do ticket (opcional, usa o canal atual se não especificado)
        """
        try:
            # Verificar permissões (apenas admins)
            user = interaction.user
            has_support_role = discord.utils.get(user.roles, name=BOT_CONFIG['support_role_name']) is not None
            has_manage_channels = user.guild_permissions.manage_channels
            
            if not (has_support_role or has_manage_channels):
                await interaction.response.send_message(
                    "❌ Apenas administradores podem usar este comando.",
                    ephemeral=True
                )
                return
            
            # Usar canal atual se não especificado
            target_channel = channel or interaction.channel
            
            # Verificar se é um canal de ticket
            ticket = self.bot.db.get_ticket_by_channel(target_channel.id)
            if not ticket:
                await interaction.response.send_message(
                    f"❌ {target_channel.mention} não é um canal de ticket válido.",
                    ephemeral=True
                )
                return
            
            await interaction.response.defer()
            
            # Forçar fechamento no banco primeiro
            success = self.bot.db.close_ticket(target_channel.id)
            
            if success:
                # Tentar fechar o canal (com tratamento de rate limit)
                try:
                    # Modificar permissões básicas
                    await target_channel.set_permissions(
                        interaction.guild.default_role,
                        send_messages=False,
                        add_reactions=False
                    )
                    
                    # Delay para evitar rate limit
                    import asyncio
                    await asyncio.sleep(1)
                    
                    # Tentar renomear (mas não falhar se der rate limit)
                    if not target_channel.name.startswith("🔒"):
                        try:
                            await target_channel.edit(name=f"🔒{target_channel.name}")
                        except discord.HTTPException as e:
                            if e.status == 429:
                                logger.warning(f"Rate limited ao renomear, canal já marcado como fechado no banco")
                            else:
                                raise
                    
                    # Enviar mensagem de fechamento
                    embed = discord.Embed(
                        title="🔒 Ticket Fechado (Forçado)",
                        description="Este ticket foi fechado forçadamente por um administrador.",
                        color=EMBED_COLORS['closed'],
                        timestamp=datetime.now()
                    )
                    
                    embed.add_field(
                        name="👤 Fechado por",
                        value=user.mention,
                        inline=True
                    )
                    
                    embed.add_field(
                        name="⚡ Motivo",
                        value="Fechamento forçado (ticket problemático)",
                        inline=True
                    )
                    
                    await target_channel.send(embed=embed)
                    
                    await interaction.followup.send(
                        f"✅ Ticket no canal {target_channel.mention} foi fechado forçadamente.",
                        ephemeral=True
                    )
                    
                    logger.info(f"Ticket {ticket['id']} fechado forçadamente por {user}")
                    
                except Exception as e:
                    logger.error(f"Erro ao modificar canal, mas ticket foi marcado como fechado no banco: {e}")
                    await interaction.followup.send(
                        f"⚠️ Ticket marcado como fechado no banco, mas houve problema ao modificar o canal: {str(e)}",
                        ephemeral=True
                    )
            else:
                await interaction.followup.send(
                    "❌ Erro ao fechar ticket no banco de dados.",
                    ephemeral=True
                )
            
        except Exception as e:
            logger.error(f"Erro no comando ticket_force_close: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Erro interno ao forçar fechamento.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ Erro interno ao forçar fechamento.",
                    ephemeral=True
                )
    
    async def _setup_tickets_in_channel(self, channel: discord.TextChannel):
        """Configura o sistema de tickets em um canal específico."""
        # Criar embed do sistema de tickets
        embed = discord.Embed(
            title="🎫 **SISTEMA DE TICKETS DE SUPORTE**",
            description="**PRECISA DE AJUDA DA EQUIPE DE TI?**\n\n**Clique no botão abaixo para abrir um ticket!**",
            color=EMBED_COLORS['info']
        )
        
        embed.add_field(
            name="📝 **PLATAFORMAS DISPONÍVEIS**",
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
            value="**Segunda a Sexta**\n\n"
                  "**08:20 às 12:30**\n\n"
                  "**13:30 às 18:20**",
            inline=False
        )
        
        embed.set_footer(
            text=f"Tickets são fechados automaticamente após {BOT_CONFIG['auto_close_hours']} horas sem atividade."
        )
        
        # Enviar mensagem com view persistente
        view = TicketView()
        await channel.send(embed=embed, view=view)


async def setup(bot):
    """Função para adicionar o cog ao bot."""
    await bot.add_cog(TicketCommands(bot))