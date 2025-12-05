import discord
from discord.ext import commands
from discord import app_commands

import config
from config import has_permission, is_server_allowed


class CogManager(commands.Cog):
    """Cog for managing other cogs (reload, load, unload)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def check_permissions(self, interaction: discord.Interaction) -> bool:
        """Check if user has permission to use bot management commands."""

        # Check if command is allowed in this server
        allowed_servers = config.BOT_MANAGEMENT["allowed_servers"]
        if not is_server_allowed(interaction.guild_id, allowed_servers):
            await interaction.response.send_message(
                "❌ Bot management commands are not available in this server.",
                ephemeral=True
            )
            return False

        # Check user's roles
        user_roles = [role.id for role in interaction.user.roles]
        allowed_roles = config.BOT_MANAGEMENT["allowed_roles"]

        if not has_permission(interaction.user.id, user_roles, allowed_roles):
            await interaction.response.send_message(
                "❌ You don't have permission to use bot management commands.",
                ephemeral=True
            )
            return False

        return True

    # ----------------------------------------------------------------------
    # Reload Command
    # ----------------------------------------------------------------------
    @app_commands.command(name="reload", description="Reload a bot cog")
    @app_commands.describe(cog="The name of the cog to reload")
    async def reload(self, interaction: discord.Interaction, cog: str):
        if not await self.check_permissions(interaction):
            return

        try:
            await self.bot.reload_extension(f"cogs.{cog}")
            await interaction.response.send_message(
                f"✅ Cog `{cog}` reloaded successfully!",
                ephemeral=True
            )
        except commands.ExtensionNotLoaded:
            await interaction.response.send_message(
                f"⚠️ Cog `{cog}` is not loaded.",
                ephemeral=True
            )
        except commands.ExtensionNotFound:
            await interaction.response.send_message(
                f"❌ Cog `{cog}` not found.",
                ephemeral=True
            )
        except commands.ExtensionFailed as e:
            await interaction.response.send_message(
                f"❌ Failed to reload `{cog}`: {e}",
                ephemeral=True
            )

    # ----------------------------------------------------------------------
    # Load Command
    # ----------------------------------------------------------------------
    @app_commands.command(name="load", description="Load a bot cog")
    @app_commands.describe(cog="The name of the cog to load")
    async def load(self, interaction: discord.Interaction, cog: str):
        if not await self.check_permissions(interaction):
            return

        try:
            await self.bot.load_extension(f"cogs.{cog}")
            await interaction.response.send_message(
                f"✅ Cog `{cog}` loaded successfully!",
                ephemeral=True
            )
        except commands.ExtensionAlreadyLoaded:
            await interaction.response.send_message(
                f"⚠️ Cog `{cog}` is already loaded.",
                ephemeral=True
            )
        except commands.ExtensionNotFound:
            await interaction.response.send_message(
                f"❌ Cog `{cog}` not found.",
                ephemeral=True
            )
        except commands.ExtensionFailed as e:
            await interaction.response.send_message(
                f"❌ Failed to load `{cog}`: {e}",
                ephemeral=True
            )

    # ----------------------------------------------------------------------
    # Unload Command
    # ----------------------------------------------------------------------
    @app_commands.command(name="unload", description="Unload a bot cog")
    @app_commands.describe(cog="The name of the cog to unload")
    async def unload(self, interaction: discord.Interaction, cog: str):
        if not await self.check_permissions(interaction):
            return

        try:
            await self.bot.unload_extension(f"cogs.{cog}")
            await interaction.response.send_message(
                f"✅ Cog `{cog}` unloaded successfully!",
                ephemeral=True
            )
        except commands.ExtensionNotLoaded:
            await interaction.response.send_message(
                f"⚠️ Cog `{cog}` is not loaded.",
                ephemeral=True
            )
        except commands.ExtensionNotFound:
            await interaction.response.send_message(
                f"❌ Cog `{cog}` not found.",
                ephemeral=True
            )
        except commands.ExtensionFailed as e:
            await interaction.response.send_message(
                f"❌ Failed to unload `{cog}`: {e}",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(CogManager(bot))
