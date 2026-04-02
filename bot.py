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

# 🔥 TIME FORMAT (FIX)
def get_time_left(end_time):
    remaining = end_time - datetime.utcnow()
    total = int(remaining.total_seconds())

    if total <= 0:
        return "0m"

    hours = total // 3600
    minutes = (total % 3600) // 60

    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


# 🔥 EMBED BUILDER (IMMER FRESH)
def build_embed(g):
    return discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=f"💎 **{g['preis']}**\n\n✨ Klicke unten um teilzunehmen!",
        color=discord.Color.from_rgb(255, 0, 200)
    ).add_field(
        name="⏳ Verbleibend",
        value=f"`{get_time_left(g['end_time'])}`",
        inline=True
    ).add_field(
        name="🏆 Gewinner",
        value=f"`{g['gewinner']}`",
        inline=True
    ).add_field(
        name="👥 Teilnehmer",
        value=f"`{len(g['participants'])}`",
        inline=True
    ).set_footer(text="🔥 Viel Glück!")


# 🔄 TIMER LOOP (JETZT 100% FIX)
@tasks.loop(seconds=30)
async def update_giveaways():
    for gid, g in list(giveaways.items()):
        if datetime.utcnow() >= g["end_time"]:
            continue

        try:
            await g["message"].edit(
                embed=build_embed(g),
                view=g["view"]
            )
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

        g["participants"].add(interaction.user.id)

        await interaction.followup.send("✅ Du bist jetzt im Giveaway!", ephemeral=True)

        # 🔥 SOFORT UPDATE (kein delay mehr)
        await g["message"].edit(
            embed=build_embed(g),
            view=self
        )


# READY
@bot.event
async def on_ready():
    print(f"Online als {bot.user}")
    await bot.tree.sync()
    update_giveaways.start()


# 🎉 GIVEAWAY
@bot.tree.command(name="giveaway", description="Erstelle ein Giveaway")
@app_commands.describe(
    dauer="Zahl",
    einheit="min oder h",
    preis="Preis",
    gewinner="Gewinner"
)
@app_commands.choices(einheit=[
    app_commands.Choice(name="Minuten", value="min"),
    app_commands.Choice(name="Stunden", value="h")
])
async def giveaway(interaction: discord.Interaction, dauer: int, einheit: app_commands.Choice[str], preis: str, gewinner: int):

    if interaction.user.id != ALLOWED_USER_ID:
        return await interaction.response.send_message("❌ Keine Rechte", ephemeral=True)

    if interaction.channel.id != ALLOWED_CHANNEL_ID:
        return await interaction.response.send_message("❌ Falscher Channel", ephemeral=True)

    if einheit.value == "h":
        end_time = datetime.utcnow() + timedelta(hours=dauer)
    else:
        end_time = datetime.utcnow() + timedelta(minutes=dauer)

    view = JoinButton(str(interaction.id))

    await interaction.response.send_message("🎉 Giveaway wird erstellt...")
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

        text = "\n".join([f"<@{w}>" for w in winners])

        await channel.send(
            f"🎉 **GIVEAWAY BEENDET** 🎉\n\n🏆 Gewinner:\n{text}\n\n💎 {g['preis']}"
        )

    await g["message"].edit(
        embed=discord.Embed(
            title="🎉 GIVEAWAY BEENDET",
            description=f"💎 **{g['preis']}**",
            color=discord.Color.red()
        ),
        view=None
    )

    del giveaways[gid]


# 🔁 REROLL
@bot.tree.command(name="reroll", description="Neuer Gewinner")
async def reroll(interaction: discord.Interaction, message_id: str):

    if interaction.user.id != ALLOWED_USER_ID:
        return await interaction.response.send_message("❌ Keine Rechte", ephemeral=True)

    g = giveaways.get(message_id)

    if not g or not g["participants"]:
        return await interaction.response.send_message("❌ Fehler", ephemeral=True)

    winner = random.choice(list(g["participants"]))

    await interaction.response.send_message(f"🔁 Neuer Gewinner: <@{winner}> 🎉")


bot.run(TOKEN)
