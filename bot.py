import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord.ext import commands

# Simple web server to keep host alive (handles GET and HEAD for UptimeRobot)
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def log_message(self, format, *args):
        return

def run_web_server():
    server = HTTPServer(('0.0.0.0', 10000), SimpleHTTPRequestHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

# CONFIGURATION
BUMP_CHANNEL_ID = None

ROLE_TO_PING_ID = 1533479070136795329

DISBOARD_BOT_ID = 302050872383242240
DISCADIA_BOT_ID = 1222548162741538938

DISBOARD_COOLDOWN = 2 * 60 * 60
DISCADIA_COOLDOWN = 24 * 60 * 60

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
        await channel.send(f"{role_tag}{ping_message}")
    except asyncio.CancelledError:
        pass
    finally:
        active_timers[service_name] = None

def reset_timer(service_name, task):
    if active_timers[service_name] and not active_timers[service_name].done():
        active_timers[service_name].cancel()
    active_timers[service_name] = task

def extract_full_text(message: discord.Message) -> str:
    """Helper function to collect all text from message content and embeds."""
    text_list = [message.content or ""]
    for embed in message.embeds:
        if embed.title:
            text_list.append(embed.title)
        if embed.description:
            text_list.append(embed.description)
        for field in embed.fields:
            if field.name:
                text_list.append(field.name)
            if field.value:
                text_list.append(field.value)
    return " ".join(text_list).lower()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
        
    print(f"[ALL] {message.author.name}: {message.content[:50]}")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if BUMP_CHANNEL_ID and message.channel.id != BUMP_CHANNEL_ID:
        await bot.process_commands(message)
        return

    full_text = extract_full_text(message)
    content_lower = message.content.lower()

    # Console debug log whenever Disboard or Discadia sends a message
    if message.author.id in (DISBOARD_BOT_ID, DISCADIA_BOT_ID):
        print(f"[DEBUG] Received message from {message.author.name} ({message.author.id}): '{full_text}'")

    # --- Manual Override Commands ---
    if content_lower in ("!bumped discadia", "!discadia"):
        await message.channel.send("Discadia bump recorded manually! Set timer for 24 hours.")
        task = asyncio.create_task(
            schedule_reminder(message.channel, "discadia", DISCADIA_COOLDOWN, "Discadia is ready to bump")
        )
        reset_timer("discadia", task)
        return

    if content_lower in ("!bumped disboard", "!disboard"):
        await message.channel.send("Disboard bump recorded manually! Set timer for 2 hours.")
        task = asyncio.create_task(
            schedule_reminder(message.channel, "disboard", DISBOARD_COOLDOWN, "Disboard is ready to bump")
        )
        reset_timer("disboard", task)
        return

    # --- Cancel Commands ---
    if content_lower in ("!bumpstop disboard", "!bumpstop all"):
        if active_timers["disboard"] and not active_timers["disboard"].done():
            active_timers["disboard"].cancel()
            active_timers["disboard"] = None
            await message.channel.send("Disboard timer stopped.")
        else:
            await message.channel.send("No active Disboard timer running.")

    if content_lower in ("!bumpstop discadia", "!bumpstop all"):
        if active_timers["discadia"] and not active_timers["discadia"].done():
            active_timers["discadia"].cancel()
            active_timers["discadia"] = None
            await message.channel.send("Discadia timer stopped.")
        else:
            await message.channel.send("No active Discadia timer running.")

    # --- Automatic Disboard Detection ---
    is_disboard = message.author.id == DISBOARD_BOT_ID
    is_disboard_success = is_disboard and ("bump done" in full_text or "bump success" in full_text)

    if is_disboard_success:
        await message.channel.send("Disboard bump detected! Set timer for 2 hours.")
        task = asyncio.create_task(
            schedule_reminder(message.channel, "disboard", DISBOARD_COOLDOWN, "Disboard is ready to bump")
        )
        reset_timer("disboard", task)

    # --- Automatic Discadia Detection ---
    is_discadia = message.author.id == DISCADIA_BOT_ID
    is_discadia_success = is_discadia and "has been successfully bumped" in full_text

    if is_discadia_success:
        await message.channel.send("Discadia bump detected! Set timer for 24 hours.")
        task = asyncio.create_task(
            schedule_reminder(message.channel, "discadia", DISCADIA_COOLDOWN, "Discadia is ready to bump")
        )
        reset_timer("discadia", task)

    await bot.process_commands(message)

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
