import discord
from discord.ext import commands, tasks
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
edit_lock = asyncio.Lock()  # 🔥 WICHTIG

# 🔥 TIME
def get_time_left(end_time):
    remaining = int((end_time - datetime.utcnow()).total_seconds())

    if remaining <= 0:
        return "0m"

    h = remaining // 3600
    m = (remaining % 3600) // 60

    return f"{h}h {m}m" if h > 0 else f"{m}m"


# 🔥 EMBED
def build_embed(g):
    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=f"💎 **{g['preis']}**\n\n✨ Klicke unten um teilzunehmen!",
        color=discord.Color.from_rgb(255, 0, 200)
    )

    embed.add_field(name="⏳ Verbleibend", value=f"`{get_time_left(g['end_time'])}`", inline=True)
    embed.add_field(name="🏆 Gewinner", value=f"`{g['gewinner']}`", inline=True)
    embed.add_field(name="👥 Teilnehmer", value=f"`{len(g['participants'])}`", inline=True)

    embed.set_footer(text="🔥 Viel Glück!")

    return embed


# 🔄 TIMER LOOP
@tasks.loop(seconds=20)
async def update_giveaways():
    async with edit_lock:
        for gid, g in giveaways.items():
            if datetime.utcnow() >= g["end_time"]:
                continue

            try:
                await g["message"].edit(embed=build_embed(g), view=g["view"])
            except:
                pass


# 🎉 BUTTON
class JoinButton(discord.ui.View):
    def __init__(self, giveaway_id):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id

    @discord.ui.button(label="🎉 Beitreten", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        g = giveaways.get(self.giveaway_id)

        if not g:
            return await interaction.followup.send("❌ Giveaway weg.", ephemeral=True)

        if interaction.user.id in g["participants"]:
            return await interaction.followup.send("❗ Schon drin.", ephemeral=True)

        # ✅ Teilnehmer add
        g["participants"].add(interaction.user.id)

        await interaction.followup.send("✅ Du bist im Giveaway!", ephemeral=True)

        # 🔥 LOCK verhindert überschreiben
        async with edit_lock:
            await g["message"].edit(embed=build_embed(g), view=self)


# READY
@bot.event
async def on_ready():
    print(f"Online als {bot.user}")
    await bot.tree.sync()
    update_giveaways.start()


# 🎉 COMMAND
@bot.tree.command(name="giveaway")
@app_commands.describe(dauer="Zahl", einheit="min/h", preis="Preis", gewinner="Gewinner")
@app_commands.choices(einheit=[
    app_commands.Choice(name="Minuten", value="min"),
    app_commands.Choice(name="Stunden", value="h")
])
async def giveaway(interaction: discord.Interaction, dauer: int, einheit: app_commands.Choice[str], preis: str, gewinner: int):

    if interaction.user.id != ALLOWED_USER_ID:
        return await interaction.response.send_message("❌ Keine Rechte", ephemeral=True)

    if interaction.channel.id != ALLOWED_CHANNEL_ID:
        return await interaction.response.send_message("❌ Falscher Channel", ephemeral=True)

    end_time = datetime.utcnow() + (
        timedelta(hours=dauer) if einheit.value == "h"
        else timedelta(minutes=dauer)
    )

    view = JoinButton(str(interaction.id))

    await interaction.response.send_message("🎉 Erstelle Giveaway...")
    msg = await interaction.original_response()

    giveaways[str(interaction.id)] = {
        "end_time": end_time,
        "preis": preis,
        "gewinner": gewinner,
        "participants": set(),
        "message": msg,
        "view": view
    }

    await msg.edit(embed=build_embed(giveaways[str(interaction.id)]), view=view)

    bot.loop.create_task(end_giveaway(str(interaction.id)))


# 🎉 ENDE
async def end_giveaway(gid):
    g = giveaways[gid]

    wait = (g["end_time"] - datetime.utcnow()).total_seconds()
    if wait > 0:
        await asyncio.sleep(wait)

    participants = list(g["participants"])
    channel = g["message"].channel

    if not participants:
        await channel.send("❌ Keine Teilnehmer")
    else:
        winners = random.sample(participants, min(len(participants), g["gewinner"]))

        await channel.send(
            "🎉 Gewinner:\n" + "\n".join([f"<@{w}>" for w in winners])
        )

    await g["message"].edit(
        embed=discord.Embed(title="🎉 BEENDET", color=discord.Color.red()),
        view=None
    )

    del giveaways[gid]


bot.run(TOKEN)
