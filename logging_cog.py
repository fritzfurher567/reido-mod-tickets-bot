"""
cogs/logging.py
General server activity logging:
Message edits/deletes, and channel create/delete events, sent to a
configurable server-log channel. Separate from the moderation-action log.
"""

import datetime

import discord
from discord import app_commands
from discord.ext import commands

import database as db
from config import COLOR_INFO, COLOR_WARNING, COLOR_ERROR, COLOR_SUCCESS, BOT_CREDIT


def base_embed(title: str, description: str, color: int) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.datetime.utcnow())
    embed.set_footer(text=BOT_CREDIT)
    return embed


class ServerLogging(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _log_channel(self, guild: discord.Guild):
        config = await db.get_guild_config(guild.id)
        channel_id = config.get("server_log_channel")
        return guild.get_channel(channel_id) if channel_id else None

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        channel = await self._log_channel(message.guild)
        if not channel:
            return
        content = message.content or "*(no text content — likely an embed or attachment)*"
        embed = base_embed(
            "🗑️ Message Deleted",
            f"**Author:** {message.author.mention}\n**Channel:** {message.channel.mention}\n\n{content[:1000]}",
            COLOR_ERROR
        )
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild or before.content == after.content:
            return
        channel = await self._log_channel(before.guild)
        if not channel:
            return
        embed = base_embed(
            "✏️ Message Edited",
            f"**Author:** {before.author.mention}\n**Channel:** {before.channel.mention}\n\n"
            f"**Before:** {before.content[:500] or '*(empty)*'}\n**After:** {after.content[:500] or '*(empty)*'}",
            COLOR_WARNING
        )
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        log_channel = await self._log_channel(channel.guild)
        if log_channel:
            try:
                await log_channel.send(embed=base_embed("📁 Channel Created", f"**{channel.name}** ({channel.type})", COLOR_SUCCESS))
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        log_channel = await self._log_channel(channel.guild)
        if log_channel:
            try:
                await log_channel.send(embed=base_embed("📁 Channel Deleted", f"**{channel.name}** ({channel.type})", COLOR_ERROR))
            except discord.Forbidden:
                pass

    @app_commands.command(name="setserverlog", description="Set the channel for general server activity logs (edits, deletes, etc.)")
    @app_commands.describe(channel="Channel to send server logs to")
    @app_commands.checks.has_permissions(administrator=True)
    async def setserverlog(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await db.update_guild_config(interaction.guild.id, server_log_channel=channel.id)
        await interaction.response.send_message(embed=base_embed("Server Log Set", f"Server activity will be logged to {channel.mention}.", COLOR_SUCCESS))


async def setup(bot: commands.Bot):
    await bot.add_cog(ServerLogging(bot))
