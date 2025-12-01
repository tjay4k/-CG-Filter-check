import discord
import json
import datetime
import aiohttp
import os
from discord.ext import commands
from discord import app_commands


# ------------------ CONFIG ------------------
TARGET_GUILD_ID = 1309981030790463529
TARGET_CHANNEL_ID = 1420801597126217861

# ❗ List of servers where the panel & commands exist
CONTROL_GUILDS = [
    1309981030790463529,   # control server 1
    1322753191749615626    # control server 2
]

# Role required to use the invite button
REQUIRED_ROLE_ID = 1363491917282676836

# Admin roles (permitted to run admin commands)
ADMIN_ROLE_IDS = {1403468054150643814}

BOT_OWNER_ID = 433328712532885504

LOG_WEBHOOK_URL = (
    "https://discord.com/api/webhooks/1445173947367948601/InhWvggtcgJTzbJOEympACCMjzHl19WoQLrATXKGm25D01XZWdfObtPnDqunE53nKtKV"
)

DATA_FILE = "invited_users.json"


# ------------------ JSON DATA HANDLING ------------------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"requested": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


data = load_data()


# ------------------ WEBHOOK LOGGING ------------------
async def log_to_webhook(message: str):
    if not LOG_WEBHOOK_URL:
        return
    async with aiohttp.ClientSession() as session:
        await session.post(LOG_WEBHOOK_URL, json={"content": message})


# ------------------ INVITE BUTTON ------------------
class InviteButton(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Get Invite", style=discord.ButtonStyle.primary, custom_id="invite_button")
    async def get_invite(self, interaction: discord.Interaction, button: discord.ui.Button):

        user = interaction.user
        user_id = user.id

        # Ensure button only works in control guilds
        if interaction.guild.id not in CONTROL_GUILDS:
            return await interaction.response.send_message(
                "❌ This button can only be used in approved servers.",
                ephemeral=True
            )

        # Owner bypasses restrictions
        if user_id != BOT_OWNER_ID:

            # Check role
            required_role = interaction.guild.get_role(REQUIRED_ROLE_ID)
            if required_role not in user.roles:
                return await interaction.response.send_message(
                    "❌ You do not have the required role to request an invite.",
                    ephemeral=True
                )

            # Already got invite
            if user_id in data["requested"]:
                return await interaction.response.send_message(
                    "❌ You already received an invite.",
                    ephemeral=True
                )

        # Create invite from target guild
        target_guild = self.bot.get_guild(TARGET_GUILD_ID)
        target_channel = target_guild.get_channel(TARGET_CHANNEL_ID)

        invite = await target_channel.create_invite(
            max_uses=1,
            max_age=3600,
            unique=True
        )

        # Track user
        if user_id != BOT_OWNER_ID:
            data["requested"].append(user_id)
            save_data(data)

        await log_to_webhook(
            f"🎟️ **{user}** (ID: {user_id}) requested an invite."
        )

        # DM the user
        try:
            await user.send(
                f"# **Congratulations on passing the CG Academy!** 🎉\n"
                f"### You must now do the following:\n"
                f"• Request to join the Coruscant Guard [Roblox group](https://www.roblox.com/communities/34815613/TGR-Coruscant-Gu-rd#!/about)\n"
                f"• Join the Coruscant Guard [Discord Server]({invite.url}) **(one-time use only)**\n"
                f"• Fill out the verification format in https://discord.com/channels/1269671417192910860/1352349414546604133\n"
                f"• Change your server name to: [TRN] | (Your username) | (your timezone)\n"
                f"• Join the Republic Security Forces [Discord Server](https://discord.gg/UTvv6bg7Ws)\n"
                f"• Fill out the format in https://discord.com/channels/1343041443316502590/1343044438213001307\n"
                f"• Leave the [TGR] PEACEKEEPER ACADEMY Discord Server\n"
                f"• Wait patiently to be accepted and roled.\n\n"
                f"\n"
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

    # ---------- Slash Command: Send Invite Panel ----------
    @app_commands.guilds(*[discord.Object(id=g) for g in CONTROL_GUILDS])
    @app_commands.command(name="sendinvitepanel", description="Send the permanent invite panel.")
    async def sendinvitepanel(self, interaction: discord.Interaction):

        if interaction.guild_id not in CONTROL_GUILDS:
            return await interaction.response.send_message("❌ Not allowed here.", ephemeral=True)

        # Role check
        if (
            not any(role.id in ADMIN_ROLE_IDS for role in interaction.user.roles)
            and interaction.user.id != BOT_OWNER_ID
        ):
            return await interaction.response.send_message("❌ You are not authorized.", ephemeral=True)

        embed = discord.Embed(
            title="Request Invite",
            description=(
                "**Click the button to receive the following:**\n"
                "• A **one-time use** invite link to the CG Discord Server\n"
                "• Information on what you are **required** to do next.\n\n"
                "• If you do not receive a DM, contact <@433328712532885504>."
            ),
            color=0xFFFFFF
        )

        await interaction.response.send_message(
            embed=embed,
            view=InviteButton(self.bot)
        )

    # ---------- Slash Command: Reset invite eligibility ----------
    @app_commands.guilds(*[discord.Object(id=g) for g in CONTROL_GUILDS])
    @app_commands.command(name="resetinvite", description="Reset a user's invite eligibility.")
    async def resetinvite(self, interaction: discord.Interaction, user: discord.User):

        if interaction.guild_id not in CONTROL_GUILDS:
            return await interaction.response.send_message("❌ Not allowed here.", ephemeral=True)

        if (
            not any(role.id in ADMIN_ROLE_IDS for role in interaction.user.roles)
            and interaction.user.id != BOT_OWNER_ID
        ):
            return await interaction.response.send_message("❌ You are not authorized.", ephemeral=True)

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
            await interaction.response.send_message("ℹ️ That user was not restricted.")

    # ---------- Auto-remove if user leaves ANY control server ----------
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):

        if member.guild.id not in CONTROL_GUILDS:
            return

        uid = member.id

        if uid in data["requested"]:
            data["requested"].remove(uid)
            save_data(data)

            await log_to_webhook(
                f"🚪 **{member}** (ID: {uid}) left a control server — removed from invite list."
            )


async def setup(bot):
    await bot.add_cog(InviteCog(bot))
