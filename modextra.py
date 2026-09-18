"""
modextra.py
Extra moderation utilities not covered by Moderation.py: forced nicknames,
softban (ban+unban to purge recent messages without a permanent ban),
channel nuke (clone+delete to instantly wipe a channel's history), and
a personal /remindme.
"""
import datetime
import asyncio

import discord
from discord import app_commands
from discord.ext import commands


class ModExtra(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="forcenick", description="[Mod] Force-set a member's nickname")
    @app_commands.checks.has_permissions(manage_nicknames=True)
    async def forcenick(self, interaction: discord.Interaction, member: discord.Member, nickname: str):
        try:
            await member.edit(nick=nickname, reason=f"Forced by {interaction.user}")
        except discord.Forbidden:
            await interaction.response.send_message("I can't edit that member's nickname (role hierarchy).", ephemeral=True)
            return
        await interaction.response.send_message(f"Set {member.mention}'s nickname to **{nickname}**.")

    @app_commands.command(name="resetnick", description="[Mod] Reset a member's nickname to their username")
    @app_commands.checks.has_permissions(manage_nicknames=True)
    async def resetnick(self, interaction: discord.Interaction, member: discord.Member):
        try:
            await member.edit(nick=None, reason=f"Reset by {interaction.user}")
        except discord.Forbidden:
            await interaction.response.send_message("I can't edit that member's nickname (role hierarchy).", ephemeral=True)
            return
        await interaction.response.send_message(f"Reset {member.mention}'s nickname.")

    @app_commands.command(name="softban", description="[Mod] Ban then immediately unban — purges recent messages without a permanent ban")
    @app_commands.checks.has_permissions(ban_members=True)
    async def softban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason given", delete_days: int = 1):
        await interaction.response.defer()
        try:
            await member.ban(reason=f"Softban by {interaction.user}: {reason}", delete_message_days=delete_days)
            await interaction.guild.unban(member, reason="Softban — auto unban")
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to do that.", ephemeral=True)
            return
        embed = discord.Embed(title="Member Softbanned", color=discord.Color.orange())
        embed.add_field(name="Member", value=str(member))
        embed.add_field(name="Moderator", value=interaction.user.mention)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"Purged {delete_days} day(s) of messages, member NOT permanently banned")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="nuke", description="[Admin] Instantly wipe this channel's message history (clone + delete)")
    @app_commands.checks.has_permissions(administrator=True)
    async def nuke(self, interaction: discord.Interaction):
        channel = interaction.channel
        await interaction.response.send_message("Nuking this channel in 3 seconds...")
        await asyncio.sleep(3)
        new_channel = await channel.clone(reason=f"Nuked by {interaction.user}")
        await new_channel.edit(position=channel.position)
        await channel.delete(reason=f"Nuked by {interaction.user}")
        await new_channel.send(f"💥 Channel nuked by {interaction.user.mention}.")

    @app_commands.command(name="remindme", description="Set a personal reminder")
    async def remindme(self, interaction: discord.Interaction, minutes: int, reminder: str):
        if minutes <= 0 or minutes > 10080:  # cap at 1 week
            await interaction.response.send_message("Minutes must be between 1 and 10080 (1 week).", ephemeral=True)
            return
        await interaction.response.send_message(f"Okay, I'll remind you in {minutes} minute(s): \"{reminder}\"", ephemeral=True)
        await asyncio.sleep(minutes * 60)
        try:
            await interaction.user.send(f"⏰ Reminder: {reminder}")
        except discord.Forbidden:
            channel = interaction.channel
            if channel:
                await channel.send(f"{interaction.user.mention} ⏰ Reminder: {reminder}")


async def setup(bot):
    await bot.add_cog(ModExtra(bot))
