import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
from datetime import datetime, timedelta
import os

# 🔑 TOKEN
TOKEN = os.getenv("TOKEN")

# 🔒 DEINE IDS
ALLOWED_USER_ID = 1296572872441204748
ALLOWED_CHANNEL_ID = 1488964567563501617

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

giveaways = {}

# 🎉 BUTTON VIEW
class JoinButton(discord.ui.View):
    def __init__(self, giveaway_id):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id

    @discord.ui.button(label="🎉 Beitreten", style=discord.ButtonStyle.green)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        giveaway = giveaways.get(self.giveaway_id)

        if not giveaway:
            await interaction.followup.send("❌ Giveaway existiert nicht mehr.")
            return

        if interaction.user.bot:
            await interaction.followup.send("❌ Bots dürfen nicht teilnehmen!")
            return

        member = interaction.guild.get_member(interaction.user.id)

        if not member or not member.joined_at:
            await interaction.followup.send("❌ Fehler beim Prüfen.")
            return

        if interaction.user.id in giveaway["participants"]:
            await interaction.followup.send("❗ Du bist schon dabei!")
            return

        giveaway["participants"].add(interaction.user.id)

        await interaction.followup.send("✅ Erfolgreich beigetreten!")

        embed = giveaway["message"].embeds[0]
        embed.set_field_at(
            2,
            name="👥 Teilnehmer",
            value=f"**{len(giveaway['participants'])}**",
            inline=True
        )

        await giveaway["message"].edit(embed=embed, view=self)


# READY
@bot.event
async def on_ready():
    print(f"Online als {bot.user}")
    try:
        await bot.tree.sync()
    except Exception as e:
        print(e)


# 🎉 GIVEAWAY COMMAND (JETZT MIT STUNDEN!)
@bot.tree.command(name="giveaway", description="Erstelle ein Giveaway")
@app_commands.describe(
    dauer="Dauer",
    einheit="Minuten oder Stunden",
    preis="Was gibt es zu gewinnen?",
    gewinner="Anzahl Gewinner"
)
@app_commands.choices(einheit=[
    app_commands.Choice(name="Minuten", value="min"),
    app_commands.Choice(name="Stunden", value="h")
])
async def giveaway(interaction: discord.Interaction, dauer: int, einheit: app_commands.Choice[str], preis: str, gewinner: int):

    if interaction.user.id != ALLOWED_USER_ID:
        await interaction.response.send_message("❌ Du darfst das nicht!", ephemeral=True)
        return

    if interaction.channel.id != ALLOWED_CHANNEL_ID:
        await interaction.response.send_message("❌ Nur in diesem Channel erlaubt!", ephemeral=True)
        return

    if einheit.value == "h":
        end_time = datetime.utcnow() + timedelta(hours=dauer)
        dauer_text = f"{dauer} Stunden"
    else:
        end_time = datetime.utcnow() + timedelta(minutes=dauer)
        dauer_text = f"{dauer} Minuten"

    embed = discord.Embed(
        title="🎉 **GIVEAWAY** 🎉",
        description=f"💎 **Preis:**\n> {preis}",
        color=discord.Color.from_rgb(255, 0, 200)
    )

    embed.add_field(name="⏳ Dauer", value=f"`{dauer_text}`", inline=True)
    embed.add_field(name="🏆 Gewinner", value=f"`{gewinner}`", inline=True)
    embed.add_field(name="👥 Teilnehmer", value="`0`", inline=True)
    embed.set_footer(text="Drücke auf den Button um teilzunehmen!")

    view = JoinButton(giveaway_id=str(interaction.id))

    await interaction.response.send_message(embed=embed, view=view)
    message = await interaction.original_response()

    giveaways[str(interaction.id)] = {
        "end_time": end_time,
        "preis": preis,
        "gewinner": gewinner,
        "participants": set(),
        "message": message
    }

    bot.loop.create_task(end_giveaway(str(interaction.id)))


# 🎉 GIVEAWAY ENDE
async def end_giveaway(giveaway_id):
    giveaway = giveaways[giveaway_id]

    wait_time = (giveaway["end_time"] - datetime.utcnow()).total_seconds()

    if wait_time > 0:
        await asyncio.sleep(wait_time)

    participants = list(giveaway["participants"])
    channel = giveaway["message"].channel

    if not participants:
        await channel.send("❌ Niemand hat teilgenommen.")
    else:
        winners = random.sample(participants, min(len(participants), giveaway["gewinner"]))

        winners_text = "\n".join([f"<@{w}>" for w in winners])

        await channel.send(
            f"🎉 **GIVEAWAY BEENDET** 🎉\n\n"
            f"🏆 Gewinner:\n{winners_text}\n\n"
            f"💎 Preis: **{giveaway['preis']}**"
        )

    embed = giveaway["message"].embeds[0]
    embed.title = "🎉 GIVEAWAY BEENDET"
    embed.color = discord.Color.red()

    await giveaway["message"].edit(embed=embed, view=None)

    del giveaways[giveaway_id]


# 🔁 REROLL COMMAND
@bot.tree.command(name="reroll", description="Ziehe neuen Gewinner")
async def reroll(interaction: discord.Interaction, message_id: str):

    if interaction.user.id != ALLOWED_USER_ID:
        await interaction.response.send_message("❌ Du darfst das nicht!", ephemeral=True)
        return

    giveaway = giveaways.get(message_id)

    if not giveaway:
        await interaction.response.send_message("❌ Giveaway nicht gefunden!", ephemeral=True)
        return

    participants = list(giveaway["participants"])

    if not participants:
        await interaction.response.send_message("❌ Keine Teilnehmer!", ephemeral=True)
        return

    winner = random.choice(participants)

    await interaction.response.send_message(
        f"🔁 Neuer Gewinner: <@{winner}> 🎉"
    )


# START
bot.run(TOKEN)
