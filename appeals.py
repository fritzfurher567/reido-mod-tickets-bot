"""
appeals.py
Ban appeal flow: a banned user (or anyone, framed as "appeal a
moderation action") submits via /appeal, staff review with accept/deny
buttons in a review channel.
"""
import datetime

import discord
from discord import app_commands
from discord.ext import commands

import database as db


class AppealModal(discord.ui.Modal, title="Ban / Action Appeal"):
    reason = discord.ui.TextInput(label="Why should this be reconsidered?", style=discord.TextStyle.paragraph, required=True, max_length=1000)

    async def on_submit(self, interaction: discord.Interaction):
        cog: Appeals = interaction.client.get_cog("Appeals")
        await cog.submit_appeal(interaction, str(self.reason))


class AppealReviewView(discord.ui.View):
    def __init__(self, appeal_id: int):
        super().__init__(timeout=None)
        self.appeal_id = appeal_id
        self.accept.custom_id = f"appeal:accept:{appeal_id}"
        self.deny.custom_id = f"appeal:deny:{appeal_id}"

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog: Appeals = interaction.client.get_cog("Appeals")
        await cog.resolve_appeal(interaction, self.appeal_id, "accepted")

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog: Appeals = interaction.client.get_cog("Appeals")
        await cog.resolve_appeal(interaction, self.appeal_id, "denied")


class Appeals(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="appeals-channel", description="[Admin] Set where appeals get reviewed")
    @app_commands.checks.has_permissions(administrator=True)
    async def appeals_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await db.set_appeals_channel(interaction.guild_id, channel.id)
        await interaction.response.send_message(f"Appeals will be reviewed in {channel.mention}.", ephemeral=True)

    @app_commands.command(name="appeal", description="Submit an appeal for a moderation action taken against you")
    async def appeal(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AppealModal())

    async def submit_appeal(self, interaction: discord.Interaction, reason: str):
        config = await db.get_appeals_config(interaction.guild_id)
        if not config["channel_id"]:
            await interaction.response.send_message("Appeals aren't set up here yet.", ephemeral=True)
            return
        channel = interaction.guild.get_channel(config["channel_id"])
        if not channel:
            await interaction.response.send_message("Configured appeals channel no longer exists.", ephemeral=True)
            return

        appeal_id = await db.add_appeal(interaction.guild_id, interaction.user.id, reason, datetime.datetime.utcnow().isoformat())

        embed = discord.Embed(title=f"Appeal #{appeal_id}", description=reason, color=discord.Color.orange())
        embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)

        view = AppealReviewView(appeal_id)
        self.bot.add_view(view)
        msg = await channel.send(embed=embed, view=view)
        await db.set_appeal_message(appeal_id, channel.id, msg.id)

        await interaction.response.send_message("Appeal submitted. Staff will review it.", ephemeral=True)

    async def resolve_appeal(self, interaction: discord.Interaction, appeal_id: int, status: str):
        appeal = await db.get_appeal(appeal_id)
        if not appeal:
            await interaction.response.send_message("Appeal not found.", ephemeral=True)
            return

        await db.set_appeal_status(appeal_id, status, interaction.user.id)

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green() if status == "accepted" else discord.Color.red()
        embed.title = f"Appeal #{appeal_id} — {status.title()}"
        embed.set_footer(text=f"Reviewed by {interaction.user}")
        await interaction.response.edit_message(embed=embed, view=None)

        if status == "accepted":
            try:
                await interaction.guild.unban(discord.Object(id=appeal["user_id"]), reason=f"Appeal #{appeal_id} accepted")
            except discord.NotFound:
                pass  # they weren't banned, e.g. this was a timeout/warning appeal
            except discord.Forbidden:
                pass


async def setup(bot):
    await bot.add_cog(Appeals(bot))
