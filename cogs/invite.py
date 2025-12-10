import discord
import json
import os
import aiohttp
from discord.ext import commands
from discord import app_commands

# Import helper functions cleanly
from config import (
    has_permission,
    is_bot_owner,
    is_server_allowed
)
import config


# ------------------ JSON DATA HANDLING ------------------
def load_data():
    file = config.INVITE["data_file"]
    if not os.path.exists(file):
        return {"requested": []}

    with open(file, "r") as f:
        return json.load(f)


def save_data(data):
    with open(config.INVITE["data_file"], "w") as f:
        json.dump(data, f, indent=4)


data = load_data()


# ------------------ WEBHOOK LOGGING ------------------
async def log_to_webhook(message: str):
    webhook_url = config.INVITE.get("log_webhook_url")
    if not webhook_url:
        return

    async with aiohttp.ClientSession() as session:
        await session.post(webhook_url, json={"content": message})


# ------------------ INVITE BUTTON ------------------
class InviteButton(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="Get Invite",
        style=discord.ButtonStyle.primary,
        custom_id="invite_button"
    )
    async def get_invite(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        user_id = user.id

        # Ensure button is only usable in a control server
        if not is_server_allowed(interaction.guild_id, config.INVITE["control_servers"]):
            return await interaction.response.send_message(
                "❌ This button cannot be used here.",
                ephemeral=True
            )

        # Owners bypass the invite limits
        if not is_bot_owner(user_id):

            # Check required role
            required_role = interaction.guild.get_role(
                config.INVITE["required_role_id"])
            if required_role not in user.roles:
                return await interaction.response.send_message(
                    "❌ You do not have the required role to request an invite.",
                    ephemeral=True
                )

            # Prevent duplicate invite
            if user_id in data["requested"]:
                return await interaction.response.send_message(
                    "❌ You already received an invite.",
                    ephemeral=True
                )

        # Create invite from target guild
        target_guild = self.bot.get_guild(config.INVITE["target_guild_id"])
        target_channel = target_guild.get_channel(
            config.INVITE["target_channel_id"])

        invite = await target_channel.create_invite(
            max_uses=1,
            max_age=3600,
            unique=True
        )

        # Track user unless they’re an owner
        if not is_bot_owner(user_id):
            data["requested"].append(user_id)
            save_data(data)

        await log_to_webhook(
            f"🎟️ **{user}** (ID: {user_id}) requested an invite."
        )

        # Try sending DM
        try:
            await user.send(
                f"# **Congratulations on passing the CG Academy!** 🎉\n"
                f"### You must now do the following:\n"
                f"• Request to join the Coruscant Guard Roblox group\n"
                f"• Join the Coruscant Guard Discord Server → {invite.url}\n"
                f"• & Fill out the verification format in https://discord.com/channels/1269671417192910860/1352349414546604133\n"
                f"• & Change your server name to [TRN] | username | timezone\n"
                f"• Join the Republic Security Forces Discord → https://discord.gg/UTvv6bg7Ws\n"
                f"• & Fill out the verification format in https://discord.com/channels/1343041443316502590/1343044438213001307\n"
                f"• & Change your server name to [TRN] | username | timezone\n"
                f"• Leave the PEACEKEEPER ACADEMY Discord\n"
                f"• Wait patiently to be accepted.\n"
            )
        except discord.Forbidden:
            return await interaction.response.send_message(
                "⚠️ I could not DM you. Please enable DMs.",
                ephemeral=True
            )

        return await interaction.response.send_message(
            "📩 Check your DMs! I've sent your invite.",
            ephemeral=True
        )


# ------------------ MAIN COG ------------------
class InviteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def check_admin_permissions(self, interaction: discord.Interaction) -> bool:

        # Must be in control server
        if not is_server_allowed(interaction.guild_id, config.INVITE["control_servers"]):
            await interaction.response.send_message(
                "❌ This command can only be used in control servers.",
                ephemeral=True
            )
            return False

        # Check roles permissions
        user_roles = [role.id for role in interaction.user.roles]
        allowed_roles = config.INVITE["admin_roles"]

        if not has_permission(interaction.user.id, user_roles, allowed_roles):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
            return False

        return True

    # ---------------------------------------------------------
    @app_commands.command(name="sendinvitepanel", description="Send the permanent invite panel.")
    async def sendinvitepanel(self, interaction: discord.Interaction):
        if not await self.check_admin_permissions(interaction):
            return

        embed = discord.Embed(
            title="Request Invite",
            description=(
                "**Click the button to receive:**\n"
                "• A **one-time use** invite link\n"
                "• Information on what you must do next\n\n"
                "If you do not receive a DM, contact <@433328712532885504>."
            ),
            color=0xFFFFFF
        )

        await interaction.response.send_message(
            embed=embed,
            view=InviteButton(self.bot)
        )

    # ---------------------------------------------------------
    @app_commands.command(name="resetinvite", description="Reset a user's invite eligibility.")
    @app_commands.describe(user="User to reset")
    async def resetinvite(self, interaction: discord.Interaction, user: discord.User):
        if not await self.check_admin_permissions(interaction):
            return

        uid = user.id

        if uid in data["requested"]:
            data["requested"].remove(uid)
            save_data(data)

            await interaction.response.send_message(
                f"✅ Reset invite eligibility for **{user}**."
            )
            await log_to_webhook(
                f"🔄 Eligibility reset for {user} by {interaction.user}."
            )
        else:
            await interaction.response.send_message(
                "ℹ️ That user was not restricted.",
                ephemeral=True
            )

    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Automatically remove users from invite tracking when they leave"""
        if not is_server_allowed(member.guild.id, config.INVITE["control_servers"]):
            return

        uid = member.id

        if uid in data["requested"]:
            data["requested"].remove(uid)
            save_data(data)

            await log_to_webhook(
                f"🚪 **{member}** (ID: {uid}) left a control server – removed from invite list."
            )


async def setup(bot):
    await bot.add_cog(InviteCog(bot))
