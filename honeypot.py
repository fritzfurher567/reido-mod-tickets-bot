"""
honeypot.py
A trap channel: real members never post there. Anyone who posts in it
gets deleted + instant-banned. Almost exclusively catches raid bots and
scammers since legitimate members are told to ignore the channel.
"""
import datetime

import discord
from discord import app_commands
from discord.ext import commands

import database as db


class Honeypot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="sethoneypot", description="[Admin] Set the honeypot trap channel")
    @app_commands.checks.has_permissions(administrator=True)
    async def sethoneypot(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await db.set_honeypot_channel(interaction.guild_id, channel.id)
        await interaction.response.send_message(
            f"Honeypot set to {channel.mention}. Leave it visible in the channel list with an "
            f"enticing name (e.g. #verify-here, #free-nitro) but tell real members never to post "
            f"there — anyone who does gets auto-banned.",
            ephemeral=True,
        )

    @app_commands.command(name="honeypot-toggle", description="[Admin] Toggle ban-on-trigger vs kick-on-trigger")
    @app_commands.checks.has_permissions(administrator=True)
    async def honeypot_toggle(self, interaction: discord.Interaction, ban: bool):
        config = await db.get_honeypot_config(interaction.guild_id)
        # reuse update pattern directly since there's no dedicated setter for this column
        import aiosqlite
        async with aiosqlite.connect(db.DB_PATH) as conn:
            await conn.execute(
                "UPDATE honeypot_config SET ban_on_trigger = ? WHERE guild_id = ?",
                (int(ban), interaction.guild_id)
            )
            await conn.commit()
        await interaction.response.send_message(
            f"Honeypot will now **{'ban' if ban else 'kick'}** triggering members.", ephemeral=True
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        config = await db.get_honeypot_config(message.guild.id)
        if not config["channel_id"] or config["channel_id"] != message.channel.id:
            return

        try:
            await message.delete()
        except discord.Forbidden:
            pass

        try:
            if config["ban_on_trigger"]:
                await message.author.ban(reason="Triggered honeypot channel")
                action = "Banned"
            else:
                await message.author.kick(reason="Triggered honeypot channel")
                action = "Kicked"
        except discord.Forbidden:
            action = "Flagged (missing permissions to act)"

        guild_config = await db.get_guild_config(message.guild.id)
        log_channel_id = guild_config.get("mod_log_channel")
        if log_channel_id:
            log_channel = message.guild.get_channel(log_channel_id)
            if log_channel:
                embed = discord.Embed(
                    title=f"🍯 Honeypot Triggered — {action}",
                    description=f"{message.author.mention} (`{message.author.id}`) posted in the honeypot channel.",
                    color=discord.Color.dark_red(),
                    timestamp=datetime.datetime.utcnow(),
                )
                if message.content:
                    embed.add_field(name="Message content", value=message.content[:1000], inline=False)
                await log_channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Honeypot(bot))
