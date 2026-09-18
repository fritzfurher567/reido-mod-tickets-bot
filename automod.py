"""
cogs/automod.py
Auto-moderation:
- Banned word filter
- Invite link filter
- Excessive caps filter
- Mass mention filter
Moderators (anyone with Manage Messages) are exempt from all filters.
Violations delete the message, warn the user, and log to the mod-log channel.
"""

import datetime
import re

import discord
from discord import app_commands
from discord.ext import commands

import database as db
from config import COLOR_WARNING, COLOR_ERROR, COLOR_SUCCESS, BOT_CREDIT

INVITE_REGEX = re.compile(r"(discord\.gg|discord\.com/invite|discordapp\.com/invite)/\S+", re.IGNORECASE)


def base_embed(title: str, description: str, color: int) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.datetime.utcnow())
    embed.set_footer(text=BOT_CREDIT)
    return embed


async def log_action(guild: discord.Guild, embed: discord.Embed):
    config = await db.get_guild_config(guild.id)
    channel_id = config.get("mod_log_channel")
    if channel_id:
        channel = guild.get_channel(channel_id)
        if channel:
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                pass


def is_excessive_caps(content: str) -> bool:
    letters = [c for c in content if c.isalpha()]
    if len(letters) < 10:
        return False
    upper = sum(1 for c in letters if c.isupper())
    return (upper / len(letters)) > 0.7


class AutoMod(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if isinstance(message.author, discord.Member) and message.author.guild_permissions.manage_messages:
            return  # mods are exempt

        config = await db.get_automod_config(message.guild.id)
        violation_reason = None

        banned_words = [w.strip().lower() for w in config.get("banned_words", "").split(",") if w.strip()]
        if banned_words:
            lowered = message.content.lower()
            if any(word in lowered for word in banned_words):
                violation_reason = "used a banned word"

        if violation_reason is None and config.get("anti_invite") and INVITE_REGEX.search(message.content):
            violation_reason = "posted a Discord invite link"

        if violation_reason is None and config.get("caps_filter") and is_excessive_caps(message.content):
            violation_reason = "excessive caps"

        mention_limit = config.get("mention_limit") or 0
        if violation_reason is None and mention_limit > 0 and len(message.mentions) > mention_limit:
            violation_reason = "mass mentions"

        if violation_reason:
            try:
                await message.delete()
            except discord.Forbidden:
                pass

            try:
                await message.channel.send(
                    embed=base_embed("Message Removed", f"{message.author.mention}, your message was removed: **{violation_reason}**.", COLOR_WARNING),
                    delete_after=6
                )
            except discord.Forbidden:
                pass

            timestamp = datetime.datetime.utcnow().isoformat()
            await db.add_warning(message.guild.id, message.author.id, self.bot.user.id, f"Auto-mod: {violation_reason}", timestamp)

            await log_action(message.guild, base_embed(
                "Auto-Mod Action",
                f"**User:** {message.author.mention}\n**Reason:** {violation_reason}\n**Channel:** {message.channel.mention}",
                COLOR_ERROR
            ))

    # ---------- CONFIG COMMANDS ----------
    @app_commands.command(name="automod-bannedwords", description="Add or remove banned words (comma-separated).")
    @app_commands.describe(action="add, remove, or list", words="Comma-separated words (not needed for list)")
    @app_commands.choices(action=[
        app_commands.Choice(name="add", value="add"),
        app_commands.Choice(name="remove", value="remove"),
        app_commands.Choice(name="list", value="list"),
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def automod_bannedwords(self, interaction: discord.Interaction, action: app_commands.Choice[str], words: str = ""):
        config = await db.get_automod_config(interaction.guild.id)
        current = set(w.strip().lower() for w in config.get("banned_words", "").split(",") if w.strip())
        new_words = set(w.strip().lower() for w in words.split(",") if w.strip())

        if action.value == "add":
            current |= new_words
        elif action.value == "remove":
            current -= new_words
        # "list" falls through without modifying

        if action.value != "list":
            await db.update_automod_config(interaction.guild.id, banned_words=",".join(sorted(current)))

        display = ", ".join(sorted(current)) if current else "*(none set)*"
        await interaction.response.send_message(embed=base_embed("Banned Words", display, COLOR_SUCCESS), ephemeral=True)

    @app_commands.command(name="automod-toggle", description="Turn an auto-mod filter on or off.")
    @app_commands.describe(feature="Which filter to toggle", enabled="On or off")
    @app_commands.choices(feature=[
        app_commands.Choice(name="Invite link filter", value="anti_invite"),
        app_commands.Choice(name="Excessive caps filter", value="caps_filter"),
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def automod_toggle(self, interaction: discord.Interaction, feature: app_commands.Choice[str], enabled: bool):
        await db.update_automod_config(interaction.guild.id, **{feature.value: int(enabled)})
        state = "enabled" if enabled else "disabled"
        await interaction.response.send_message(embed=base_embed("Auto-Mod Updated", f"**{feature.name}** is now **{state}**.", COLOR_SUCCESS))

    @app_commands.command(name="automod-mentionlimit", description="Set the max mentions allowed per message (0 to disable).")
    @app_commands.describe(limit="Maximum number of mentions allowed in a single message")
    @app_commands.checks.has_permissions(administrator=True)
    async def automod_mentionlimit(self, interaction: discord.Interaction, limit: app_commands.Range[int, 0, 50]):
        await db.update_automod_config(interaction.guild.id, mention_limit=limit)
        desc = "Mention spam filter disabled." if limit == 0 else f"Messages with more than **{limit}** mentions will be removed."
        await interaction.response.send_message(embed=base_embed("Mention Limit Updated", desc, COLOR_SUCCESS))


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoMod(bot))
