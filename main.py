import discord
import google.generativeai as genai
import os
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
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f'🎉 Bot is online as {bot.user}')


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


# Run the bot
bot.run(DISCORD_BOT_TOKEN)
