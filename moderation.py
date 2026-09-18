"""
cogs/moderation.py
Full moderation toolkit: kick, ban, unban, timeout, warnings, purge,
channel lock/unlock, slowmode, nickname/role management, and server lockdown.
All actions are logged to the guild's configured mod-log channel, if set.
"""

import datetime

import discord
from discord import app_commands
from discord.ext import commands

import database as db
from config import COLOR_SUCCESS, COLOR_ERROR, COLOR_WARNING, BOT_CREDIT


def mod_embed(title: str, description: str, color: int) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color,
                           timestamp=datetime.datetime.utcnow())
    embed.set_footer(text=BOT_CREDIT)
    return embed


async def log_action(guild: discord.Guild, embed: discord.Embed):
    """Send an embed to the guild's configured mod-log channel, if one is set."""
    config = await db.get_guild_config(guild.id)
    channel_id = config.get("mod_log_channel")
    if channel_id:
        channel = guild.get_channel(channel_id)
        if channel:
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                pass


def parse_duration(duration: str) -> datetime.timedelta | None:
    """Parse a short duration string like '10m', '2h', '1d' into a timedelta."""
    units = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}
    try:
        unit = duration[-1].lower()
        amount = int(duration[:-1])
        if unit not in units:
            return None
        return datetime.timedelta(**{units[unit]: amount})
    except (ValueError, IndexError):
        return None


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------- KICK ----------
    @app_commands.command(name="kick", description="Kick a member from the server.")
    @app_commands.describe(member="The member to kick", reason="Reason for the kick")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message(
                embed=mod_embed("Error", "You can't kick someone with an equal or higher role.", COLOR_ERROR),
                ephemeral=True
            )
        try:
            await member.send(embed=mod_embed(
                f"You were kicked from {interaction.guild.name}", f"**Reason:** {reason}", COLOR_ERROR
            ))
        except discord.Forbidden:
            pass

        await member.kick(reason=f"{reason} (by {interaction.user})")
        embed = mod_embed("Member Kicked", f"**{member}** was kicked by {interaction.user.mention}\n**Reason:** {reason}", COLOR_ERROR)
        await interaction.response.send_message(embed=embed)
        await log_action(interaction.guild, embed)

    # ---------- BAN ----------
    @app_commands.command(name="ban", description="Ban a member from the server.")
    @app_commands.describe(member="The member to ban", reason="Reason for the ban", delete_days="Days of messages to delete (0-7)")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided", delete_days: app_commands.Range[int, 0, 7] = 0):
        if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message(
                embed=mod_embed("Error", "You can't ban someone with an equal or higher role.", COLOR_ERROR),
                ephemeral=True
            )
        try:
            await member.send(embed=mod_embed(
                f"You were banned from {interaction.guild.name}", f"**Reason:** {reason}", COLOR_ERROR
            ))
        except discord.Forbidden:
            pass

        await member.ban(reason=f"{reason} (by {interaction.user})", delete_message_days=delete_days)
        embed = mod_embed("Member Banned", f"**{member}** was banned by {interaction.user.mention}\n**Reason:** {reason}", COLOR_ERROR)
        await interaction.response.send_message(embed=embed)
        await log_action(interaction.guild, embed)

    # ---------- UNBAN ----------
    @app_commands.command(name="unban", description="Unban a user by their user ID.")
    @app_commands.describe(user_id="The user ID to unban", reason="Reason for the unban")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: str = "No reason provided"):
        try:
            user = await self.bot.fetch_user(int(user_id))
            await interaction.guild.unban(user, reason=reason)
        except (ValueError, discord.NotFound):
            return await interaction.response.send_message(
                embed=mod_embed("Error", "Couldn't find a ban for that user ID.", COLOR_ERROR), ephemeral=True
            )

        embed = mod_embed("Member Unbanned", f"**{user}** was unbanned by {interaction.user.mention}\n**Reason:** {reason}", COLOR_SUCCESS)
        await interaction.response.send_message(embed=embed)
        await log_action(interaction.guild, embed)

    # ---------- TIMEOUT ----------
    @app_commands.command(name="timeout", description="Timeout (mute) a member for a set duration.")
    @app_commands.describe(member="The member to timeout", duration="e.g. 10m, 2h, 1d (max 28d)", reason="Reason for the timeout")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, duration: str, reason: str = "No reason provided"):
        delta = parse_duration(duration)
        if delta is None or delta.total_seconds() <= 0:
            return await interaction.response.send_message(
                embed=mod_embed("Error", "Invalid duration. Use formats like `10m`, `2h`, `1d`.", COLOR_ERROR),
                ephemeral=True
            )
        if delta > datetime.timedelta(days=28):
            delta = datetime.timedelta(days=28)

        await member.timeout(delta, reason=f"{reason} (by {interaction.user})")
        embed = mod_embed("Member Timed Out", f"**{member}** was timed out by {interaction.user.mention} for `{duration}`\n**Reason:** {reason}", COLOR_WARNING)
        await interaction.response.send_message(embed=embed)
        await log_action(interaction.guild, embed)

    # ---------- REMOVE TIMEOUT ----------
    @app_commands.command(name="untimeout", description="Remove a timeout from a member.")
    @app_commands.describe(member="The member to remove timeout from")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def untimeout(self, interaction: discord.Interaction, member: discord.Member):
        await member.timeout(None, reason=f"Timeout removed by {interaction.user}")
        embed = mod_embed("Timeout Removed", f"**{member}**'s timeout was removed by {interaction.user.mention}", COLOR_SUCCESS)
        await interaction.response.send_message(embed=embed)
        await log_action(interaction.guild, embed)

    # ---------- WARN ----------
    @app_commands.command(name="warn", description="Warn a member. Warnings are saved and can be reviewed later.")
    @app_commands.describe(member="The member to warn", reason="Reason for the warning")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        timestamp = datetime.datetime.utcnow().isoformat()
        warning_id = await db.add_warning(interaction.guild.id, member.id, interaction.user.id, reason, timestamp)

        try:
            await member.send(embed=mod_embed(
                f"You were warned in {interaction.guild.name}", f"**Reason:** {reason}", COLOR_WARNING
            ))
        except discord.Forbidden:
            pass

        embed = mod_embed("Member Warned", f"**{member}** was warned by {interaction.user.mention}\n**Reason:** {reason}\n**Warning ID:** {warning_id}", COLOR_WARNING)
        await interaction.response.send_message(embed=embed)
        await log_action(interaction.guild, embed)

    # ---------- WARNINGS LIST ----------
    @app_commands.command(name="warnings", description="View all warnings for a member.")
    @app_commands.describe(member="The member to check")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
        warns = await db.get_warnings(interaction.guild.id, member.id)
        if not warns:
            return await interaction.response.send_message(
                embed=mod_embed("Warnings", f"{member.mention} has no warnings.", COLOR_SUCCESS)
            )

        description = "\n\n".join(
            f"**#{w['id']}** — {w['reason']}\n<t:{int(datetime.datetime.fromisoformat(w['timestamp']).timestamp())}:R> by <@{w['moderator_id']}>"
            for w in warns
        )
        embed = mod_embed(f"Warnings for {member}", description, COLOR_WARNING)
        await interaction.response.send_message(embed=embed)

    # ---------- CLEAR WARNINGS ----------
    @app_commands.command(name="clearwarnings", description="Clear all warnings for a member.")
    @app_commands.describe(member="The member whose warnings to clear")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def clearwarnings(self, interaction: discord.Interaction, member: discord.Member):
        await db.clear_warnings(interaction.guild.id, member.id)
        embed = mod_embed("Warnings Cleared", f"All warnings for **{member}** were cleared by {interaction.user.mention}", COLOR_SUCCESS)
        await interaction.response.send_message(embed=embed)
        await log_action(interaction.guild, embed)

    # ---------- REMOVE SINGLE WARNING ----------
    @app_commands.command(name="removewarning", description="Remove a single warning by its ID.")
    @app_commands.describe(warning_id="The warning ID to remove (shown in /warnings)")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def removewarning(self, interaction: discord.Interaction, warning_id: int):
        success = await db.remove_warning(interaction.guild.id, warning_id)
        if success:
            await interaction.response.send_message(
                embed=mod_embed("Warning Removed", f"Warning `#{warning_id}` was removed.", COLOR_SUCCESS)
            )
        else:
            await interaction.response.send_message(
                embed=mod_embed("Error", f"No warning found with ID `#{warning_id}`.", COLOR_ERROR), ephemeral=True
            )

    # ---------- PURGE ----------
    @app_commands.command(name="purge", description="Delete a number of recent messages in this channel.")
    @app_commands.describe(amount="Number of messages to delete (1-100)", member="Only delete messages from this member")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100], member: discord.Member = None):
        await interaction.response.defer(ephemeral=True)

        def check(msg):
            return member is None or msg.author.id == member.id

        deleted = await interaction.channel.purge(limit=amount, check=check)
        await interaction.followup.send(
            embed=mod_embed("Messages Purged", f"Deleted **{len(deleted)}** messages.", COLOR_SUCCESS),
            ephemeral=True
        )

    # ---------- LOCK ----------
    @app_commands.command(name="lock", description="Lock the current channel (prevent @everyone from sending messages).")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def lock(self, interaction: discord.Interaction):
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.response.send_message(embed=mod_embed("Channel Locked", f"{interaction.channel.mention} has been locked.", COLOR_WARNING))

    # ---------- UNLOCK ----------
    @app_commands.command(name="unlock", description="Unlock the current channel.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def unlock(self, interaction: discord.Interaction):
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = None
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.response.send_message(embed=mod_embed("Channel Unlocked", f"{interaction.channel.mention} has been unlocked.", COLOR_SUCCESS))

    # ---------- LOCKDOWN (all channels) ----------
    @app_commands.command(name="lockdown", description="Lock every text channel in the server.")
    @app_commands.checks.has_permissions(administrator=True)
    async def lockdown(self, interaction: discord.Interaction):
        await interaction.response.defer()
        count = 0
        for channel in interaction.guild.text_channels:
            overwrite = channel.overwrites_for(interaction.guild.default_role)
            overwrite.send_messages = False
            try:
                await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
                count += 1
            except discord.Forbidden:
                continue
        await interaction.followup.send(embed=mod_embed("Server Lockdown", f"Locked **{count}** channels.", COLOR_ERROR))

    # ---------- SLOWMODE ----------
    @app_commands.command(name="slowmode", description="Set slowmode delay for the current channel.")
    @app_commands.describe(seconds="Delay in seconds (0 to disable, max 21600)")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def slowmode(self, interaction: discord.Interaction, seconds: app_commands.Range[int, 0, 21600]):
        await interaction.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            desc = f"Slowmode disabled in {interaction.channel.mention}."
        else:
            desc = f"Slowmode set to **{seconds}s** in {interaction.channel.mention}."
        await interaction.response.send_message(embed=mod_embed("Slowmode Updated", desc, COLOR_SUCCESS))

    # ---------- NICKNAME ----------
    @app_commands.command(name="nickname", description="Change a member's nickname.")
    @app_commands.describe(member="The member to rename", nickname="New nickname (leave blank to reset)")
    @app_commands.checks.has_permissions(manage_nicknames=True)
    async def nickname(self, interaction: discord.Interaction, member: discord.Member, nickname: str = None):
        await member.edit(nick=nickname)
        desc = f"**{member}**'s nickname was reset." if nickname is None else f"**{member}**'s nickname changed to **{nickname}**."
        await interaction.response.send_message(embed=mod_embed("Nickname Updated", desc, COLOR_SUCCESS))

    # ---------- ROLE ADD ----------
    @app_commands.command(name="addrole", description="Add a role to a member.")
    @app_commands.describe(member="The member", role="The role to add")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def addrole(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        await member.add_roles(role, reason=f"Added by {interaction.user}")
        await interaction.response.send_message(embed=mod_embed("Role Added", f"Gave {role.mention} to **{member}**.", COLOR_SUCCESS))

    # ---------- ROLE REMOVE ----------
    @app_commands.command(name="removerole", description="Remove a role from a member.")
    @app_commands.describe(member="The member", role="The role to remove")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def removerole(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        await member.remove_roles(role, reason=f"Removed by {interaction.user}")
        await interaction.response.send_message(embed=mod_embed("Role Removed", f"Removed {role.mention} from **{member}**.", COLOR_SUCCESS))

    # ---------- SET MOD LOG CHANNEL ----------
    @app_commands.command(name="setmodlog", description="Set the channel where moderation actions are logged.")
    @app_commands.describe(channel="The channel to send mod logs to")
    @app_commands.checks.has_permissions(administrator=True)
    async def setmodlog(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await db.update_guild_config(interaction.guild.id, mod_log_channel=channel.id)
        await interaction.response.send_message(embed=mod_embed("Mod Log Set", f"Moderation actions will now be logged to {channel.mention}.", COLOR_SUCCESS))

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                embed=mod_embed("Missing Permissions", "You don't have permission to use this command.", COLOR_ERROR),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=mod_embed("Error", f"Something went wrong: `{error}`", COLOR_ERROR), ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
