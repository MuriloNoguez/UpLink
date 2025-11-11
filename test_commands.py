import discord
from discord.ext import commands
import asyncio

# Configuração simples
TOKEN = "MTQzNzgxNTI0NTY5NDMwODQwNA.GqAmXW.BNJ3_qBvgOYYIQDCUdBRhBW1Ghi3PrYC4s_FXg"

intents = discord.Intents.default()
intents.message_content = True

class TestBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
    
    async def setup_hook(self):
        # Sincronizar comandos
        try:
            synced = await self.tree.sync()
            print(f"✅ Sincronizados {len(synced)} comandos")
            for cmd in synced:
                print(f"  - /{cmd.name}: {cmd.description}")
        except Exception as e:
            print(f"❌ Erro ao sincronizar: {e}")
    
    async def on_ready(self):
        print(f"\n🟢 Bot {self.user} está online!")
        print(f"🌐 Servidores: {len(self.guilds)}")
        for guild in self.guilds:
            print(f"  - {guild.name} (ID: {guild.id})")

bot = TestBot()

@bot.tree.command(name="test", description="Comando de teste simples")
async def test_command(interaction: discord.Interaction):
    await interaction.response.send_message("✅ Comandos slash funcionando!", ephemeral=True)

@bot.tree.command(name="ticket", description="🎫 Sistema de tickets")
async def ticket_command(interaction: discord.Interaction):
    await interaction.response.send_message("🎫 Sistema de tickets em desenvolvimento!", ephemeral=True)

if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"Erro: {e}")