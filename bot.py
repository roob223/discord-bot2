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

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

giveaways = {}

# 🕒 Dauer Parser (MIN, STUNDEN, TAGE)
def parse_time(time_str):
    try:
        if time_str.endswith("h"):
            return int(time_str[:-1]) * 60
        elif time_str.endswith("d"):
            return int(time_str[:-1]) * 1440
        else:
            return int(time_str)  # Minuten
    except:
        return None


# 🎉 Button
class JoinButton(discord.ui.View):
    def __init__(self, giveaway_id):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id

    @discord.ui.button(label="🎉 Beitreten", style=discord.ButtonStyle.green)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        giveaway = giveaways.get(self.giveaway_id)

        if not giveaway:
            await interaction.response.send_message("❌ Giveaway existiert nicht mehr.", ephemeral=True)
            return

        if interaction.user.bot:
            await interaction.response.send_message("❌ Bots dürfen nicht teilnehmen!", ephemeral=True)
            return

        if datetime.utcnow() - interaction.user.created_at < timedelta(days=7):
            await interaction.response.send_message("❌ Account zu neu!", ephemeral=True)
            return

        member = interaction.guild.get_member(interaction.user.id)
        if not member or not member.joined_at:
            await interaction.response.send_message("❌ Fehler beim Prüfen.", ephemeral=True)
            return

        if datetime.utcnow() - member.joined_at < timedelta(days=3):
            await interaction.response.send_message("❌ Du bist noch nicht lange genug auf dem Server!", ephemeral=True)
            return

        if interaction.user.id in giveaway["participants"]:
            await interaction.response.send_message("❗ Du bist schon dabei!", ephemeral=True)
            return

        giveaway["participants"].add(interaction.user.id)

        await interaction.response.send_message("✅ Erfolgreich beigetreten!", ephemeral=True)

        embed = giveaway["message"].embeds[0]
        embed.set_field_at(2, name="👥 Teilnehmer", value=str(len(giveaway["participants"])), inline=True)
        await giveaway["message"].edit(embed=embed, view=self)


# Ready
@bot.event
async def on_ready():
    print(f"Online als {bot.user}")
    try:
        await bot.tree.sync()
    except Exception as e:
        print(e)


# 🎉 Command
@bot.tree.command(name="giveaway", description="Erstelle ein Giveaway")
@app_commands.describe(
    dauer="z.B: 10 / 2h / 1d",
    preis="Was gibt es zu gewinnen?",
    gewinner="Anzahl der Gewinner"
)
async def giveaway(interaction: discord.Interaction, dauer: str, preis: str, gewinner: int):

    if interaction.user.id != ALLOWED_USER_ID:
        await interaction.response.send_message("❌ Du darfst das nicht!", ephemeral=True)
        return

    if interaction.channel.id != ALLOWED_CHANNEL_ID:
        await interaction.response.send_message("❌ Nur in diesem Channel erlaubt!", ephemeral=True)
        return

    minutes = parse_time(dauer)

    if not minutes:
        await interaction.response.send_message("❌ Falsches Format! Beispiel: 10 / 2h / 1d", ephemeral=True)
        return

    end_time = datetime.utcnow() + timedelta(minutes=minutes)

    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=f"**Preis:** {preis}",
        color=discord.Color.purple()
    )

    embed.add_field(name="⏳ Dauer", value=dauer, inline=True)
    embed.add_field(name="🏆 Gewinner", value=str(gewinner), inline=True)
    embed.add_field(name="👥 Teilnehmer", value="0", inline=True)
    embed.set_footer(text="Klicke auf den Button!")

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


# 🎉 ENDE
async def end_giveaway(giveaway_id):
    giveaway = giveaways[giveaway_id]

    wait_time = (giveaway["end_time"] - datetime.utcnow()).total_seconds()

    if wait_time > 0:
        await asyncio.sleep(wait_time)

    participants = list(giveaway["participants"])

    if not participants:
        await giveaway["message"].channel.send("❌ Niemand hat teilgenommen.")
    else:
        winners = random.sample(participants, min(len(participants), giveaway["gewinner"]))

        for winner in winners:
            await giveaway["message"].channel.send(
                f"🎉 <@{winner}> hat **{giveaway['preis']}** gewonnen!\n"
                f"👉 open a ticket for your key 🎟️"
            )

    embed = giveaway["message"].embeds[0]
    embed.title = "🎉 GIVEAWAY BEENDET"
    embed.color = discord.Color.red()

    await giveaway["message"].edit(embed=embed, view=None)

    del giveaways[giveaway_id]


# Start
bot.run(TOKEN)
