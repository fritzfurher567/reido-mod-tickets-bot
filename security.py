"""
security.py
Panic-button lockdown: instantly locks every text channel (denies
send_messages for @everyone) and raises the server's verification level.
/unlock reverses both. State is persisted so a bot restart mid-lockdown
doesn't lose track of what it changed.
"""
import json

import discord
from discord import app_commands
from discord.ext import commands

import database as db

VERIFICATION_LEVELS = {
    "none": discord.VerificationLevel.none,
    "low": discord.VerificationLevel.low,
    "medium": discord.VerificationLevel.medium,
    "high": discord.VerificationLevel.high,
    "highest": discord.VerificationLevel.highest,
}


class Security(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="emergency-lockdown", description="[Admin] Panic-lock the server: freezes all text channels + raises verification")
    @app_commands.checks.has_permissions(administrator=True)
    async def emergency_lockdown(self, interaction: discord.Interaction, reason: str = "Emergency lockdown"):
        state = await db.get_lockdown_state(interaction.guild_id)
        if state["is_locked"]:
            await interaction.response.send_message("Server is already locked down.", ephemeral=True)
            return

        await interaction.response.defer()
        guild = interaction.guild

        locked_ids = []
        for channel in guild.text_channels:
            overwrite = channel.overwrites_for(guild.default_role)
            if overwrite.send_messages is not False:  # only touch channels that weren't already locked
                overwrite.send_messages = False
                try:
                    await channel.set_permissions(guild.default_role, overwrite=overwrite, reason=reason)
                    locked_ids.append(channel.id)
                except discord.Forbidden:
                    pass

        previous_level = guild.verification_level.name
        try:
            await guild.edit(verification_level=discord.VerificationLevel.highest, reason=reason)
        except discord.Forbidden:
            pass

        await db.set_lockdown_state(guild.id, True, json.dumps(locked_ids), previous_level)

        embed = discord.Embed(
            title="🔒 SERVER LOCKDOWN ACTIVE",
            description=f"Reason: {reason}\nLocked {len(locked_ids)} channel(s). Verification raised to highest.",
            color=discord.Color.dark_red(),
        )
        embed.set_footer(text=f"Initiated by {interaction.user}")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="emergency-unlock", description="[Admin] Reverse an active panic lockdown")
    @app_commands.checks.has_permissions(administrator=True)
    async def unlock(self, interaction: discord.Interaction):
        state = await db.get_lockdown_state(interaction.guild_id)
        if not state["is_locked"]:
            await interaction.response.send_message("Server isn't currently locked down.", ephemeral=True)
            return

        await interaction.response.defer()
        guild = interaction.guild
        locked_ids = json.loads(state["locked_channels"] or "[]")

        for channel_id in locked_ids:
            channel = guild.get_channel(channel_id)
            if channel:
                overwrite = channel.overwrites_for(guild.default_role)
                overwrite.send_messages = None  # reset to default rather than force-True
                try:
                    await channel.set_permissions(guild.default_role, overwrite=overwrite, reason="Lockdown lifted")
                except discord.Forbidden:
                    pass

        prev_level = VERIFICATION_LEVELS.get(state["previous_verification_level"], discord.VerificationLevel.medium)
        try:
            await guild.edit(verification_level=prev_level, reason="Lockdown lifted")
        except discord.Forbidden:
            pass

        await db.set_lockdown_state(guild.id, False, "", "")

        embed = discord.Embed(
            title="🔓 Lockdown Lifted",
            description=f"Restored {len(locked_ids)} channel(s) and verification level.",
            color=discord.Color.green(),
        )
        embed.set_footer(text=f"Lifted by {interaction.user}")
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Security(bot))
