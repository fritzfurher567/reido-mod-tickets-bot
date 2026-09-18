"""
cogs/audit.py
Audit log commands ("every command is audited"). The actual
logging happens globally in main.py's RestrictedCommandTree, since that's
where every single command already passes through for permission checks —
this cog just exposes commands to configure and view that log.
"""

import datetime

import discord
from discord import app_commands
from discord.ext import commands

import database as db
from config import COLOR_SUCCESS, COLOR_INFO, BOT_CREDIT


def base_embed(title: str, description: str, color: int = COLOR_INFO) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.datetime.utcnow())
    embed.set_footer(text=BOT_CREDIT)
    return embed


class Audit(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="auditlog-channel", description="Set the channel where every command usage gets logged.")
    @app_commands.describe(channel="Channel for the live audit feed (leave unset to disable)")
    @app_commands.checks.has_permissions(administrator=True)
    async def auditlog_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await db.update_guild_config(interaction.guild.id, audit_log_channel=channel.id)
        await interaction.response.send_message(embed=base_embed("Audit Log Channel Set", f"Every command used in this server will now be logged to {channel.mention}.", COLOR_SUCCESS))

    @app_commands.command(name="auditlog", description="Show the most recent command usage in this server.")
    @app_commands.checks.has_permissions(administrator=True)
    async def auditlog(self, interaction: discord.Interaction):
        entries = await db.get_recent_audit_entries(interaction.guild.id, limit=15)
        if not entries:
            return await interaction.response.send_message(embed=base_embed("Audit Log", "No commands logged yet.", COLOR_INFO))

        lines = [f"<@{e['user_id']}> used `/{e['command_name']}` — <t:{int(datetime.datetime.fromisoformat(e['timestamp']).timestamp())}:R>" for e in entries]
        await interaction.response.send_message(embed=base_embed("📜 Recent Command Usage", "\n".join(lines), COLOR_INFO), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Audit(bot))
