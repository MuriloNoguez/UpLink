"""
Script para sincronizar comandos slash com o Discord.
Execute este arquivo primeiro para garantir que os comandos apareçam no Discord.
"""

import asyncio
import logging
import discord
from discord.ext import commands

from config import validate_config, DISCORD_TOKEN, BOT_CONFIG
from modules.commands.ticket_commands import TicketCommands

# Configuração de logging simples
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Intents necessários
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True


class SyncBot(commands.Bot):
    """Bot temporário apenas para sincronizar comandos."""
    
    def __init__(self):
        super().__init__(
            command_prefix=BOT_CONFIG['command_prefix'],
            intents=intents,
            help_command=None
        )
        self.sync_complete = False
    
    async def setup_hook(self):
        """Carrega os comandos e sincroniza."""
        logger.info("🔄 Iniciando sincronização de comandos...")
        
        # Carregar os comandos
        try:
            await self.add_cog(TicketCommands(self))
            logger.info("✅ Comandos carregados")
        except Exception as e:
            logger.error(f"❌ Erro ao carregar comandos: {e}")
            return
        
        # Sincronizar comandos
        try:
            print("\n" + "="*60)
            print("🔄 SINCRONIZANDO COMANDOS SLASH...")
            print("="*60)
            
            synced = await self.tree.sync()
            
            print(f"✅ SINCRONIZADOS {len(synced)} COMANDOS COM SUCESSO!")
            print("-" * 60)
            
            for i, cmd in enumerate(synced, 1):
                print(f"{i:2}. /{cmd.name} - {cmd.description}")
            
            print("-" * 60)
            print("🎉 COMANDOS DISPONÍVEIS NO DISCORD!")
            print("💡 Digite / no Discord para ver os comandos")
            print("="*60 + "\n")
            
            self.sync_complete = True
            
        except Exception as e:
            logger.error(f"❌ Erro ao sincronizar comandos: {e}")
            print(f"\n❌ ERRO NA SINCRONIZAÇÃO: {e}\n")
    
    async def on_ready(self):
        """Quando conectar, mostrar status e fechar."""
        logger.info(f"🟢 Bot conectado como {self.user}")
        logger.info(f"🌐 Conectado a {len(self.guilds)} servidor(es)")
        
        if self.sync_complete:
            print("\n🎯 SINCRONIZAÇÃO CONCLUÍDA!")
            print("📋 Agora você pode executar o bot principal com: python main.py")
            print("⏱️  Aguarde 30 segundos e feche este processo...")
            
            # Aguardar um pouco para garantir que a sincronização foi processada
            await asyncio.sleep(30)
            
            print("🔚 Fechando sincronizador...")
            await self.close()
        else:
            print("❌ Sincronização falhou - verifique os logs acima")
            await self.close()


async def main():
    """Função principal para sincronizar comandos."""
    try:
        # Validar configuração
        validate_config()
        
        # Criar bot temporário
        bot = SyncBot()
        
        print("🚀 INICIANDO SINCRONIZADOR DE COMANDOS")
        print("📝 Este processo irá sincronizar os comandos slash com o Discord")
        print("⏱️  Processo será finalizado automaticamente após 30 segundos\n")
        
        # Executar bot
        try:
            await bot.start(DISCORD_TOKEN)
        finally:
            # Garantir que o bot seja fechado adequadamente
            if not bot.is_closed():
                await bot.close()
        
    except KeyboardInterrupt:
        print("\n⏹️  Processo interrompido pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        print(f"\n❌ ERRO: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Sincronizador finalizado")