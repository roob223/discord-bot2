import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
from datetime import datetime, timedelta
import os

TOKEN = os.getenv("TOKEN")

ALLOWED_USER_ID = 1296572872441204748
ALLOWED_CHANNEL_ID = 1488964567563501617

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

giveaways = {}

# 🔥 TIMER FORMAT
def format_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{int(hours)}h {int(minutes)}m"


# 🎉 BUTTON
class JoinButton(discord.ui.View):
    def __init__(self, giveaway_id):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id

    @discord.ui.button(label="🎉 Beitreten", style=discord.ButtonStyle.green)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        giveaway = giveaways.get(self.giveaway_id)

        if not giveaway:
            return await interaction.response.send_message("❌ Nicht gefunden", ephemeral=True, delete_after=5)

        if interaction.user.id in giveaway["participants"]:
            return await interaction.response.send_message("❗ Schon dabei", ephemeral=True, delete_after=5)

        giveaway["participants"].add(interaction.user.id)

        await interaction.response.send_message("✅ Beigetreten!", ephemeral=True, delete_after=5)


# READY
@bot.event
async def on_ready():
    print(f"Online als {bot.user}")
    await bot.tree.sync()


# 🎉 COMMAND
@bot.tree.command(name="giveaway", description="Giveaway erstellen")
@app_commands.describe(dauer="Zahl", einheit="min oder h", preis="Preis", gewinner="Gewinner")
@app_commands.choices(einheit=[
    app_commands.Choice(name="Minuten", value="min"),
    app_commands.Choice(name="Stunden", value="h")
])
async def giveaway(interaction: discord.Interaction, dauer: int, einheit: app_commands.Choice[str], preis: str, gewinner: int):

    if interaction.user.id != ALLOWED_USER_ID:
        return await interaction.response.send_message("❌ Keine Rechte", ephemeral=True)

    if einheit.value == "h":
        end_time = datetime.utcnow() + timedelta(hours=dauer)
    else:
        end_time = datetime.utcnow() + timedelta(minutes=dauer)

    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=f"💎 **{preis}**",
        color=discord.Color.purple()
    )

    embed.add_field(name="⏳ Verbleibend", value="Startet...", inline=True)
    embed.add_field(name="🏆 Gewinner", value=str(gewinner), inline=True)
    embed.add_field(name="👥 Teilnehmer", value="0", inline=True)

    view = JoinButton(str(interaction.id))

    await interaction.response.send_message(embed=embed, view=view)
    message = await interaction.original_response()

    giveaways[str(interaction.id)] = {
        "end_time": end_time,
        "preis": preis,
        "gewinner": gewinner,
        "participants": set(),
        "message": message
    }

    bot.loop.create_task(update_timer(str(interaction.id)))
    bot.loop.create_task(end_giveaway(str(interaction.id)))


# 🔄 TIMER LOOP
async def update_timer(giveaway_id):
    while giveaway_id in giveaways:
        giveaway = giveaways[giveaway_id]

        remaining = (giveaway["end_time"] - datetime.utcnow()).total_seconds()

        if remaining <= 0:
            break

        embed = giveaway["message"].embeds[0]

        embed.set_field_at(
            0,
            name="⏳ Verbleibend",
            value=f"`{format_time(remaining)}`",
            inline=True
        )

        embed.set_field_at(
            2,
            name="👥 Teilnehmer",
            value=f"`{len(giveaway['participants'])}`",
            inline=True
        )

        try:
            await giveaway["message"].edit(embed=embed)
        except:
            pass

        await asyncio.sleep(60)  # jede Minute


# 🎉 ENDE
async def end_giveaway(giveaway_id):
    giveaway = giveaways[giveaway_id]

    wait = (giveaway["end_time"] - datetime.utcnow()).total_seconds()
    if wait > 0:
        await asyncio.sleep(wait)

    participants = list(giveaway["participants"])
    channel = giveaway["message"].channel

    if not participants:
        await channel.send("❌ Niemand teilgenommen")
    else:
        winners = random.sample(participants, min(len(participants), giveaway["gewinner"]))

        await channel.send(
            f"🎉 Gewinner:\n" + "\n".join([f"<@{w}>" for w in winners])
        )

    del giveaways[giveaway_id]


# 🔁 REROLL
@bot.tree.command(name="reroll", description="Neuer Gewinner")
async def reroll(interaction: discord.Interaction, message_id: str):

    if interaction.user.id != ALLOWED_USER_ID:
        return await interaction.response.send_message("❌ Keine Rechte", ephemeral=True)

    giveaway = giveaways.get(message_id)

    if not giveaway:
        return await interaction.response.send_message("❌ Nicht gefunden", ephemeral=True)

    winner = random.choice(list(giveaway["participants"]))

    await interaction.response.send_message(f"🔁 Neuer Gewinner: <@{winner}> 🎉")


bot.run(TOKEN)
