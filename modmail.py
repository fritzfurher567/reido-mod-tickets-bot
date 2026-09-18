"""
modmail.py
Full ModMail system:
- A member DMs the bot -> bot creates a private channel in a configured
  category, staff see and reply there.
- Staff replies in that channel get relayed back to the member as a DM.
- Member's further DMs get relayed into the same open thread.
- /modmail-close ends the thread (with an optional reason) and DMs the
  member that it's closed, then logs a transcript to a log channel.
- /modmail-setup configures the category + log channel.
- Handles: only one open thread per member per guild; bot DMs vs guild
  messages disambiguated by checking all open threads for that user
  across guilds the bot shares with them.
"""
import datetime

import discord
from discord import app_commands
from discord.ext import commands

import database as db


class ModmailCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Thread", style=discord.ButtonStyle.red, custom_id="modmail:close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog: ModMail = interaction.client.get_cog("ModMail")
        await cog.close_thread(interaction.channel, interaction.user, "Closed via button")
        await interaction.response.send_message("Thread closed.", ephemeral=True)


class ModMail(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.add_view(ModmailCloseView())

    # ---------------- Setup ----------------

    @app_commands.command(name="modmail-setup", description="[Admin] Configure ModMail category and log channel")
    @app_commands.checks.has_permissions(administrator=True)
    async def modmail_setup(self, interaction: discord.Interaction, category: discord.CategoryChannel, log_channel: discord.TextChannel):
        await db.set_modmail_config(interaction.guild_id, category.id, log_channel.id)
        await interaction.response.send_message(
            f"ModMail configured. New threads open under **{category.name}**, transcripts log to {log_channel.mention}.\n"
            f"Members start a thread by DMing the bot directly.",
            ephemeral=True,
        )

    # ---------------- Staff-side commands (run inside a modmail thread channel) ----------------

    @app_commands.command(name="modmail-close", description="[Mod] Close the modmail thread in this channel")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def modmail_close(self, interaction: discord.Interaction, reason: str = "No reason given"):
        thread = await db.get_modmail_thread_by_channel(interaction.channel_id)
        if not thread or thread["status"] != "open":
            await interaction.response.send_message("This isn't an open modmail thread channel.", ephemeral=True)
            return
        await interaction.response.send_message(f"Closing thread: {reason}")
        await self.close_thread(interaction.channel, interaction.user, reason)

    @app_commands.command(name="modmail-reply", description="[Mod] Reply to the member in this modmail thread")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def modmail_reply(self, interaction: discord.Interaction, message: str):
        thread = await db.get_modmail_thread_by_channel(interaction.channel_id)
        if not thread or thread["status"] != "open":
            await interaction.response.send_message("This isn't an open modmail thread channel.", ephemeral=True)
            return
        member = self.bot.get_user(thread["user_id"])
        if not member:
            await interaction.response.send_message("Couldn't find that user (they may share no other mutual server with the bot).", ephemeral=True)
            return
        try:
            embed = discord.Embed(description=message, color=discord.Color.blurple())
            embed.set_author(name="Staff", icon_url=interaction.guild.icon.url if interaction.guild.icon else discord.Embed.Empty)
            await member.send(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message("Couldn't DM that user — they may have DMs closed.", ephemeral=True)
            return
        await interaction.response.send_message(f"**Staff ({interaction.user.display_name}):** {message}")

    # ---------------- DM intake / relay ----------------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Only act on DMs here — guild-channel plain messages in a thread
        # channel are handled separately below so replies don't require
        # the /modmail-reply command every time.
        if isinstance(message.channel, discord.DMChannel):
            await self._handle_dm(message)
        elif message.guild:
            await self._handle_thread_message(message)

    async def _handle_dm(self, message: discord.Message):
        existing_threads = await db.find_modmail_thread_for_user_any_guild(message.author.id)

        if existing_threads:
            # relay into the first open thread found
            thread = existing_threads[0]
            guild = self.bot.get_guild(thread["guild_id"])
            channel = guild.get_channel(thread["channel_id"]) if guild else None
            if channel:
                embed = discord.Embed(description=message.content, color=discord.Color.green())
                embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
                if message.attachments:
                    embed.set_image(url=message.attachments[0].url)
                await channel.send(embed=embed)
                await message.add_reaction("✅")
            return

        # No open thread anywhere — figure out which mutual guild has modmail configured
        mutual_guilds = [g for g in self.bot.guilds if g.get_member(message.author.id)]
        target_guild = None
        config = None
        for g in mutual_guilds:
            c = await db.get_modmail_config(g.id)
            if c["category_id"]:
                target_guild = g
                config = c
                break

        if not target_guild:
            await message.channel.send("This server hasn't set up ModMail yet — sorry, I can't open a thread.")
            return

        category = target_guild.get_channel(config["category_id"])
        if not category:
            await message.channel.send("ModMail is misconfigured on that server — the category no longer exists.")
            return

        overwrites = {
            target_guild.default_role: discord.PermissionOverwrite(view_channel=False),
            target_guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        channel = await target_guild.create_text_channel(
            name=f"modmail-{message.author.name}",
            category=category,
            overwrites=overwrites,
            topic=f"ModMail thread for {message.author} ({message.author.id})",
        )

        await db.create_modmail_thread(target_guild.id, message.author.id, channel.id, datetime.datetime.utcnow().isoformat())

        intro = discord.Embed(
            title="New ModMail Thread",
            description=f"{message.author.mention} (`{message.author.id}`) opened a thread.",
            color=discord.Color.green(),
        )
        first_msg = discord.Embed(description=message.content, color=discord.Color.green())
        first_msg.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)

        await channel.send(embed=intro, view=ModmailCloseView())
        await channel.send(embed=first_msg)

        await message.channel.send(
            f"Your message was sent to the **{target_guild.name}** staff team. "
            f"They'll reply here — just keep DMing me to continue the conversation."
        )

    async def _handle_thread_message(self, message: discord.Message):
        thread = await db.get_modmail_thread_by_channel(message.channel.id)
        if not thread or thread["status"] != "open":
            return
        if message.content.startswith("/"):
            return  # let slash commands through untouched

        member = self.bot.get_user(thread["user_id"])
        if not member:
            return
        try:
            embed = discord.Embed(description=message.content, color=discord.Color.blurple())
            embed.set_author(name=f"Staff ({message.author.display_name})", icon_url=message.author.display_avatar.url)
            if message.attachments:
                embed.set_image(url=message.attachments[0].url)
            await member.send(embed=embed)
            await message.add_reaction("✅")
        except discord.Forbidden:
            await message.channel.send("⚠️ Couldn't deliver that — the user may have DMs closed.")

    # ---------------- Closing ----------------

    async def close_thread(self, channel: discord.TextChannel, closed_by: discord.abc.User, reason: str):
        thread = await db.get_modmail_thread_by_channel(channel.id)
        if not thread:
            return
        await db.close_modmail_thread(channel.id)

        member = self.bot.get_user(thread["user_id"])
        if member:
            try:
                await member.send(f"Your modmail thread has been closed. Reason: {reason}\nDM me again anytime to open a new one.")
            except discord.Forbidden:
                pass

        guild = channel.guild
        config = await db.get_modmail_config(guild.id)
        if config["log_channel_id"]:
            log_channel = guild.get_channel(config["log_channel_id"])
            if log_channel:
                embed = discord.Embed(title="ModMail Thread Closed", color=discord.Color.dark_grey())
                embed.add_field(name="User", value=f"<@{thread['user_id']}>")
                embed.add_field(name="Closed by", value=str(closed_by))
                embed.add_field(name="Reason", value=reason, inline=False)
                await log_channel.send(embed=embed)

        try:
            await channel.delete(reason=f"ModMail thread closed by {closed_by}")
        except discord.Forbidden:
            pass


async def setup(bot):
    await bot.add_cog(ModMail(bot))
