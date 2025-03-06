import discord
import google.generativeai as genai
import os
import asyncio
from datetime import datetime, timedelta
import yt_dlp
from discord.ext import commands

# Load API keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)

reminders = []
expired_messages = []
music_queue = []


def parse_datetime(date_str):
    try:
        # Ensure input format is correct
        date_obj = datetime.strptime(date_str.strip(), "%Y-%m-%d %H:%M")
        return date_obj
    except Exception as e:
        print(f"Date parsing error: {e}")  # Debugging output
        return None


@bot.command()
async def remind(ctx, reminder_time: str, *, reminder_text: str):
    reminder_dt = parse_datetime(reminder_time)
    if not reminder_dt:
        await ctx.send("💔 Invalid date format! Use YYYY-MM-DD HH:MM")
        return
    if reminder_dt < datetime.now():
        await ctx.send("💔 Cannot set a reminder for the past!")
        return
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


async def reminder_task():
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.now()
        for reminder in reminders[:]:
            if now >= reminder["time"]:
                channel = bot.get_channel(reminder["channel_id"])
                if channel:
                    await channel.send(
                        f'🐿️ Reminder for {reminder["user_name"]}: {reminder["message"]}'
                    )
                reminders.remove(reminder)
        await asyncio.sleep(60)


async def auto_delete_messages():
    await bot.wait_until_ready()
    while not bot.is_closed():
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
                        pass
                expired_messages.remove(msg)
        await asyncio.sleep(60)


@bot.event
async def setup_hook():
    bot.loop.create_task(reminder_task())
    bot.loop.create_task(auto_delete_messages())


@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="general")
    if channel:
        await channel.send(
            f'🎉 Welcome {member.mention} to {member.guild.name}!')


@bot.command()
async def chat(ctx, *, user_input: str):
    try:
        response = model.generate_content(user_input)
        await ctx.send(response.text)
    except Exception as e:
        await ctx.send("💔 Error generating response. Try again later.")


@bot.command()
async def summarize(ctx, *, text: str):
    try:
        response = model.generate_content(f"Summarize this: {text}")
        await ctx.send(f'📝 Summary: {response.text}')
    except Exception as e:
        await ctx.send("💔 Error summarizing text. Try again later.")


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
    """Adds a song to the queue and plays if not already playing"""
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("💔 You need to be in a voice channel to play music!")
        return

    voice_channel = ctx.author.voice.channel
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    # Add song to queue
    music_queue.append({"url": url, "ctx": ctx})
    await ctx.send(f'🎵 Added to queue: {url}')

    if not vc:
        vc = await voice_channel.connect()

    if not vc.is_playing():
        await play_next(vc)


async def play_next(vc):
    """Plays the next song in the queue, if available"""
    if music_queue:
        song = music_queue.pop(0)
        url = song["url"]
        ctx = song["ctx"]

        ydl_opts = {'format': 'bestaudio', 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info['url']

        def after_play(err):
            if err:
                print(f"Error: {err}")
            bot.loop.create_task(play_next(vc))  # Play the next song

        vc.play(discord.FFmpegPCMAudio(url2), after=after_play)
        await ctx.send(f'🎶 Now playing: {url}')
    else:
        await vc.disconnect()


@bot.command()
async def skip(ctx):
    """Skips the current song and plays the next in queue"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Skipping current song!")
        await play_next(ctx.voice_client)
    else:
        await ctx.send("💔 No song is currently playing!")


@bot.command()
async def queue(ctx):
    """Displays the current song queue"""
    if music_queue:
        queue_text = '\n'.join(
            [f'{i+1}. {song["url"]}' for i, song in enumerate(music_queue)])
        await ctx.send(f'🎼 **Current Queue:**\n{queue_text}')
    else:
        await ctx.send("💔 The queue is empty!")


@bot.command()
async def stop(ctx):
    """Stops the music and clears the queue"""
    if ctx.voice_client:
        music_queue.clear()
        await ctx.voice_client.disconnect()
        await ctx.send("🔇 Music stopped and bot left the channel.")
    else:
        await ctx.send("💔 The bot is not in a voice channel!")


bot.run(DISCORD_BOT_TOKEN)
