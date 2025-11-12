#!/usr/bin/env python3
"""
🚀 Script de Inicialização Inteligente para Produção
Sincroniza comandos apenas quando necessário.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from config import validate_config, DISCORD_TOKEN

# Configuração de logging mínima
logging.basicConfig(level=logging.ERROR)

class QuickSyncBot(commands.Bot):
    """Bot mínimo para sincronização rápida."""
    
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=discord.Intents.default(),
            help_command=None
        )
        self.sync_completed = False
        
    async def setup_hook(self):
        """Carrega comandos sem configurações pesadas."""
        try:
            from modules.commands.ticket_commands import TicketCommands
            await self.add_cog(TicketCommands(self))
        except Exception as e:
            print(f"❌ Erro ao carregar comandos: {e}")
            
    async def on_ready(self):
        """Sincroniza e fecha rapidamente."""
        try:
            print(f"⚡ Conectado como {self.user}")
            
            # Verificar se comandos já existem
            existing_commands = await self.tree.fetch_commands()
            
            if len(existing_commands) >= 7:  # Esperamos 8 comandos, mas 7+ é aceitável
                print(f"✅ {len(existing_commands)} comandos já sincronizados - pulando...")
                self.sync_completed = True
                await self.close()
                return
            
            # Sincronizar apenas se necessário
            print("🔄 Sincronizando comandos...")
            synced = await self.tree.sync()
            print(f"✅ {len(synced)} comandos sincronizados!")
            
            self.sync_completed = True
            await asyncio.sleep(1)  # Pequena pausa para garantir sincronização
            await self.close()
            
        except Exception as e:
            print(f"❌ Erro na sincronização: {e}")
            await self.close()


async def smart_sync():
    """Sincronização inteligente que verifica se é necessária."""
    try:
        bot = QuickSyncBot()
        await bot.start(DISCORD_TOKEN)
        return bot.sync_completed
    except Exception as e:
        print(f"❌ Erro no sync: {e}")
        return False


def main():
    """Função principal que decide se sincroniza ou não."""
    try:
        print("🔍 Verificando necessidade de sincronização...")
        
        # Tentar sincronização inteligente
        success = asyncio.run(smart_sync())
        
        if success:
            print("🎯 Sincronização concluída com sucesso!")
        else:
            print("⚠️ Sincronização pode ter falhado, mas continuando...")
            
        # Iniciar bot principal
        print("🚀 Iniciando bot principal...")
        from bot_optimized import main as run_optimized_bot
        run_optimized_bot()
        
    except KeyboardInterrupt:
        print("\n👋 Processo interrompido")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Erro no inicializador: {e}")
        # Mesmo com erro de sync, tenta iniciar o bot
        try:
            from bot_optimized import main as run_optimized_bot
            run_optimized_bot()
        except:
            sys.exit(1)


if __name__ == "__main__":
    main()