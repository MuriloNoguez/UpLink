"""
Script para testar emojis do bot e verificar se estão acessíveis.
"""

import discord
from discord.ext import commands
from config import DISCORD_TOKEN

# Configurar bot simples para teste
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Lista de emojis para testar
EMOJIS_TO_TEST = [
    {"name": "arbo", "id": "1437860050201874442"},
    {"name": "Lais", "id": "1437865327001342052"}, 
    {"name": "SP", "id": "1437860450523025459"}
]

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    print(f'Conectado a {len(bot.guilds)} servidor(es)')
    
    print("\n=== TESTE DE EMOJIS ===")
    
    # Testar cada emoji
    for emoji_data in EMOJIS_TO_TEST:
        emoji_id = emoji_data["id"]
        emoji_name = emoji_data["name"]
        
        # Tentar buscar o emoji
        emoji = bot.get_emoji(int(emoji_id))
        
        if emoji:
            print(f"✅ {emoji_name}: {emoji} (encontrado no servidor: {emoji.guild.name})")
        else:
            print(f"❌ {emoji_name}: ID {emoji_id} não encontrado")
    
    print("\n=== EMOJIS DISPONÍVEIS ===")
    
    # Listar todos os emojis disponíveis do bot
    all_emojis = bot.emojis
    if all_emojis:
        print(f"Bot tem acesso a {len(all_emojis)} emojis:")
        for emoji in all_emojis[:10]:  # Mostrar apenas os primeiros 10
            print(f"  - {emoji.name}: {emoji} (ID: {emoji.id}) [Servidor: {emoji.guild.name}]")
        if len(all_emojis) > 10:
            print(f"  ... e mais {len(all_emojis) - 10} emojis")
    else:
        print("❌ Bot não tem acesso a nenhum emoji personalizado")
    
    print("\n=== TESTE DE FORMATO ===")
    
    # Testar diferentes formatos
    for emoji_data in EMOJIS_TO_TEST:
        emoji_id = emoji_data["id"]
        emoji_name = emoji_data["name"]
        
        formats = [
            f"<:{emoji_name}:{emoji_id}>",
            f"<a:{emoji_name}:{emoji_id}>",  # animado
            f":{emoji_name}:",  # só nome
        ]
        
        print(f"\nFormatos para {emoji_name}:")
        for fmt in formats:
            print(f"  {fmt}")
    
    await bot.close()

if __name__ == "__main__":
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        print(f"Erro ao executar bot: {e}")