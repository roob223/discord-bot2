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

# 🔄 TIMER UPDATE LOOP
@tasks.loop(seconds=60)
async def update_giveaways():
    for gid, g in list(giveaways.items()):
        remaining = g["end_time"] - datetime.utcnow()

        if remaining.total_seconds() <= 0:
            continue

        if remaining.total_seconds() > 3600:
            time_text = f"{int(remaining.total_seconds() // 3600)}h"
        else:
            time_text = f"{int(remaining.total_seconds() // 60)}m"

        embed = g["message"].embeds[0]
        embed.set_field_at(0, name="⏳ Verbleibend", value=f"`{time_text}`", inline=True)

        try:
            await g["message"].edit(embed=embed, view=g["view"])
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

        giveaway = giveaways.get(self.giveaway_id)

        if not giveaway:
            await interaction.followup.send("❌ Giveaway existiert nicht mehr.", ephemeral=True)
            return

        if interaction.user.id in giveaway["participants"]:
            await interaction.followup.send("❗ Du bist schon drin.", ephemeral=True)
            return

        giveaway["participants"].add(interaction.user.id)

        # 🔥 FIX: jetzt NUR sichtbar für User
        await interaction.followup.send("✅ Du bist im Giveaway!", ephemeral=True)

        # Update Teilnehmer Anzeige
        embed = giveaway["message"].embeds[0]
        embed.set_field_at(
            2,
            name="👥 Teilnehmer",
            value=f"`{len(giveaway['participants'])}`",
            inline=True
        )

        await giveaway["message"].edit(embed=embed, view=self)


# READY
@bot.event
async def on_ready():
    print(f"Online als {bot.user}")
    await bot.tree.sync()
    update_giveaways.start()


# 🎉 GIVEAWAY
@bot.tree.command(name="giveaway", description="Erstelle ein Giveaway")
@app_commands.describe(
    dauer="Dauer",
    einheit="min oder h",
    preis="Preis",
    gewinner="Gewinner Anzahl"
)
@app_commands.choices(einheit=[
    app_commands.Choice(name="Minuten", value="min"),
    app_commands.Choice(name="Stunden", value="h")
])
async def giveaway(interaction: discord.Interaction, dauer: int, einheit: app_commands.Choice[str], preis: str, gewinner: int):

    if interaction.user.id != ALLOWED_USER_ID:
        await interaction.response.send_message("❌ Keine Rechte", ephemeral=True)
        return

    if interaction.channel.id != ALLOWED_CHANNEL_ID:
        await interaction.response.send_message("❌ Falscher Channel", ephemeral=True)
        return

    if einheit.value == "h":
        end_time = datetime.utcnow() + timedelta(hours=dauer)
        time_text = f"{dauer}h"
    else:
        end_time = datetime.utcnow() + timedelta(minutes=dauer)
        time_text = f"{dauer}m"

    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=f"💎 **{preis}**",
        color=discord.Color.blurple()
    )

    embed.add_field(name="⏳ Verbleibend", value=f"`{time_text}`", inline=True)
    embed.add_field(name="🏆 Gewinner", value=f"`{gewinner}`", inline=True)
    embed.add_field(name="👥 Teilnehmer", value="`0`", inline=True)

    embed.set_footer(text="Klicke auf den Button um teilzunehmen!")

    view = JoinButton(str(interaction.id))

    await interaction.response.send_message(embed=embed, view=view)
    msg = await interaction.original_response()

    giveaways[str(interaction.id)] = {
        "end_time": end_time,
        "preis": preis,
        "gewinner": gewinner,
        "participants": set(),
        "message": msg,
        "view": view
    }

    bot.loop.create_task(end_giveaway(str(interaction.id)))


# 🎉 ENDE
async def end_giveaway(gid):
    g = giveaways[gid]

    wait = (g["end_time"] - datetime.utcnow()).total_seconds()
    if wait > 0:
        await asyncio.sleep(wait)

    participants = list(g["participants"])

    if not participants:
        await g["message"].channel.send("❌ Keine Teilnehmer")
    else:
        winners = random.sample(participants, min(len(participants), g["gewinner"]))

        text = "\n".join([f"<@{w}>" for w in winners])

        await g["message"].channel.send(
            f"🎉 **GIVEAWAY BEENDET** 🎉\n\n🏆 Gewinner:\n{text}\n\n💎 {g['preis']}"
        )

    embed = g["message"].embeds[0]
    embed.title = "🎉 GIVEAWAY BEENDET"
    embed.color = discord.Color.red()

    await g["message"].edit(embed=embed, view=None)

    del giveaways[gid]


# 🔁 REROLL
@bot.tree.command(name="reroll", description="Neuer Gewinner")
async def reroll(interaction: discord.Interaction, message_id: str):

    if interaction.user.id != ALLOWED_USER_ID:
        await interaction.response.send_message("❌ Keine Rechte", ephemeral=True)
        return

    g = giveaways.get(message_id)

    if not g:
        await interaction.response.send_message("❌ Giveaway nicht gefunden", ephemeral=True)
        return

    if not g["participants"]:
        await interaction.response.send_message("❌ Keine Teilnehmer", ephemeral=True)
        return

    winner = random.choice(list(g["participants"]))

    await interaction.response.send_message(f"🔁 Neuer Gewinner: <@{winner}> 🎉")


bot.run(TOKEN)
