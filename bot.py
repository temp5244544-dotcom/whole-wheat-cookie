import os
import asyncio
import threading
import time
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
BUMP_CHANNEL_ID = None  # None allows detection in all channels

ROLE_TO_PING_ID = 1533479070136795329

DISBOARD_BOT_ID = 302050872383242240
DISCADIA_BOT_ID = 1222548162741538938

DISBOARD_COOLDOWN = 2 * 60 * 60
DISCADIA_COOLDOWN = 24 * 60 * 60

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

active_timers = {"disboard": None, "discadia": None}
timer_end_times = {"disboard": None, "discadia": None}

def get_role_mention():
    return f"<@&{ROLE_TO_PING_ID}> " if ROLE_TO_PING_ID else ""

def format_time_left(service_name):
    end_time = timer_end_times[service_name]
    if end_time is None:
        return "unknown"
    seconds_left = int(end_time - time.time())
    if seconds_left <= 0:
        return "any moment now"
    hours = seconds_left // 3600
    minutes = (seconds_left % 3600) // 60
    seconds = seconds_left % 60
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"

def is_timer_running(service_name):
    return active_timers[service_name] and not active_timers[service_name].done()

async def schedule_reminder(channel, service_name, seconds, ping_message):
    try:
        await asyncio.sleep(seconds)
        role_tag = get_role_mention()
        await channel.send(f"{role_tag}{ping_message}")
    except asyncio.CancelledError:
        pass
    finally:
        active_timers[service_name] = None
        timer_end_times[service_name] = None

def start_timer(channel, service_name, cooldown, ping_message):
    if is_timer_running(service_name):
        active_timers[service_name].cancel()
    task = asyncio.create_task(schedule_reminder(channel, service_name, cooldown, ping_message))
    active_timers[service_name] = task
    timer_end_times[service_name] = time.time() + cooldown

def extract_full_text(message: discord.Message) -> str:
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

    full_text = extract_full_text(message)
    content_lower = message.content.lower().strip()

    if BUMP_CHANNEL_ID and message.channel.id != BUMP_CHANNEL_ID:
        await bot.process_commands(message)
        return

    # --- Manual Override Commands ---
    if content_lower in ("!bumped discadia", "!discadia"):
        if is_timer_running("discadia"):
            await message.channel.send(f"Discadia timer is already running. {format_time_left('discadia')} left.")
        else:
            await message.channel.send("Discadia bump recorded! Timer set for 24 hours.")
            start_timer(message.channel, "discadia", DISCADIA_COOLDOWN, "Discadia is ready to bump")
        return

    if content_lower in ("!bumped disboard", "!disboard"):
        if is_timer_running("disboard"):
            await message.channel.send(f"Disboard timer is already running. {format_time_left('disboard')} left.")
        else:
            await message.channel.send("Disboard bump recorded! Timer set for 2 hours.")
            start_timer(message.channel, "disboard", DISBOARD_COOLDOWN, "Disboard is ready to bump")
        return

    # --- Cancel Commands ---
    if content_lower == "!bumpstop all":
        if is_timer_running("disboard"):
            active_timers["disboard"].cancel()
            active_timers["disboard"] = None
            timer_end_times["disboard"] = None
            await message.channel.send("Stopped Disboard timer.")
        else:
            await message.channel.send("No active Disboard timer running.")
        if is_timer_running("discadia"):
            active_timers["discadia"].cancel()
            active_timers["discadia"] = None
            timer_end_times["discadia"] = None
            await message.channel.send("Stopped Discadia timer.")
        else:
            await message.channel.send("No active Discadia timer running.")
        return

    if content_lower == "!bumpstop disboard":
        if is_timer_running("disboard"):
            active_timers["disboard"].cancel()
            active_timers["disboard"] = None
            timer_end_times["disboard"] = None
            await message.channel.send("Stopped Disboard timer.")
        else:
            await message.channel.send("No active Disboard timer running.")
        return

    if content_lower == "!bumpstop discadia":
        if is_timer_running("discadia"):
            active_timers["discadia"].cancel()
            active_timers["discadia"] = None
            timer_end_times["discadia"] = None
            await message.channel.send("Stopped Discadia timer.")
        else:
            await message.channel.send("No active Discadia timer running.")
        return

    # --- Automatic Disboard Detection ---
    is_disboard = message.author.id == DISBOARD_BOT_ID
    is_disboard_success = is_disboard and ("bump done" in full_text or "bump success" in full_text)

    if is_disboard_success:
        if is_timer_running("disboard"):
            await message.channel.send(f"Disboard timer is already running. {format_time_left('disboard')} left.")
        else:
            await message.channel.send("Disboard bump detected! Timer set for 2 hours.")
            start_timer(message.channel, "disboard", DISBOARD_COOLDOWN, "Disboard is ready to bump")

    # --- Automatic Discadia Detection ---
    is_discadia = message.author.id == DISCADIA_BOT_ID
    has_interaction = hasattr(message, 'interaction_metadata') and message.interaction_metadata is not None
    is_discadia_success = is_discadia and (
        "has been successfully bumped" in full_text or
        "bumped" in full_text or
        has_interaction
    )

    if is_discadia_success:
        if is_timer_running("discadia"):
            await message.channel.send(f"Discadia timer is already running. {format_time_left('discadia')} left.")
        else:
            await message.channel.send("Discadia bump detected! Timer set for 24 hours.")
            start_timer(message.channel, "discadia", DISCADIA_COOLDOWN, "Discadia is ready to bump")

    await bot.process_commands(message)

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
