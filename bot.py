import os
import asyncio
import discord
from discord.ext import commands

# Application/Bot IDs for popular bump services
DISBOARD_BOT_ID = 302050872383242240
DISCADIA_BOT_ID = 1010660655822508153  # Standard Discadia Bot ID

# Cooldown durations
DISBOARD_COOLDOWN = 2 * 60 * 60  # 2 Hours (7200s)
DISCADIA_COOLDOWN = 1 * 60 * 60  # 1 Hour (3600s)

# Setup Intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Track active timer tasks so we don't stack duplicates
active_timers = {
    "disboard": None,
    "discadia": None
}

async def schedule_reminder(channel, service_name, seconds, ping_message):
    """Waits for the cooldown and sends a SINGLE notification."""
    try:
        await asyncio.sleep(seconds)
        await channel.send(ping_message)
    except asyncio.CancelledError:
        # Occurs if a bump command was re-triggered early
        pass
    finally:
        active_timers[service_name] = None

def reset_timer(service_name, task):
    """Cancels any pending reminder task for a service and sets a new one."""
    if active_timers[service_name] and not active_timers[service_name].done():
        active_timers[service_name].cancel()
    active_timers[service_name] = task

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} - Ready for Disboard & Discadia tracking!")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    content_lower = message.content.lower()

    # --- DISBOARD TRACKING ---
    is_disboard_bot = message.author.id == DISBOARD_BOT_ID
    is_disboard_success = is_disboard_bot and (
        "Bump done" in message.content or 
        (message.embeds and "Bump done" in str(message.embeds[0].description))
    )
    is_disboard_manual = content_lower.startswith("!bumped disboard")

    if is_disboard_success or is_disboard_manual:
        await message.channel.send("⏱️ **Disboard bump recorded!** Set timer for 2 hours.")
        
        # Schedule the notification task
        task = asyncio.create_task(
            schedule_reminder(
                message.channel, 
                "disboard", 
                DISBOARD_COOLDOWN, 
                "🔔 **Disboard is ready!** Use `/bump` to bump the server on Disboard."
            )
        )
        reset_timer("disboard", task)

    # --- DISCADIA TRACKING ---
    is_discadia_bot = message.author.id == DISCADIA_BOT_ID
    is_discadia_success = is_discadia_bot and (
        "bumped" in content_lower or 
        (message.embeds and "successful" in str(message.embeds[0].description).lower())
    )
    is_discadia_manual = content_lower.startswith("!bumped discadia")

    if is_discadia_success or is_discadia_manual:
        await message.channel.send("⏱️ **Discadia bump recorded!** Set timer for 1 hour.")
        
        # Schedule the notification task
        task = asyncio.create_task(
            schedule_reminder(
                message.channel, 
                "discadia", 
                DISCADIA_COOLDOWN, 
                "🔔 **Discadia is ready!** You can now bump the server on Discadia again."
            )
        )
        reset_timer("discadia", task)

    await bot.process_commands(message)

# Reads token from Environment Variable (for 24/7 host) or fallback string
TOKEN = os.getenv("DISCORD_TOKEN", "YOUR_LOCAL_BOT_TOKEN_HERE")
bot.run(TOKEN)