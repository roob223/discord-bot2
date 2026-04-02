import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

# ====== DATABASE SETUP ======
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    messages INTEGER DEFAULT 0
)
""")
conn.commit()

# ====== BOT SETUP ======
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ====== EVENTS ======
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = message.author.id

    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    data = cursor.fetchone()

    if data is None:
        cursor.execute("INSERT INTO users (user_id, messages) VALUES (?, ?)", (user_id, 1))
    else:
        cursor.execute("UPDATE users SET messages = messages + 1 WHERE user_id=?", (user_id,))

    conn.commit()

    await bot.process_commands(message)

# ====== /LOOKUP COMMAND ======
@bot.tree.command(name="lookup", description="Zeigt Infos über einen User")
@app_commands.describe(user="Der User")
async def lookup(interaction: discord.Interaction, user: discord.User):

    embed = discord.Embed(title="🔍 Advanced Lookup", color=discord.Color.purple())

    embed.add_field(name="Username", value=user.name, inline=False)
    embed.add_field(name="ID", value=user.id, inline=False)
    embed.add_field(name="Account erstellt", value=user.created_at.strftime("%d.%m.%Y"), inline=False)

    member = interaction.guild.get_member(user.id)

    if member:
        embed.add_field(name="Beigetreten", value=member.joined_at.strftime("%d.%m.%Y"), inline=False)
        roles = [role.name for role in member.roles if role.name != "@everyone"]
        embed.add_field(name="Rollen", value=", ".join(roles) if roles else "Keine", inline=False)

    # ====== DATABASE DATA ======
    cursor.execute("SELECT messages FROM users WHERE user_id=?", (user.id,))
    data = cursor.fetchone()

    messages = data[0] if data else 0

    embed.add_field(name="Nachrichten", value=messages, inline=False)

    if user.avatar:
        embed.set_thumbnail(url=user.avatar.url)

    await interaction.response.send_message(embed=embed)

# ====== START ======
bot.run("DEIN_BOT_TOKEN")
