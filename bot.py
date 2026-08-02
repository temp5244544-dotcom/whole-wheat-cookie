import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord.ext import commands

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_web_server():
    server = HTTPServer(('0.0.0.0', 10000), SimpleHTTPRequestHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

BUMP_CHANNEL_ID = 1532491739120795749
ROLE_TO_PING_ID = 1533497382191501342

DISBOARD_BOT_ID = 302050872383242240
DISCADIA_BOT_ID = 1010660655822508153

DISBOARD_COOLDOWN = 2 * 60 * 60
DISCADIA_COOLDOWN = 1 * 60 * 60

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

active_timers = {"disboard": None, "discadia": None}

def get_role_mention():
    return f"<@&{ROLE_TO_PING_ID}> " if ROLE_TO_PING_ID else ""

async def schedule_reminder(channel, service_name, seconds, ping_message):
    try:
        await asyncio.sleep(seconds)
        role_tag = get_role_mention()
        await channel.send(f"🔔 {role_tag}{ping_message}")
    except asyncio.CancelledError:
        pass
    finally:
        active_timers[service_name] = None

def reset_timer(service_name, task):
    if active_timers[service_name] and not active_timers[service_name].done():
        active_timers[service_name].cancel()
    active_timers[service_name] = task

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if BUMP_CHANNEL_ID and message.channel.id != BUMP_CHANNEL_ID:
        await bot.process_commands(message)
        return

    content_lower = message.content.lower()

    if content_lower == "!bumpstop disboard" or content_lower == "!bumpstop all":
        if active_timers["disboard"] and not active_timers["disboard"].done():
            active_timers["disboard"].cancel()
            active_timers["disboard"] = None
            await message.channel.send("🛑 **Disboard timer stopped!**")
        else:
            await message.channel.send("⚠️ No active Disboard timer running.")

    if content_lower == "!bumpstop discadia" or content_lower == "!bumpstop all":
        if active_timers["discadia"] and not active_timers["discadia"].done():
            active_timers["discadia"].cancel()
            active_timers["discadia"] = None
            await message.channel.send("🛑 **Discadia timer stopped!**")
        else:
            await message.channel.send("⚠️ No active Discadia timer running.")

    is_disboard = message.author.id == DISBOARD_BOT_ID
    is_disboard_success = is_disboard and (
        "bump done" in content_lower or 
        (message.embeds and "bump done" in str(message.embeds[0].description).lower())
    )
    if is_disboard_success or content_lower.startswith("!bumped disboard"):
        await message.channel.send("⏱️ **Disboard bump recorded!** Set timer for 2 hours.")
        task = asyncio.create_task(
            schedule_reminder(
                message.channel, 
                "disboard", 
                DISBOARD_COOLDOWN, 
                "**Disboard is ready to bump!** Type `/bump` now!"
            )
        )
        reset_timer("disboard", task)

    is_discadia = message.author.id == DISCADIA_BOT_ID
    is_discadia_success = is_discadia and (
        "bumped" in content_lower or 
        (message.embeds and "successful" in str(message.embeds[0].description).lower())
    )
    if is_discadia_success or content_lower.startswith("!bumped discadia"):
        await message.channel.send("⏱️ **Discadia bump recorded!** Set timer for 1 hour.")
        task = asyncio.create_task(
            schedule_reminder(
                message.channel, 
                "discadia", 
                DISCADIA_COOLDOWN, 
                "**Discadia is ready to bump!** Time to bump again!"
            )
        )
        reset_timer("discadia", task)

    await bot.process_commands(message)

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
