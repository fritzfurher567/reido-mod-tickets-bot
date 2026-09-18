"""
cogs/tickets.py
Full ticket support system:
- A persistent panel with a "Create Ticket" button
- Category selection (General, Technical, Billing, Report, Other)
- Priority selection (Low, Medium, High, Urgent)
- Ticket channels are created per-user with proper permission overwrites
- Claim / add / remove members / close with a saved text transcript
"""

import datetime
import io

import discord
from discord import app_commands
from discord.ext import commands

import database as db
from config import (
    COLOR_SUCCESS, COLOR_ERROR, COLOR_INFO, BOT_CREDIT,
    TICKET_CATEGORIES, TICKET_PRIORITIES, PRIORITY_EMOJI,
)


def base_embed(title: str, description: str, color: int) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color,
                           timestamp=datetime.datetime.utcnow())
    embed.set_footer(text=BOT_CREDIT)
    return embed


class PrioritySelect(discord.ui.Select):
    def __init__(self, category: str):
        self.category = category
        options = [
            discord.SelectOption(label=p, emoji=PRIORITY_EMOJI.get(p)) for p in TICKET_PRIORITIES
        ]
        super().__init__(placeholder="Select a priority level...", options=options, custom_id="ticket_priority_select")

    async def callback(self, interaction: discord.Interaction):
        priority = self.values[0]
        await create_ticket_channel(interaction, self.category, priority)


class PrioritySelectView(discord.ui.View):
    def __init__(self, category: str):
        super().__init__(timeout=120)
        self.add_item(PrioritySelect(category))


class CategorySelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=c) for c in TICKET_CATEGORIES]
        super().__init__(placeholder="Select a category...", options=options, custom_id="ticket_category_select")

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        existing = await db.get_open_ticket_for_user(interaction.guild.id, interaction.user.id)
        if existing:
            channel = interaction.guild.get_channel(existing["channel_id"])
            msg = f"You already have an open ticket: {channel.mention}" if channel else "You already have an open ticket."
            return await interaction.response.send_message(
                embed=base_embed("Ticket Already Open", msg, COLOR_ERROR), ephemeral=True
            )
        await interaction.response.send_message(
            embed=base_embed("Select Priority", f"Category: **{category}**\nNow choose a priority level:", COLOR_INFO),
            view=PrioritySelectView(category),
            ephemeral=True
        )


class CategorySelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CategorySelect())


class TicketPanelView(discord.ui.View):
    """Persistent view attached to the ticket panel message."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.blurple, emoji="🎫", custom_id="ticket_create_button")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            embed=base_embed("Open a Ticket", "Please select a category for your ticket:", COLOR_INFO),
            view=CategorySelectView(),
            ephemeral=True
        )


class TicketControlView(discord.ui.View):
    """Persistent view attached inside each ticket channel."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.green, emoji="🙋", custom_id="ticket_claim_button")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket = await db.get_ticket_by_channel(interaction.channel.id)
        if not ticket:
            return await interaction.response.send_message("This isn't a ticket channel.", ephemeral=True)
        await db.claim_ticket(interaction.channel.id, interaction.user.id)
        await interaction.response.send_message(
            embed=base_embed("Ticket Claimed", f"{interaction.user.mention} is now handling this ticket.", COLOR_SUCCESS)
        )

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red, emoji="🔒", custom_id="ticket_close_button")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await close_ticket_channel(interaction)


async def create_ticket_channel(interaction: discord.Interaction, category: str, priority: str):
    guild = interaction.guild
    config = await db.get_guild_config(guild.id)
    category_id = config.get("ticket_category_id")
    ticket_category = guild.get_channel(category_id) if category_id else None

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
    }

    safe_name = "".join(c for c in interaction.user.name.lower() if c.isalnum()) or "user"
    channel_name = f"ticket-{safe_name}"

    channel = await guild.create_text_channel(
        name=channel_name,
        category=ticket_category,
        overwrites=overwrites,
        reason=f"Ticket opened by {interaction.user}",
    )

    timestamp = datetime.datetime.utcnow().isoformat()
    ticket_id = await db.create_ticket(guild.id, channel.id, interaction.user.id, category, priority, timestamp)

    intro = base_embed(
        f"Ticket #{ticket_id}",
        f"**Opened by:** {interaction.user.mention}\n"
        f"**Category:** {category}\n"
        f"**Priority:** {PRIORITY_EMOJI.get(priority, '')} {priority}\n\n"
        f"Support will be with you shortly. Use the buttons below to manage this ticket.",
        COLOR_INFO,
    )
    await channel.send(content=interaction.user.mention, embed=intro, view=TicketControlView())

    await interaction.response.send_message(
        embed=base_embed("Ticket Created", f"Your ticket has been created: {channel.mention}", COLOR_SUCCESS),
        ephemeral=True
    )

    log_channel_id = config.get("ticket_log_channel")
    if log_channel_id:
        log_channel = guild.get_channel(log_channel_id)
        if log_channel:
            await log_channel.send(embed=base_embed(
                "Ticket Opened",
                f"**Ticket:** {channel.mention}\n**User:** {interaction.user.mention}\n**Category:** {category}\n**Priority:** {priority}",
                COLOR_INFO
            ))


async def close_ticket_channel(interaction: discord.Interaction):
    ticket = await db.get_ticket_by_channel(interaction.channel.id)
    if not ticket:
        return await interaction.response.send_message("This isn't a ticket channel.", ephemeral=True)

    await interaction.response.send_message(embed=base_embed("Closing Ticket", "Saving transcript and closing this ticket...", COLOR_WARNING if False else COLOR_INFO))

    # Build a simple text transcript
    lines = []
    async for message in interaction.channel.history(limit=None, oldest_first=True):
        content = message.content or "[embed/attachment]"
        lines.append(f"[{message.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {message.author}: {content}")
    transcript_text = "\n".join(lines) if lines else "No messages."
    transcript_file = discord.File(io.BytesIO(transcript_text.encode()), filename=f"transcript-{interaction.channel.name}.txt")

    await db.close_ticket(interaction.channel.id)

    config = await db.get_guild_config(interaction.guild.id)
    log_channel_id = config.get("ticket_log_channel")
    if log_channel_id:
        log_channel = interaction.guild.get_channel(log_channel_id)
        if log_channel:
            await log_channel.send(
                embed=base_embed("Ticket Closed", f"**Ticket:** #{interaction.channel.name}\n**Closed by:** {interaction.user.mention}", COLOR_ERROR),
                file=transcript_file
            )

    await interaction.channel.send(embed=base_embed("Ticket Closing", "This channel will be deleted in 5 seconds.", COLOR_ERROR))
    await discord.utils.sleep_until(datetime.datetime.utcnow() + datetime.timedelta(seconds=5))
    await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        # Register persistent views so buttons keep working after a bot restart
        self.bot.add_view(TicketPanelView())
        self.bot.add_view(TicketControlView())

    # ---------- SETUP ----------
    @app_commands.command(name="ticket-setup", description="Configure the ticket system for this server.")
    @app_commands.describe(
        category="Category where new ticket channels will be created",
        log_channel="Channel where ticket logs/transcripts are sent",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_setup(self, interaction: discord.Interaction, category: discord.CategoryChannel, log_channel: discord.TextChannel):
        await db.update_guild_config(
            interaction.guild.id,
            ticket_category_id=category.id,
            ticket_log_channel=log_channel.id,
        )
        await interaction.response.send_message(
            embed=base_embed("Ticket System Configured", f"New tickets will be created under **{category.name}**.\nLogs will go to {log_channel.mention}.", COLOR_SUCCESS)
        )

    # ---------- PANEL ----------
    @app_commands.command(name="ticket-panel", description="Post the ticket creation panel in this channel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_panel(self, interaction: discord.Interaction):
        embed = base_embed(
            "🎫 Support Tickets",
            "Need help? Click the button below to open a ticket.\nYou'll be asked to pick a category and priority level.",
            COLOR_INFO
        )
        await interaction.channel.send(embed=embed, view=TicketPanelView())
        await interaction.response.send_message("Panel posted.", ephemeral=True)

    # ---------- ADD MEMBER ----------
    @app_commands.command(name="ticket-add", description="Add a member to the current ticket.")
    @app_commands.describe(member="The member to add")
    async def ticket_add(self, interaction: discord.Interaction, member: discord.Member):
        ticket = await db.get_ticket_by_channel(interaction.channel.id)
        if not ticket:
            return await interaction.response.send_message("This isn't a ticket channel.", ephemeral=True)
        await interaction.channel.set_permissions(member, view_channel=True, send_messages=True)
        await interaction.response.send_message(embed=base_embed("Member Added", f"{member.mention} was added to this ticket.", COLOR_SUCCESS))

    # ---------- REMOVE MEMBER ----------
    @app_commands.command(name="ticket-remove", description="Remove a member from the current ticket.")
    @app_commands.describe(member="The member to remove")
    async def ticket_remove(self, interaction: discord.Interaction, member: discord.Member):
        ticket = await db.get_ticket_by_channel(interaction.channel.id)
        if not ticket:
            return await interaction.response.send_message("This isn't a ticket channel.", ephemeral=True)
        await interaction.channel.set_permissions(member, overwrite=None)
        await interaction.response.send_message(embed=base_embed("Member Removed", f"{member.mention} was removed from this ticket.", COLOR_ERROR))

    # ---------- SET PRIORITY ----------
    @app_commands.command(name="ticket-priority", description="Change the priority of the current ticket.")
    @app_commands.choices(priority=[app_commands.Choice(name=p, value=p) for p in TICKET_PRIORITIES])
    async def ticket_priority(self, interaction: discord.Interaction, priority: app_commands.Choice[str]):
        ticket = await db.get_ticket_by_channel(interaction.channel.id)
        if not ticket:
            return await interaction.response.send_message("This isn't a ticket channel.", ephemeral=True)
        await db.set_ticket_priority(interaction.channel.id, priority.value)
        await interaction.response.send_message(
            embed=base_embed("Priority Updated", f"Priority set to {PRIORITY_EMOJI.get(priority.value, '')} **{priority.value}**.", COLOR_INFO)
        )

    # ---------- CLOSE (slash command version) ----------
    @app_commands.command(name="ticket-close", description="Close the current ticket.")
    async def ticket_close(self, interaction: discord.Interaction):
        await close_ticket_channel(interaction)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
