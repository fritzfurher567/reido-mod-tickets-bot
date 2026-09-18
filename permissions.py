"""
cogs/permissions.py
Role-based command permissions:
- The server owner and anyone with Administrator can always use every command.
- Admins can restrict any other command to specific roles with /permission-restrict.
- A command with no restrictions configured stays open to everyone (subject to
  whatever normal Discord permission check it already has, e.g. Manage Messages).
- Enforcement happens globally via the RestrictedCommandTree in main.py — this
  cog only manages the restriction list itself.

Also includes a dedicated /role command group for adding/removing roles,
separate from the moderation cog's /addrole and /removerole.
"""

import discord
from discord import app_commands
from discord.ext import commands

import database as db
from config import COLOR_SUCCESS, COLOR_ERROR, COLOR_INFO, BOT_CREDIT


def base_embed(title: str, description: str, color: int = COLOR_INFO) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text=BOT_CREDIT)
    return embed


class Permissions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------- RESTRICTION MANAGEMENT ----------
    # Only the owner/Administrators can manage restrictions — enforced by the
    # global RestrictedCommandTree check plus this explicit permission check
    # as a second layer, since misconfiguring this system would be serious.

    @app_commands.command(name="permission-restrict", description="Restrict a command to a specific role. Owner/Admins always retain access.")
    @app_commands.describe(command="The exact command name (e.g. 'ban' or 'ticket-close')", role="Role allowed to use it")
    @app_commands.checks.has_permissions(administrator=True)
    async def permission_restrict(self, interaction: discord.Interaction, command: str, role: discord.Role):
        command = command.lstrip("/").strip().lower()
        if not self.bot.tree.get_command(command.split(" ")[0]):
            return await interaction.response.send_message(
                embed=base_embed("Unknown Command", f"`{command}` doesn't match any registered command.", COLOR_ERROR),
                ephemeral=True
            )
        await db.add_command_restriction(interaction.guild.id, command, role.id)
        await interaction.response.send_message(
            embed=base_embed("Restriction Added", f"Only {role.mention} (plus the owner/Admins) can now use `/{command}`.", COLOR_SUCCESS)
        )

    @app_commands.command(name="permission-unrestrict", description="Remove a role from a command's allowed list.")
    @app_commands.describe(command="The command name", role="Role to remove from the allowed list")
    @app_commands.checks.has_permissions(administrator=True)
    async def permission_unrestrict(self, interaction: discord.Interaction, command: str, role: discord.Role):
        command = command.lstrip("/").strip().lower()
        success = await db.remove_command_restriction(interaction.guild.id, command, role.id)
        if success:
            await interaction.response.send_message(
                embed=base_embed("Restriction Removed", f"{role.mention} was removed from `/{command}`'s allowed list.", COLOR_SUCCESS)
            )
        else:
            await interaction.response.send_message(
                embed=base_embed("Not Found", f"{role.mention} wasn't on the allowed list for `/{command}`.", COLOR_ERROR), ephemeral=True
            )

    @app_commands.command(name="permission-clear", description="Remove ALL role restrictions from a command (opens it back up).")
    @app_commands.describe(command="The command name")
    @app_commands.checks.has_permissions(administrator=True)
    async def permission_clear(self, interaction: discord.Interaction, command: str):
        command = command.lstrip("/").strip().lower()
        await db.clear_command_restrictions(interaction.guild.id, command)
        await interaction.response.send_message(
            embed=base_embed("Restrictions Cleared", f"`/{command}` is now open to everyone (subject to its normal permission checks).", COLOR_SUCCESS)
        )

    @app_commands.command(name="permission-list", description="Show role restrictions for one command, or all restricted commands.")
    @app_commands.describe(command="Optional — leave blank to list every restricted command")
    async def permission_list(self, interaction: discord.Interaction, command: str = None):
        if command:
            command = command.lstrip("/").strip().lower()
            role_ids = await db.get_command_restrictions(interaction.guild.id, command)
            if not role_ids:
                return await interaction.response.send_message(embed=base_embed("No Restrictions", f"`/{command}` has no role restrictions — anyone can use it.", COLOR_INFO))
            mentions = ", ".join(f"<@&{rid}>" for rid in role_ids)
            return await interaction.response.send_message(embed=base_embed(f"Restrictions for /{command}", mentions, COLOR_INFO))

        all_restrictions = await db.get_all_command_restrictions(interaction.guild.id)
        if not all_restrictions:
            return await interaction.response.send_message(embed=base_embed("No Restrictions", "No commands are currently restricted.", COLOR_INFO))

        grouped = {}
        for entry in all_restrictions:
            grouped.setdefault(entry["command_name"], []).append(entry["role_id"])

        lines = [f"**/{cmd}** — " + ", ".join(f"<@&{rid}>" for rid in roles) for cmd, roles in grouped.items()]
        await interaction.response.send_message(embed=base_embed("Restricted Commands", "\n".join(lines), COLOR_INFO))

    # ---------- ROLE ADD/REMOVE GROUP ----------

    role_group = app_commands.Group(name="role", description="Add or remove a role from a member.")

    @role_group.command(name="add", description="Give a member a role.")
    @app_commands.describe(member="The member to give the role to", role="The role to add")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def role_add(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        if role >= interaction.guild.me.top_role:
            return await interaction.response.send_message(
                embed=base_embed("Can't Assign That Role", "That role is higher than or equal to my own — move my role above it in Server Settings.", COLOR_ERROR),
                ephemeral=True
            )
        if role in member.roles:
            return await interaction.response.send_message(embed=base_embed("Already Has Role", f"{member.mention} already has {role.mention}.", COLOR_INFO), ephemeral=True)

        await member.add_roles(role, reason=f"Added by {interaction.user}")
        await interaction.response.send_message(embed=base_embed("Role Added", f"Gave {role.mention} to {member.mention}.", COLOR_SUCCESS))

    @role_group.command(name="remove", description="Remove a role from a member.")
    @app_commands.describe(member="The member to remove the role from", role="The role to remove")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def role_remove(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        if role not in member.roles:
            return await interaction.response.send_message(embed=base_embed("Doesn't Have Role", f"{member.mention} doesn't have {role.mention}.", COLOR_INFO), ephemeral=True)

        await member.remove_roles(role, reason=f"Removed by {interaction.user}")
        await interaction.response.send_message(embed=base_embed("Role Removed", f"Removed {role.mention} from {member.mention}.", COLOR_SUCCESS))

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                embed=base_embed("Missing Permissions", "You don't have permission to use this command.", COLOR_ERROR), ephemeral=True
            )
        else:
            await interaction.response.send_message(embed=base_embed("Error", f"Something went wrong: `{error}`", COLOR_ERROR), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Permissions(bot))
