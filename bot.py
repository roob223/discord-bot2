import discord, os, smtplib
from discord.ext import commands

bot = commands.Bot(command_prefix='!')

@bot.event
async def on_ready():
    print('Bot ist bereit!')

@bot.command()
async def reaktion(ctx, server_id, channel_id, message, emoji):
    server = bot.get_guild(int(server_id))
    channel = server.get_channel(int(channel_id))

    await ctx.send('Login-Daten erforderlich...')

    # Hier fügen Sie den Login-Prozess mit verschiedenen E-Mail- und Passwort-Kombinationen ein

    for email, password in zip(emails, passwords):
        login_data = smtplib.SMTP('smtp.gmail.com', 587)
        login_data.starttls()
        login_data.login(email, password)
        login_data.quit()

        # Füge den Benutzer zum Server hinzu
        await channel.send(f'Willkommen {email}!')
        await channel.send(message)
        await channel.send(emoji)

bot.run('YOUR_TOKEN')
