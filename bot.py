import discord
from discord import app_commands
from discord.ext import commands

intents = discord.Intents.default()
intents.members = True  # wichtig für User-Infos

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot ist online als {bot.user}")

# /lookup command
@bot.tree.command(name="lookup", description="Zeigt Infos über einen Discord User")
@app_commands.describe(user="Der User den du nachschlagen willst")
async def lookup(interaction: discord.Interaction, user: discord.User):

    embed = discord.Embed(title="🔍 User Lookup", color=discord.Color.blue())

    embed.add_field(name="Username", value=user.name, inline=False)
    embed.add_field(name="ID", value=user.id, inline=False)
    embed.add_field(name="Account erstellt am", value=user.created_at.strftime("%d.%m.%Y"), inline=False)

    if user.avatar:
        embed.set_thumbnail(url=user.avatar.url)

    await interaction.response.send_message(embed=embed)

bot.run("DEIN_BOT_TOKEN")
