import discord
import google.generativeai as genai
import os
import asyncio
from datetime import datetime, timedelta
import yt_dlp
import ffmpeg
from discord.ext import commands

# Load API keys from Replit Secrets
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Ensure API Keys Exist
if not GEMINI_API_KEY:
    print("💔 ERROR: GEMINI_API_KEY is missing!")
    exit()
if not DISCORD_BOT_TOKEN:
    print("💔 ERROR: DISCORD_BOT_TOKEN is missing!")
    exit()

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# Set up Discord bot with necessary intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Required for welcoming new users
intents.voice_states = True  # Required for music management
bot = commands.Bot(command_prefix="!", intents=intents)

# Store reminders
reminders = []
# Store messages to auto-delete
expired_messages = []
# Music queue
music_queue = []


async def reminder_task():
    while True:
        now = datetime.now()
        for reminder in reminders[:]:  # Copy list to avoid modification issues
            if now >= reminder["time"]:
                channel = bot.get_channel(reminder["channel_id"])
                if channel:
                    await channel.send(
                        f'🐿️ Reminder for {reminder["user_name"]}: {reminder["message"]}'
                    )
                reminders.remove(reminder)
        await asyncio.sleep(60)  # Check every minute


async def auto_delete_messages():
    while True:
        now = datetime.now()
        for msg in expired_messages[:]:
            if now >= msg["delete_at"]:
                channel = bot.get_channel(msg["channel_id"])
                if channel:
                    try:
                        message = await channel.fetch_message(msg["message_id"]
                                                              )
                        await message.delete()
                    except discord.NotFound:
                        pass  # Message was already deleted
                expired_messages.remove(msg)
        await asyncio.sleep(60)  # Check every minute


@bot.event
async def on_ready():
    print(f'🎉 Bot is online as {bot.user}')
    bot.loop.create_task(reminder_task())  # Start reminder checking loop
    bot.loop.create_task(auto_delete_messages())  # Start auto-delete loop


@bot.event
async def on_member_join(member):
    channel = discord.utils.get(
        member.guild.text_channels,
        name="general")  # Change to your welcome channel name
    if channel:
        await channel.send(
            f'🎉 Welcome {member.mention} to {member.guild.name}!')


@bot.command()
async def chat(ctx, *, user_input: str):
    if not user_input:
        await ctx.send("🐥 Please provide a message to chat with AI.")
        return
    try:
        response = model.generate_content(user_input)
        await ctx.send(response.text)
    except Exception as e:
        await ctx.send("💔 Error generating response. Try again later.")
        print(f"Error: {e}")


@bot.command()
async def remind(ctx, reminder_time: str, *, reminder_text: str):
    try:
        reminder_dt = datetime.strptime(reminder_time, "%Y-%m-%d %H:%M")
        reminders.append({
            "user_id": ctx.author.id,
            "user_name": ctx.author.name,
            "channel_id": ctx.channel.id,
            "message": reminder_text,
            "time": reminder_dt
        })
        await ctx.send(
            f'🎉 Reminder set for {reminder_dt.strftime("%Y-%m-%d %H:%M")}: {reminder_text}'
        )
    except ValueError:
        await ctx.send("💔 Invalid date format! Use YYYY-MM-DD HH:MM")


@bot.command()
async def expire(ctx, delete_after: int, *, message_text: str):
    msg = await ctx.send(message_text)
    delete_at = datetime.now() + timedelta(seconds=delete_after)
    expired_messages.append({
        "message_id": msg.id,
        "channel_id": ctx.channel.id,
        "delete_at": delete_at
    })
    await ctx.send(f'🕒 This message will be deleted in {delete_after} seconds.'
                   )


@bot.command()
async def poll(ctx, question: str, *options: str):
    if len(options) < 2 or len(options) > 10:
        await ctx.send("💔 Please provide between 2 and 10 options.")
        return
    poll_message = f'**{question}**\n\n'
    emojis = ["🐰", "🐶", "🐱", "🐻", "🦄", "🐸", "🐥", "🐢", "🦊", "🐼"]
    for i, option in enumerate(options):
        poll_message += f'{emojis[i]} {option}\n'
    poll_msg = await ctx.send(poll_message)
    for i in range(len(options)):
        await poll_msg.add_reaction(emojis[i])


@bot.command()
async def play(ctx, url: str):
    voice_channel = ctx.author.voice.channel
    if not voice_channel:
        await ctx.send("💔 You need to be in a voice channel to play music!")
        return
    vc = await voice_channel.connect()
    music_queue.append(url)
    await ctx.send(f'🎵 Added to queue: {url}')
    if not vc.is_playing():
        await play_next(ctx, vc)


async def play_next(ctx, vc):
    if music_queue:
        url = music_queue.pop(0)
        ydl_opts = {'format': 'bestaudio', 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info['url']
        vc.play(discord.FFmpegPCMAudio(url2),
                after=lambda e: bot.loop.create_task(play_next(ctx, vc)))
        await ctx.send(f'🎶 Now playing: {url}')
    else:
        await vc.disconnect()


@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Skipping current song!")
        await play_next(ctx, ctx.voice_client)


@bot.command()
async def queue(ctx):
    if music_queue:
        queue_text = '\n'.join(
            [f'{i+1}. {song}' for i, song in enumerate(music_queue)])
        await ctx.send(f'🎼 Current queue:\n{queue_text}')
    else:
        await ctx.send("💔 The queue is empty!")


@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("🔇 Music stopped and bot left the channel.")


# Run the bot
bot.run(DISCORD_BOT_TOKEN)
