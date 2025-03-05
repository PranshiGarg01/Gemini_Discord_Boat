import discord
import google.generativeai as genai
import os
import asyncio
from datetime import datetime
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
bot = commands.Bot(command_prefix="!", intents=intents)

# Store reminders
reminders = []


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


@bot.event
async def on_ready():
    print(f'🎉 Bot is online as {bot.user}')
    bot.loop.create_task(reminder_task())  # Start reminder checking loop


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


# Run the bot
bot.run(DISCORD_BOT_TOKEN)
