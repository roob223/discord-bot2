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
RESULT_CHANNEL_ID = 1488964567563501617  # Gewinner Channel

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

giveaways = {}

# 🕒 Zeit Parser
def parse_time(time_str):
    try:
        if time_str.endswith("h"):
            return int(time_str[:-1]) * 60
        elif time_str.endswith("d"):
            return int(time_str[:-1]) * 1440
        else:
            return int(time_str)
    except:
        return None


# 🎉 Button FIXED
class JoinButton(discord.ui.View):
    def __init__(self, giveaway_id):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id

    @discord.ui.button(label="🎉 Beitreten", style=discord.ButtonStyle.green)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            giveaway = giveaways.get(self.giveaway_id)

            if not giveaway:
                await interaction.response.send_message("❌ Giveaway existiert nicht mehr.", ephemeral=True)
                return

            if interaction.user.bot:
                await interaction.response.send_message("❌ Bots dürfen nicht teilnehmen!", ephemeral=True)
                return

            member = interaction.guild.get_member(interaction.user.id)

            if not member:
                await interaction.response.send_message("❌ Fehler.", ephemeral=True)
                return

            if interaction.user.id in giveaway["participants"]:
                await interaction.response.send_message("❗ Du bist schon dabei!", ephemeral=True)
                return

            giveaway["participants"].add(interaction.user.id)

            await interaction.response.send_message("✅ Erfolgreich beigetreten!", ephemeral=True)

            embed = giveaway["message"].embeds[0]
            embed.set_field_at(2, name="👥 Teilnehmer", value=str(len(giveaway["participants"])), inline=True)
            await giveaway["message"].edit(embed=embed, view=self)

        except Exception as e:
            print("Button Fehler:", e)


# Ready
@bot.event
async def on_ready():
    print(f"Online als {bot.user}")
    await bot.tree.sync()


# 🎉 Command
@bot.tree.command(name="giveaway", description="Erstelle ein Giveaway")
@app_commands.describe(
    dauer="z.B: 10 / 2h / 1d",
    preis="Was gibt es zu gewinnen?",
    gewinner="Anzahl der Gewinner"
)
async def giveaway(interaction: discord.Interaction, dauer: str, preis: str, gewinner: int):

    if interaction.user.id != ALLOWED_USER_ID:
        await interaction.response.send_message("❌ Keine Rechte", ephemeral=True)
        return

    if interaction.channel.id != ALLOWED_CHANNEL_ID:
        await interaction.response.send_message("❌ Falscher Channel", ephemeral=True)
        return

    minutes = parse_time(dauer)

    if not minutes:
        await interaction.response.send_message("❌ Format: 10 / 2h / 1d", ephemeral=True)
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

    bot.loop.create_task(end_giveaway(str(interaction.id)))


# 🎉 ENDE FIXED
async def end_giveaway(giveaway_id):
    giveaway = giveaways[giveaway_id]

    wait_time = (giveaway["end_time"] - datetime.utcnow()).total_seconds()

    if wait_time > 0:
        await asyncio.sleep(wait_time)

    participants = list(giveaway["participants"])
    channel = bot.get_channel(RESULT_CHANNEL_ID)

    if not channel:
        print("Channel nicht gefunden")
        return

    if not participants:
        await channel.send("❌ Niemand hat teilgenommen.")
    else:
        winners = random.sample(participants, min(len(participants), giveaway["gewinner"]))

        winner_mentions = " ".join([f"<@{w}>" for w in winners])

        await channel.send(
            f"🎉 Gewinner: {winner_mentions}\n"
            f"🏆 Preis: **{giveaway['preis']}**"
        )

    embed = giveaway["message"].embeds[0]
    embed.title = "🎉 GIVEAWAY BEENDET"
    embed.color = discord.Color.red()

    await giveaway["message"].edit(embed=embed, view=None)

    del giveaways[giveaway_id]


# Start
bot.run(TOKEN)
