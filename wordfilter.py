"""
wordfilter.py
Simple server-side word blacklist: matched messages get deleted.
Complements Automod.py's existing checks rather than replacing them.
"""
import discord
from discord import app_commands
from discord.ext import commands

import database as db


class WordFilter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="blacklist-add", description="[Admin] Add a word to the blacklist")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def blacklist_add(self, interaction: discord.Interaction, word: str):
        await db.add_blacklisted_word(interaction.guild_id, word)
        await interaction.response.send_message(f"Added `{word}` to the blacklist.", ephemeral=True)

    @app_commands.command(name="blacklist-remove", description="[Admin] Remove a word from the blacklist")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def blacklist_remove(self, interaction: discord.Interaction, word: str):
        removed = await db.remove_blacklisted_word(interaction.guild_id, word)
        if removed:
            await interaction.response.send_message(f"Removed `{word}` from the blacklist.", ephemeral=True)
        else:
            await interaction.response.send_message("That word wasn't on the blacklist.", ephemeral=True)

    @app_commands.command(name="blacklist-list", description="[Admin] View the word blacklist")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def blacklist_list(self, interaction: discord.Interaction):
        words = await db.get_blacklisted_words(interaction.guild_id)
        if not words:
            await interaction.response.send_message("Blacklist is empty.", ephemeral=True)
            return
        await interaction.response.send_message(f"Blacklisted words: {', '.join(f'`{w}`' for w in words)}", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        words = await db.get_blacklisted_words(message.guild.id)
        if not words:
            return
        content_lower = message.content.lower()
        if any(w in content_lower for w in words):
            try:
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention} your message was removed for containing a blacklisted word.",
                    delete_after=6,
                )
            except discord.Forbidden:
                pass


async def setup(bot):
    await bot.add_cog(WordFilter(bot))
