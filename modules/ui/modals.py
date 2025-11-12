"""
Modais para interação com o usuário no sistema de tickets.
"""

import logging
import asyncio
from datetime import datetime

import discord

from config import TICKET_REASONS, BOT_CONFIG
from .views import TicketControlView
from utils.helpers import resolve_emoji

logger = logging.getLogger(__name__)


class ReasonSelect(discord.ui.Select):
    """Select menu para escolha do motivo do ticket."""
    
    def __init__(self, bot=None, guild=None):
        self.bot = bot
        self.guild = guild
        
        options = []
        for reason in TICKET_REASONS:
            # Resolver emoji dinamicamente
            emoji = resolve_emoji(bot, reason['emoji'], guild) if bot and guild else reason['emoji']
            
            options.append(discord.SelectOption(
                label=reason['label'],
                description=reason['description'],
                emoji=emoji
            ))
        
        super().__init__(
            placeholder="Selecione o motivo do seu chamado...",
            options=options,
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
            await interaction.followup.send(
                "❌ Ocorreu um erro. Tente novamente.",
                ephemeral=True, delete_after=60
            )


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
            
            # Checar permissões do bot no servidor antes de operações que podem falhar com 403
            try:
                bot_member = guild.me
                bot_perms = bot_member.guild_permissions if bot_member else None
            except Exception:
                bot_perms = None

            missing_perms = []
            if not bot_perms or not bot_perms.manage_channels:
                missing_perms.append('Manage Channels')
            if not bot_perms or not bot_perms.send_messages:
                missing_perms.append('Send Messages')
            if not bot_perms or not bot_perms.embed_links:
                missing_perms.append('Embed Links')
            if not bot_perms or not bot_perms.attach_files:
                missing_perms.append('Attach Files')

            if missing_perms:
                # Informar o usuário e abortar a criação do ticket de forma amigável
                perms_list = ', '.join(missing_perms)
                logger.error(f"Bot sem permissões necessárias no servidor {guild.name}: {perms_list}")
                await interaction.followup.send(
                    f"❌ O bot não possui permissões necessárias neste servidor: {perms_list}. Peça a um administrador para conceder essas permissões ao cargo do bot e tente novamente.",
                    ephemeral=True, delete_after=60
                )
                return
            
            # Verificar se já existe um ticket/canal para este usuário
            latest_ticket = interaction.client.db.get_user_latest_ticket(user.id)
            existing_channel = None
            ticket_id = None
            is_reopened = False
            
            if latest_ticket:
                # Buscar o canal existente
                existing_channel = guild.get_channel(latest_ticket['channel_id'])
                
                if existing_channel:
                    # Reabrir o ticket existente
                    ticket_id = interaction.client.db.reopen_ticket(
                        existing_channel.id,
                        self.reason,
                        self.description.value
                    )
                    is_reopened = True
                    logger.info(f"Reabrindo ticket existente para {user} no canal {existing_channel.name}")
                    
                    # Restaurar permissões se necessário
                    await existing_channel.set_permissions(
                        user,
                        read_messages=True,
                        send_messages=True,
                        attach_files=True,
                        embed_links=True
                    )
                    
                    # Remover emoji de fechado se existir
                    new_name = existing_channel.name.replace("🔒", "").replace("⏸️", "")
                    if existing_channel.name != new_name:
                        await existing_channel.edit(name=new_name)
                        
                    channel = existing_channel
            
            if not existing_channel:
                # Criar novo canal se não existe um canal anterior
                # Buscar ou criar categoria "Tickets"
                category = discord.utils.get(guild.categories, name=BOT_CONFIG['tickets_category_name'])
                if not category:
                    category = await guild.create_category(
                        name=BOT_CONFIG['tickets_category_name'],
                        reason="Categoria criada automaticamente pelo bot de tickets"
                    )
                    logger.info(f"Categoria '{BOT_CONFIG['tickets_category_name']}' criada no servidor {guild.name}")
                
                # Configurar permissões do canal (apenas administradores e dono do ticket)
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    user: discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        attach_files=True,
                        embed_links=True
                    ),
                    guild.me: discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        manage_messages=True,
                        embed_links=True
                    )
                }
                
                # Adicionar permissões para todos os administradores do servidor
                for member in guild.members:
                    if member.guild_permissions.administrator and not member.bot:
                        overwrites[member] = discord.PermissionOverwrite(
                            read_messages=True,
                            send_messages=True,
                            manage_messages=True,
                            embed_links=True
                        )
                
                # Criar canal do ticket
                channel_name = f"💻┃{user.name.lower()}"
                channel = await category.create_text_channel(
                    name=channel_name,
                    overwrites=overwrites,
                    reason=f"Ticket criado por {user}"
                )
                
                # Salvar no banco de dados
                ticket_id = interaction.client.db.create_ticket(
                    user_id=user.id,
                    user_name=str(user),
                    channel_id=channel.id,
                    reason=self.reason,
                    description=self.description.value
                )
            
            if not ticket_id:
                if not is_reopened and channel:
                    await channel.delete(reason="Erro ao criar ticket no banco")
                await interaction.followup.send(
                    "❌ Erro ao criar ticket. Tente novamente.",
                    ephemeral=True, delete_after=60
                )
                return
            
            # Embed de informações do ticket
            if is_reopened:
                embed = discord.Embed(
                    title="🔄 Ticket Reaberto",
                    description="Seu ticket foi reaberto com uma nova solicitação!",
                    color=0xffa500,  # Laranja
                    timestamp=datetime.now()
                )
                embed.add_field(
                    name="📜 Histórico Preservado",
                    value="Este é seu canal de ticket pessoal. Todo o histórico anterior foi mantido.",
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="🎫 Novo Ticket de Suporte",
                    description="Seu ticket foi criado com sucesso!",
                    color=0x00ff00,  # Verde
                    timestamp=datetime.now()
                )
            
            embed.add_field(
                name="👤 Usuário",
                value=user.mention,
                inline=True
            )
            
            embed.add_field(
                name="🏷️ Motivo",
                value=self.reason,
                inline=True
            )
            
            embed.add_field(
                name="📅 Data",
                value=f"`{datetime.now().strftime('%d/%m/%Y %H:%M')}`",
                inline=True
            )
            
            embed.add_field(
                name="📝 Descrição:",
                value=self.description.value,
                inline=False
            )
            
            embed.add_field(
                name="📎 Anexos e Arquivos",
                value="💡 Adicione anexos abaixo para ajudar na resolução do problema, links, fotos...",
                inline=False
            )
            
            if is_reopened:
                embed.add_field(
                    name="⚠️ Importante",
                    value="Este ticket foi reaberto. Scroll para cima para ver conversas anteriores.",
                    inline=False
                )
                embed.set_footer(
                    text="Este é seu canal pessoal de ticket. Será fechado automaticamente em 12 horas se não houver atividade."
                )
            else:
                embed.set_footer(
                    text="Este ticket será fechado automaticamente em 12 horas se não houver atividade."
                )
            
            # View com botões de controle para administradores
            control_view = TicketControlView()
            
            # Enviar mensagem no canal do ticket
            await channel.send(
                content=f"🔔 **{user.mention}, seu ticket foi {'reaberto' if is_reopened else 'criado'}!**\n"
                       f"� <@&1382008028517109832> responderá em breve.",
                embed=embed,
                view=control_view
            )
            
            # Responder ao usuário
            if is_reopened:
                embed_response = discord.Embed(
                    title="🔄 Ticket Reaberto com Sucesso!",
                    description=f"Seu ticket foi reaberto no canal {channel.mention}",
                    color=0xffa500  # Laranja
                )
                embed_response.add_field(
                    name="📜 Histórico Mantido:",
                    value="Todas as conversas anteriores foram preservadas no canal.",
                    inline=False
                )
            else:
                embed_response = discord.Embed(
                    title="🎫 Ticket Criado com Sucesso!",
                    description=f"Seu ticket foi criado no canal {channel.mention}",
                    color=0x00ff00  # Verde
                )
            
            embed_response.add_field(
                name="📍 Próximo passo:",
                value=f"**[Clique aqui para acessar seu ticket](<https://discord.com/channels/{channel.guild.id}/{channel.id}>)**",
                inline=False
            )
            embed_response.add_field(
                name="💡 Dica:",
                value="Você também pode acessar através da lista de canais na lateral esquerda",
                inline=False
            )
            
            message = await interaction.followup.send(
                embed=embed_response,
                ephemeral=True
            )
            
            # Agendar exclusão da mensagem após 60 segundos
            import asyncio
            async def delete_after_delay():
                try:
                    await asyncio.sleep(60)
                    await message.delete()
                except Exception:
                    pass  # Ignorar erros se a mensagem já foi deletada
            
            asyncio.create_task(delete_after_delay())
            
            logger.info(f"Ticket {ticket_id} {'reaberto' if is_reopened else 'criado'} por {user} no canal {channel.name}")
            
        except Exception as e:
            logger.error(f"Erro ao criar ticket: {e}")
            # If sending the modal failed, try to reply safely. If no response was sent yet
            # we must use interaction.response.send_message, otherwise followup is allowed.
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ Ocorreu um erro. Tente novamente.", ephemeral=True)
                else:
                    await interaction.followup.send("❌ Ocorreu um erro. Tente novamente.", ephemeral=True)
            except Exception:
                # Last resort: log the failure. Avoid raising further to keep bot stable.
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
            await interaction.followup.send(
                "❌ Ocorreu um erro. Tente novamente.",
                ephemeral=True, delete_after=60
            )


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
            
            # Fechar o ticket no banco
            if interaction.client.db.close_ticket(channel.id):
                # Modificar permissões do canal
                ticket_owner_id = self.ticket['user_id']
                ticket_owner = interaction.guild.get_member(ticket_owner_id)
                
                if ticket_owner:
                    try:
                        await channel.set_permissions(
                            ticket_owner,
                            send_messages=False,
                            add_reactions=False,
                            view_channel=True  # Ainda pode ver mas não interagir
                        )
                    except discord.HTTPException as e:
                        if e.status == 429:  # Rate limited
                            logger.warning(f"Rate limited ao alterar permissões do canal {channel.name} - continuando com fechamento")
                        else:
                            logger.error(f"Erro ao alterar permissões do canal: {e}")
                    except Exception as e:
                        logger.error(f"Erro inesperado ao alterar permissões: {e}")
                
                # Renomear canal com emoji de fechado
                new_name = f"🔒{channel.name}"
                if not channel.name.startswith("🔒"):
                    try:
                        await channel.edit(name=new_name)
                    except discord.HTTPException as e:
                        if e.status == 429:  # Rate limited
                            logger.warning(f"Rate limited ao renomear canal {channel.name} - continuando com fechamento")
                        else:
                            logger.error(f"Erro ao renomear canal: {e}")
                    except Exception as e:
                        logger.error(f"Erro inesperado ao renomear canal: {e}")
                
                # Definir cores e emojis baseados no status
                status_config = {
                    "resolvido": {"color": 0x00ff00, "emoji": "✅", "title": "Ticket Resolvido"},
                    "chamado_aberto": {"color": 0x0099ff, "emoji": "📞", "title": "Chamado Aberto"},
                    "aguardando_resposta": {"color": 0xffa500, "emoji": "⏳", "title": "Aguardando Resposta"},
                    "em_analise": {"color": 0x9932cc, "emoji": "🔍", "title": "Em Análise"}
                }
                
                config = status_config.get(self.status, status_config["resolvido"])
                
                # Enviar embed com status
                embed = discord.Embed(
                    title=f"{config['emoji']} {config['title']}",
                    description=self.description.value,
                    color=config['color'],
                    timestamp=datetime.now()
                )
                
                embed.add_field(
                    name="👤 Administrador",
                    value=user.mention,
                    inline=True
                )
                
                embed.add_field(
                    name="📅 Data",
                    value=f"<t:{int(datetime.now().timestamp())}:f>",
                    inline=True
                )
                
                # Adicionar view com botão de reabrir
                from .views import ReopenTicketView
                reopen_view = ReopenTicketView()
                
                try:
                    await channel.send(embed=embed, view=reopen_view)
                    logger.info(f"Ticket {self.ticket['id']} fechado por {user} com status: {self.status}")
                except discord.HTTPException as e:
                    if e.status == 429:  # Rate limited
                        logger.warning(f"Rate limited ao enviar mensagem de fechamento - ticket foi fechado no banco")
                    else:
                        logger.error(f"Erro ao enviar mensagem de fechamento: {e}")
                except Exception as e:
                    logger.error(f"Erro inesperado ao enviar mensagem: {e}")
                    
                # Log independente do sucesso do envio da mensagem
                logger.info(f"Ticket {self.ticket['id']} fechado no banco por {user} com status: {self.status}")
            else:
                await interaction.followup.send(
                    "❌ Erro ao fechar ticket."
                )
            
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



