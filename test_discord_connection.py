#!/usr/bin/env python3
"""
🧪 Teste Rápido de Conectividade Discord
Testa se o bot consegue conectar sem executar toda a aplicação
"""

import asyncio
import discord
from dotenv import load_dotenv
import os

load_dotenv()

async def quick_discord_test():
    """Teste rápido de conectividade."""
    print("🧪 TESTE RÁPIDO DE CONECTIVIDADE DISCORD")
    print("-" * 45)
    
    token = os.getenv('DISCORD_TOKEN')
    
    if not token:
        print("❌ Token não encontrado!")
        return False
    
    print(f"🔑 Usando token: {token[:20]}...{token[-10:]}")
    print("⏳ Tentando conectar...")
    
    try:
        # Cliente mínimo apenas para teste
        client = discord.Client(intents=discord.Intents.default())
        
        @client.event
        async def on_ready():
            print(f"✅ CONEXÃO BEM-SUCEDIDA!")
            print(f"🤖 Bot: {client.user}")
            print(f"🌐 Conectado a {len(client.guilds)} servidor(es)")
            
            # Fechar após confirmar conexão
            await client.close()
        
        # Tentar conectar por máximo 10 segundos
        await asyncio.wait_for(client.start(token), timeout=10.0)
        
        return True
        
    except discord.LoginFailure:
        print("❌ FALHA DE LOGIN: Token inválido ou expirado")
        return False
    except asyncio.TimeoutError:
        print("⏱️ TIMEOUT: Conexão demorou mais de 10 segundos")
        return False
    except Exception as e:
        print(f"❌ ERRO INESPERADO: {e}")
        return False

async def main():
    """Executa o teste."""
    success = await quick_discord_test()
    
    if success:
        print("\n🎉 TOKEN VÁLIDO! O problema pode estar na configuração do bot.")
        print("💡 Tente executar: python bot_optimized.py")
    else:
        print("\n🚨 TOKEN INVÁLIDO!")
        print("🔧 SOLUÇÕES:")
        print("1. Gere um novo token no Discord Developer Portal")
        print("2. Verifique se o bot não foi resetado")
        print("3. Confirme que copiou o token completo")
        print("4. Recoloque o novo token no arquivo .env")

if __name__ == "__main__":
    asyncio.run(main())