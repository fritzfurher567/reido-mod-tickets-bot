"""
main.py
Entry point for the bot. Loads environment variables, sets up intents,
loads all cogs, initializes the database, and starts the bot.

This is a stripped-down build of Nexus containing only the moderation
and ticket/modmail systems. Run with:  python main.py
"""

import asyncio
import logging
import os

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

import database as db
from database import init_db
from config import BOT_CREDIT

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX", "!")

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
log = logging.getLogger("bot")

intents = discord.Intents.default()
intents.members = True          # required for join/leave events
intents.message_content = True  # required for prefix commands / message-based features


class RestrictedCommandTree(app_commands.CommandTree):
    """
    A command tree that enforces per-command role restrictions before any
    command runs. The server owner and anyone with Administrator always pass.
    If a command has no restrictions configured, it's open to everyone
    (subject to whatever permission checks that command already has).
    Configure restrictions with /permission-restrict.
    """

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None or interaction.command is None:
            return True

        allowed = await self._permission_check(interaction)
        if allowed:
            asyncio.create_task(self._log_usage(interaction))
        return allowed

    async def _permission_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == interaction.guild.owner_id:
            return True

        if isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator:
            return True

        allowed_role_ids = await db.get_command_restrictions(interaction.guild.id, interaction.command.qualified_name)
        if not allowed_role_ids:
            return True  # no restriction configured for this command

        member_role_ids = {role.id for role in interaction.user.roles} if isinstance(interaction.user, discord.Member) else set()
        if member_role_ids.intersection(allowed_role_ids):
            return True

        await interaction.response.send_message(
            "🔒 You don't have a role that's permitted to use this command.", ephemeral=True
        )
        return False

    async def _log_usage(self, interaction: discord.Interaction):
        """Fire-and-forget audit logging — never blocks or fails the actual command."""
        try:
            import datetime as _dt
            timestamp = _dt.datetime.utcnow().isoformat()
            await db.add_audit_entry(interaction.guild.id, interaction.user.id, interaction.command.qualified_name, timestamp)

            config = await db.get_guild_config(interaction.guild.id)
            channel_id = config.get("audit_log_channel")
            if channel_id:
                channel = interaction.guild.get_channel(channel_id)
                if channel:
                    embed = discord.Embed(
                        description=f"{interaction.user.mention} used `/{interaction.command.qualified_name}` in {interaction.channel.mention if interaction.channel else 'a channel'}",
                        color=0x2B2D31,
                        timestamp=_dt.datetime.utcnow()
                    )
                    await channel.send(embed=embed)
        except Exception as e:
            log.error(f"Audit logging failed: {e}")


bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None, tree_cls=RestrictedCommandTree)

# Moderation + tickets/modmail only. See README.md for what each one does.
STARTUP_COGS = [
    "permissions",
    "audit",
    "moderation",
    "moderation2",
    "modextra",
    "automod",
    "wordfilter",
    "appeals",
    "security",
    "honeypot",
    "logging_cog",
    "tickets",
    "modmail",
]


@bot.event
async def on_ready():
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name=f"the server | {BOT_CREDIT}")
    )
    try:
        synced = await bot.tree.sync()
        log.info(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        log.error(f"Failed to sync commands: {e}")

    log.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    log.info(BOT_CREDIT)


async def main():
    if not TOKEN:
        raise RuntimeError(
            "No DISCORD_TOKEN found. Copy .env.example to .env and add your bot token."
        )

    await init_db()
    async with bot:
        for cog in STARTUP_COGS:
            try:
                await bot.load_extension(cog)
                log.info(f"Loaded {cog}")
            except Exception as e:
                log.error(f"Failed to load {cog}: {e}")

        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
