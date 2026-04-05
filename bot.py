import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
from datetime import datetime, date
import re

TOKEN = os.getenv("TOKEN")

STOCK_CHANNEL_ID = 1490321095503384739
LOG_CHANNEL_ID = 1490325916725940385
PANEL_CHANNEL_ID = 1490322325936144616  

GEN_ROLE_ID = 1490321899266506913
OWNER_ID = 1296572872441204748

DAILY_LIMIT = 40
COOLDOWN = 30

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

stock_message = None
usage = {}
cooldowns = {}
rainbow_index = 0

RAINBOW_COLORS = [
    discord.Color.red(),
    discord.Color.orange(),
    discord.Color.yellow(),
    discord.Color.green(),
    discord.Color.blue(),
    discord.Color.purple()
]

generators = {
    "Discord": "discord.txt",
    "Steam": "steam.txt",
    "Netflix": "netflix.txt",
    "FiveMReady": "fivemready.txt",
    "CapCut": "capcut.txt",
    "Disney+": "disney+.txt",
    "Crunchyroll": "crunchyroll.txt",
    "IPVanish": "ipvanish.txt",
    "Wondershare Filmora": "filmora.txt",
    "AMC+ Lifetime": "amc.txt",
    "Xbox Accounts – Aged 1 Month": "xbox.txt",
    "Prime Video": "prime.txt",
}

emoji_map = {
    "Discord": "💬",
    "Steam": "🎮",
    "Netflix": "🎬",
    "FiveMReady": "🚗",
    "CapCut": "✂️",
    "Disney+": "🏰",
    "Crunchyroll": "🍥",
    "IPVanish": "🛡️",
    "Wondershare Filmora": "🎞️",
    "AMC+ Lifetime": "📺",
    "Xbox Accounts – Aged 1 Month": "🎮",
    "Prime Video": "📦",
}

# 🔥 FIX: KEEP FULL LINE (MIT WEBMAIL ETC.)
def extract_account(line):
    line = line.strip()
    if not line:
        return None

    # Wenn irgendeine Email drin ist → komplette Zeile behalten
    if re.search(r'[^\s]+@[^\s]+', line):
        return line

    return None


def get_account(file):
    if not os.path.exists(file):
        return None

    with open(file, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    if not lines:
        return None

    acc = lines[0].strip()

    with open(file, "w", encoding="utf-8") as f:
        f.writelines(lines[1:])

    return acc


def check_reset(user_id):
    today = str(date.today())
    if user_id not in usage or usage[user_id]["date"] != today:
        usage[user_id] = {"count": 0, "date": today}


# 🔥 STOCK UPDATE
async def update_stock():
    global stock_message, rainbow_index

    channel = bot.get_channel(STOCK_CHANNEL_ID)
    if not channel:
        return

    total = 0
    text = ""

    for name, file in generators.items():
        count = 0
        if os.path.exists(file):
            with open(file, "r", encoding="utf-8") as f:
                count = sum(1 for _ in f)

        total += count
        status = "🟢" if count > 0 else "🔴"
        text += f"{emoji_map.get(name)} {name} → {count} {status}\n"

    color = RAINBOW_COLORS[rainbow_index % len(RAINBOW_COLORS)]
    rainbow_index += 1

    embed = discord.Embed(
        title="🔥 LIVE GENERATOR STOCK 🔥",
        description=f"💎 TOTAL: {total}\n\n{text}",
        color=color
    )

    if stock_message:
        await stock_message.edit(embed=embed)
    else:
        stock_message = await channel.send(embed=embed)


@tasks.loop(seconds=5)
async def rainbow_loop():
    await update_stock()


# 🔥 GEN SYSTEM
class GenSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=name, emoji=emoji_map.get(name)) for name in generators]
        super().__init__(placeholder="Select Generator", options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)

        if GEN_ROLE_ID not in [r.id for r in interaction.user.roles]:
            return await interaction.response.send_message("❌ No access", ephemeral=True)

        if user_id in cooldowns:
            remaining = COOLDOWN - (datetime.utcnow() - cooldowns[user_id]).total_seconds()
            if remaining > 0:
                return await interaction.response.send_message(f"⏳ Wait {int(remaining)}s", ephemeral=True)

        check_reset(user_id)

        if usage[user_id]["count"] >= DAILY_LIMIT:
            return await interaction.response.send_message("🚫 Daily limit reached", ephemeral=True)

        gen = self.values[0]
        file = generators[gen]

        acc = get_account(file)

        if not acc:
            return await interaction.response.send_message("❌ Out of stock", ephemeral=True)

        usage[user_id]["count"] += 1
        cooldowns[user_id] = datetime.utcnow()

        # ✅ SEND FULL DATA
        embed = discord.Embed(
            title="🎁 ACCOUNT GENERATED",
            description=f"💎 {gen}\n━━━━━━━━━━━━━━\n```{acc}```\n━━━━━━━━━━━━━━\n🌐 Includes full access (webmail etc.)",
            color=discord.Color.blurple()
        )

        await interaction.user.send(embed=embed)
        await interaction.response.send_message("✅ Check your DM", ephemeral=True)

        # 🔥 LOGS
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(
                title="📊 GEN LOG",
                description=(
                    f"👤 User: {interaction.user.mention}\n"
                    f"🎮 Generator: {gen}\n"
                    f"📈 Usage: {usage[user_id]['count']}/{DAILY_LIMIT}"
                ),
                color=discord.Color.green()
            )
            await log_channel.send(embed=log_embed)

        await update_stock()


class GenView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(GenSelect())


@bot.tree.command(name="gen")
async def gen(interaction: discord.Interaction):
    if GEN_ROLE_ID not in [r.id for r in interaction.user.roles]:
        return await interaction.response.send_message("❌ No access", ephemeral=True)

    await interaction.response.send_message("Select Generator:", view=GenView(), ephemeral=True)


# 🔥 FILES (ONLY OWNER)
@bot.tree.command(name="files")
@app_commands.describe(generator="Generator", file="Upload .txt")
@app_commands.choices(generator=[app_commands.Choice(name=x, value=x) for x in generators])
async def files(interaction: discord.Interaction, generator: app_commands.Choice[str], file: discord.Attachment):

    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("❌ Only Owner", ephemeral=True)

    content = await file.read()
    text = content.decode("utf-8", errors="ignore")

    lines = []

    for line in text.split("\n"):
        acc = extract_account(line)
        if acc:
            lines.append(acc)

    path = generators[generator.value]

    with open(path, "a", encoding="utf-8") as f:
        for l in lines:
            f.write(l + "\n")

    await interaction.response.send_message(
        f"✅ Added {len(lines)} accounts",
        ephemeral=True
    )

    await update_stock()


# 🔥 PANEL (DEIN ALTER)
class ClearModal(discord.ui.Modal, title="Clear Generator"):
    gen_name = discord.ui.TextInput(label="Generator Name")

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID:
            return await interaction.response.send_message("❌ No access", ephemeral=True)

        gen = self.gen_name.value.strip()

        if gen not in generators:
            return await interaction.response.send_message("❌ Invalid Generator", ephemeral=True)

        open(generators[gen], "w").close()

        await interaction.response.send_message(f"✅ Cleared {gen}", ephemeral=True)
        await update_stock()


class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🧹 Clear Generator", style=discord.ButtonStyle.red)
    async def clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ClearModal())


# 🔥 READY
@bot.event
async def on_ready():
    print(f"✅ Online: {bot.user}")
    await bot.tree.sync()

    await update_stock()
    rainbow_loop.start()

    channel = bot.get_channel(PANEL_CHANNEL_ID)
    if channel:
        await channel.send("🛠️ Control Panel", view=PanelView())


bot.run(TOKEN)
