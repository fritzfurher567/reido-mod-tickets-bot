"""
moderation2.py
A few moderation utilities not in Moderation.py: mute-role setup/apply,
unban by raw ID, active ban list, and purging messages from one specific
user within a channel.
"""
import discord
from discord import app_commands
from discord.ext import commands

import database as db


class Moderation2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="muterole-setup", description="[Admin] Create/configure a Muted role that blocks sending in all channels")
    @app_commands.checks.has_permissions(administrator=True)
    async def muterole_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        role = discord.utils.get(interaction.guild.roles, name="Muted")
        if not role:
            role = await interaction.guild.create_role(name="Muted", reason="Mute role setup")
        for channel in interaction.guild.channels:
            try:
                await channel.set_permissions(role, send_messages=False, add_reactions=False, speak=False)
            except discord.Forbidden:
                pass
        await interaction.followup.send(f"Mute role ready: {role.mention}", ephemeral=True)

    @app_commands.command(name="muterole-apply", description="[Mod] Apply the Muted role to a member")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def muterole_apply(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason given"):
        role = discord.utils.get(interaction.guild.roles, name="Muted")
        if not role:
            await interaction.response.send_message("Run /muterole-setup first.", ephemeral=True)
            return
        await member.add_roles(role, reason=reason)
        await interaction.response.send_message(f"Muted {member.mention}: {reason}")

    @app_commands.command(name="unbanid", description="[Mod] Unban a user by their raw ID")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unbanid(self, interaction: discord.Interaction, user_id: str):
        try:
            await interaction.guild.unban(discord.Object(id=int(user_id)))
            await interaction.response.send_message(f"Unbanned user ID `{user_id}`.")
        except (ValueError, discord.NotFound):
            await interaction.response.send_message("Invalid ID or that user isn't banned.", ephemeral=True)

    @app_commands.command(name="banlist", description="[Mod] View currently banned users")
    @app_commands.checks.has_permissions(ban_members=True)
    async def banlist(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        bans = [entry async for entry in interaction.guild.bans(limit=25)]
        if not bans:
            await interaction.followup.send("No bans on record.", ephemeral=True)
            return
        lines = [f"**{b.user}** — {b.reason or 'No reason'}" for b in bans]
        embed = discord.Embed(title="🔨 Ban List", description="\n".join(lines), color=discord.Color.dark_red())
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="purgeuser", description="[Mod] Delete a specific member's recent messages in this channel")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purgeuser(self, interaction: discord.Interaction, member: discord.Member, amount: app_commands.Range[int, 1, 200] = 50):
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount, check=lambda m: m.author.id == member.id)
        await interaction.followup.send(f"Deleted {len(deleted)} message(s) from {member.mention}.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Moderation2(bot))
