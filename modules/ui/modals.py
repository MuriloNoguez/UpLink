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
                ephemeral=True
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
                    ephemeral=True
                )
                return
            
            # Verificar se já existe um ticket/canal para este usuário
            latest_ticket = interaction.client.db.get_user_latest_ticket(user.id)
            existing_channel = None
            ticket_id = None
            is_reopened = False
            # Controla se devemos pular o embed padrão (quando já enviamos a mensagem de reabertura)
            skip_normal_embed = False
            
            if latest_ticket:
                # Buscar o canal existente
                existing_channel = guild.get_channel(latest_ticket['channel_id'])
                
                if existing_channel:
                    # Reabrir o ticket existente no banco primeiro
                    ticket_id = interaction.client.db.reopen_ticket(
                        existing_channel.id,
                        self.reason,
                        self.description.value
                    )
                    is_reopened = True
                    channel = existing_channel
                    logger.info(f"Reabrindo ticket existente para {user} no canal {existing_channel.name}")
                    
                    # Preparar e ENVIAR MENSAGEM PRIMEIRO (antes de qualquer alteração)
                    embed_reopen = discord.Embed(
                        title="🔄 Ticket Reaberto",
                        description="Seu ticket foi reaberto com uma nova solicitação!",
                        color=0xffa500,  # Laranja
                        timestamp=datetime.now()
                    )
                    embed_reopen.add_field(
                        name="👤 Usuário", value=user.mention, inline=True
                    )
                    embed_reopen.add_field(
                        name="🏷️ Motivo", value=self.reason, inline=True
                    )
                    embed_reopen.add_field(
                        name="📅 Data", value=f"`{datetime.now().strftime('%d/%m/%Y %H:%M')}`", inline=True
                    )
                    embed_reopen.add_field(
                        name="📝 Nova Descrição:", value=self.description.value, inline=False
                    )
                    embed_reopen.add_field(
                        name="📜 Histórico Preservado",
                        value="Todo o histórico anterior foi mantido. Scroll para cima para ver conversas anteriores.",
                        inline=False
                    )
                    
                    # Usar view de controle (import no topo do módulo evita sombreamento de nome)
                    control_view = TicketControlView()
                    
                    # ENVIAR MENSAGEM IMEDIATAMENTE
                    await channel.send(
                        content=f"🔔 **{user.mention}, seu ticket foi reaberto!**\n"
                               f"📞 <@&1382008028517109832> responderá em breve.",
                        embed=embed_reopen,
                        view=control_view
                    )
                    
                    # Agora fazer alterações (em background, sem bloquear)
                    import asyncio
                    async def update_channel_async():
                        try:
                            # Restaurar permissões
                            await channel.set_permissions(
                                user, send_messages=True, add_reactions=True, view_channel=True
                            )
                        except Exception as e:
                            logger.warning(f"Erro ao atualizar canal após reabertura: {e}")
                    
                    # Executar em background
                    asyncio.create_task(update_channel_async())
                    
                    # Pular a criação normal do embed (já foi enviado)
                    skip_normal_embed = True
            
            # Nota: `skip_normal_embed` já foi inicializada acima
            
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
                    ephemeral=True
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
            
            # Enviar mensagem apenas para tickets NOVOS (reabertura já foi enviada acima)
            if not skip_normal_embed:
                # View com botões de controle para administradores
                control_view = TicketControlView()
                
                # Enviar mensagem no canal do ticket
                await channel.send(
                    content=f"🔔 **{user.mention}, seu ticket foi {'reaberto' if is_reopened else 'criado'}!**\n"
                           f"📞 <@&1382008028517109832> responderá em breve.",
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
            
            # Agendar exclusão da mensagem após 45 segundos
            import asyncio
            async def delete_after_delay():
                try:
                    await asyncio.sleep(45)
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
                ephemeral=True
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
            await interaction.followup.send(
                f"✅ Ticket fechado com status: **{config['title']}**",
                ephemeral=True
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



