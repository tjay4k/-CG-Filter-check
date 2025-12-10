import discord
from discord.ext import commands
from discord import app_commands
from discord.ext import tasks
from datetime import datetime, time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import asyncio
import os
import logging

import config
from config import is_server_allowed, has_permission, is_bot_owner

logger = logging.getLogger(__name__)


class StaffRatingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = None
        self.setup_sheets_client()
        
        # Position structure with sheet names and cells
        # Headers: ("header", "Header Text")
        # Positions: (sheet_name, cell_address, position_title)
        self.POSITIONS = [
            # Section header
            ("header", "▬▬▬▬▬ Coruscant Guard High Command ▬▬▬▬▬"),
            # High Command (from Info2 sheet)
            ("Info2", "E14:F14", "**Commander Fox**"),
            ("Info2", "E15:F15", "**Commander Thorn**"),
            ("Info2", "E16:F16", "**Commander Stone**"),
            ("Info2", "E17:F17", "**Lieutenant Thire**"),
            
            # Section header
            ("header", "▬▬▬▬▬ Coruscant Guard Instructor Command ▬▬▬▬▬"),
            # Instructor Command (from Officers sheet)
            ("Officers", "F40", "**Instructor Department Commander**"),
            ("Officers", "F33", "**Instructor Department Executive**"),
            ("Officers", "F21", "**Instructor Department Lead Sergeant**"),
            ("Officers", "F22", "**Instructor Department Sergeant**"),
            ("Officers", "F23", "**Instructor Department Sergeant**"),
            
            # Section header
            ("header", "▬▬▬▬▬ Coruscant Guard Hound Company Command ▬▬▬▬▬"),
            # Hound Company
            ("Officers", "F41", "**Hound Company Commander**"),
            ("Officers", "F30", "**Hound Company Executive**"),
            ("Officers", "F12", "**Hound Company Sergeant**"),
            ("Officers", "F13", "**Hound Company Sergeant**"),
            ("Officers", "F14", "**Hound Company Sergeant**"),
            
            # Section header
            ("header", "▬▬▬▬▬ Coruscant Guard Riot Company Command ▬▬▬▬▬"),
            # Riot Company
            ("Officers", "F42", "**Riot Company Commander**"),
            ("Officers", "F31", "**Riot Company Executive**"),
            ("Officers", "F15", "**Riot Company Sergeant**"),
            ("Officers", "F16", "**Riot Company Sergeant**"),
            ("Officers", "F17", "**Riot Company Sergeant**"),
            
            # Section header
            ("header", "▬▬▬▬▬ Coruscant Guard Shock Company Command ▬▬▬▬▬"),
            # Shock Company
            ("Officers", "F43", "**Shock Company Commander**"),
            ("Officers", "F32", "**Shock Company Executive**"),
            ("Officers", "F18", "**Shock Company Sergeant**"),
            ("Officers", "F19", "**Shock Company Sergeant**"),
            ("Officers", "F20", "**Shock Company Sergeant**"),
        ]
    
    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"{self.__class__.__name__} cog has been loaded")
        # Start the automatic posting task
        if not self.auto_post_rating.is_running():
            self.auto_post_rating.start()
            logger.info("Automatic staff rating task started")
    
    def setup_sheets_client(self):
        """Initialize Google Sheets API client"""
        try:
            # Get credentials path from config
            creds_file = config.STAFF_RATING.get('credentials_file', 'credentials.json')
            
            # Get the directory where this file is located
            current_dir = os.path.dirname(os.path.abspath(__file__))
            creds_path = os.path.join(current_dir, creds_file)
            
            # Check if credentials file exists
            if not os.path.exists(creds_path):
                logger.error(f"credentials file not found at: {creds_path}")
                logger.error(f"Current working directory: {os.getcwd()}")
                logger.error(f"Script directory: {current_dir}")
                return
            
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            logger.info("Loading Google Sheets credentials...")
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                creds_path, 
                scope
            )
            
            logger.info("Authorizing with Google...")
            self.client = gspread.authorize(creds)
            logger.info("✓ Google Sheets client initialized successfully!")
            
        except FileNotFoundError:
            logger.error(f"{creds_file} file not found!")
        except Exception as e:
            logger.error(f"Failed to initialize Sheets client: {e}", exc_info=True)
    
    async def check_permissions(self, interaction: discord.Interaction) -> bool:
        """Check if user has permission to use staff rating commands"""
        user_role_ids = [role.id for role in interaction.user.roles]
        
        if not has_permission(
            interaction.user.id,
            user_role_ids,
            config.STAFF_RATING.get('admin_roles', [])
        ):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
            return False
        
        return True
    
    def get_rating_channel(self, guild_id: int):
        """Get the rating channel ID for a specific guild"""
        servers = config.STAFF_RATING.get('servers', {})
        server_config = servers.get(guild_id, {})
        return server_config.get('rating_channel_id')
    
    def find_member_by_username(self, guild, username):
        """
        Search for a Discord member whose display name contains the username.
        Display names follow format: [RANK] | username | timezone
        """
        if username == "N/A" or not username:
            return None
        
        # Search through all members
        for member in guild.members:
            # Check if username is in their display name (case-insensitive)
            if username.lower() in member.display_name.lower():
                return member
        
        return None
    
    def get_cell_value(self, spreadsheet, sheet_name, cell_address):
        """Get value from a specific cell, handling merged cells"""
        try:
            sheet = spreadsheet.worksheet(sheet_name)
            
            # Handle merged cells (e.g., E14:F14)
            if ":" in cell_address:
                # For merged cells, get the first cell value
                start_cell = cell_address.split(":")[0]
                value = sheet.acell(start_cell).value
            else:
                value = sheet.acell(cell_address).value
            
            # Return "N/A" if empty
            return value.strip() if value and value.strip() else "N/A"
            
        except Exception as e:
            logger.error(f"Error fetching {cell_address} from {sheet_name}: {e}")
            return "N/A"
    
    @app_commands.command(name="post_rating", description="Post the staff rating form")
    async def post_staff_rating(self, interaction: discord.Interaction):
        """Post the staff rating messages with reactions"""
        
        # Check permissions
        if not await self.check_permissions(interaction):
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get the rating channel for this server
            channel_id = self.get_rating_channel(interaction.guild_id)
            if not channel_id:
                await interaction.followup.send(
                    f"❌ This server is not configured for staff ratings. Please contact the bot owner.",
                    ephemeral=True
                )
                return
            
            channel = self.bot.get_channel(channel_id)
            if not channel:
                await interaction.followup.send(
                    f"❌ Could not find channel with ID {channel_id}",
                    ephemeral=True
                )
                return
            
            # Get spreadsheet URL from config
            sheet_url = config.STAFF_RATING.get('spreadsheet_url')
            if not sheet_url:
                await interaction.followup.send(
                    "❌ Spreadsheet URL not configured in config.yaml",
                    ephemeral=True
                )
                return
            
            # Get reactions from config
            reactions = config.STAFF_RATING.get('reactions', ["🟩", "🟨", "🟥"])
            
            # Open spreadsheet
            spreadsheet = self.client.open_by_url(sheet_url)
            
            # Send intro message
            intro_text = """<@&1269671417394499684>
            ## Coruscant Guard Staff Rating
As always, this rating is conducted to gather insight into how our staff team is perceived by the community. The list is ordered from highest to lowest rank.
Please be honest with your feedback, your responses will **not affect any promotions or demotions.** This is solely for internal review and continuous improvement.
Your input helps us grow and improve our training environment, so we truly appreciate you taking the time to participate!"""
            
            await channel.send(intro_text)
            await asyncio.sleep(0.1)
            
            # Process each position
            for item in self.POSITIONS:
                if item[0] == "header":
                    # Send section header
                    await channel.send(item[1])
                    await asyncio.sleep(0.1)
                else:
                    sheet_name, cell_address, position_title = item
                    
                    # Get the current holder from spreadsheet
                    holder = self.get_cell_value(spreadsheet, sheet_name, cell_address)
                    
                    # Try to find the Discord member
                    member = self.find_member_by_username(interaction.guild, holder)
                    
                    # Format the message
                    if member:
                        # Found the member - ping them
                        message_text = f"{position_title} - {member.mention}"
                    else:
                        # Member not found - show plain username
                        message_text = f"{position_title} - {holder}"
                    
                    # Send message
                    msg = await channel.send(message_text)
                    
                    # Add reactions
                    for emoji in reactions:
                        await msg.add_reaction(emoji)
                        await asyncio.sleep(0.3)
                    
                    await asyncio.sleep(0.1)
            
            await interaction.followup.send(
                "✅ Staff rating posted successfully!",
                ephemeral=True
            )
            
        except gspread.exceptions.SpreadsheetNotFound:
            logger.error("Spreadsheet not found. Check URL and service account permissions.")
            await interaction.followup.send(
                "❌ Spreadsheet not found. Check the URL and service account permissions.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error posting staff rating: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="preview_rating", description="Preview staff rating data without posting")
    async def preview_rating(self, interaction: discord.Interaction):
        """Preview the current staff data with member pings"""
        
        # Check permissions
        if not await self.check_permissions(interaction):
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get spreadsheet URL from config
            sheet_url = config.STAFF_RATING.get('spreadsheet_url')
            if not sheet_url:
                await interaction.followup.send(
                    "❌ Spreadsheet URL not configured in config.yaml",
                    ephemeral=True
                )
                return
            
            spreadsheet = self.client.open_by_url(sheet_url)
            
            preview_text = "**Staff Rating Preview:**\n\n"
            
            for item in self.POSITIONS:
                if item[0] == "header":
                    preview_text += f"\n{item[1]}\n"
                else:
                    sheet_name, cell_address, position_title = item
                    holder = self.get_cell_value(spreadsheet, sheet_name, cell_address)
                    
                    # Try to find member
                    member = self.find_member_by_username(interaction.guild, holder)
                    
                    if member:
                        preview_text += f"{position_title} - {member.mention} ✓\n"
                    else:
                        preview_text += f"{position_title} - {holder}\n"
            
            # Split into multiple messages if too long
            if len(preview_text) > 2000:
                chunks = [preview_text[i:i+1900] for i in range(0, len(preview_text), 1900)]
                for chunk in chunks:
                    await interaction.followup.send(chunk, ephemeral=True)
            else:
                await interaction.followup.send(preview_text, ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error previewing staff rating: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

    @tasks.loop(time=time(hour=21, minute=0)) # Runs every sunday at 21:00 PM UTC / 20:00 PM GMT+2
    async def auto_post_rating(self):
        """Automatically post staff rating every Sunday"""
        # Check if today is Sunday (weekday 6)
        if datetime.now().weekday() != 6:
            return
        
        logger.info("Auto-posting staff rating...")
        
        try:
            # Get all configured servers
            servers = config.STAFF_RATING.get('servers', {})
            
            for guild_id, server_config in servers.items():
                # Skip if auto_post is disabled for this server
                if not server_config.get('auto_post', False):
                    continue
                
                channel_id = server_config.get('rating_channel_id')
                if not channel_id:
                    logger.warning(f"No rating channel configured for guild {guild_id}")
                    continue
                
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    logger.warning(f"Could not find channel {channel_id} for guild {guild_id}")
                    continue
                
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    logger.warning(f"Could not find guild {guild_id}")
                    continue
                
                # Post the rating
                await self._post_rating_to_channel(channel, guild)
                logger.info(f"Successfully auto-posted staff rating to guild {guild_id}")
                
                # Add delay between servers to avoid rate limits
                await asyncio.sleep(2)
                
        except Exception as e:
            logger.error(f"Error in auto_post_rating: {e}", exc_info=True)
    
    @auto_post_rating.before_loop
    async def before_auto_post(self):
        """Wait until bot is ready before starting the loop"""
        await self.bot.wait_until_ready()
        logger.info("Auto-post task waiting for Sunday at 12:00 PM UTC")
    
    async def _post_rating_to_channel(self, channel: discord.TextChannel, guild: discord.Guild):
        """Helper method to post rating to a specific channel"""
        try:
            # Get spreadsheet URL from config
            sheet_url = config.STAFF_RATING.get('spreadsheet_url')
            if not sheet_url:
                logger.error("Spreadsheet URL not configured")
                return
            
            # Get reactions from config
            reactions = config.STAFF_RATING.get('reactions', ["🟩", "🟨", "🟥"])
            
            # Open spreadsheet
            spreadsheet = self.client.open_by_url(sheet_url)
            
            # Send intro message
            intro_text = """<@&1269671417394499684>
## Coruscant Guard Staff Rating
As always, this rating is conducted to gather insight into how our staff team is perceived by the community. The list is ordered from highest to lowest rank.
Please be honest with your feedback, your responses will **not affect any promotions or demotions.** This is solely for internal review and continuous improvement.
Your input helps us grow and improve our training environment, so we truly appreciate you taking the time to participate!"""
            
            await channel.send(intro_text)
            await asyncio.sleep(0.1)
            
            # Process each position
            for item in self.POSITIONS:
                if item[0] == "header":
                    await channel.send(item[1])
                    await asyncio.sleep(0.1)
                else:
                    sheet_name, cell_address, position_title = item
                    holder = self.get_cell_value(spreadsheet, sheet_name, cell_address)
                    member = self.find_member_by_username(guild, holder)
                    
                    if member:
                        message_text = f"{position_title} - {member.mention}"
                    else:
                        message_text = f"{position_title} - {holder}"
                    
                    msg = await channel.send(message_text)
                    
                    for emoji in reactions:
                        await msg.add_reaction(emoji)
                        await asyncio.sleep(0.3)
                    
                    await asyncio.sleep(0.1)
                    
        except Exception as e:
            logger.error(f"Error posting rating to channel {channel.id}: {e}", exc_info=True)
    
    def cog_unload(self):
        """Clean up when cog is unloaded"""
        self.auto_post_rating.cancel()


async def setup(bot):
    await bot.add_cog(StaffRatingCog(bot))