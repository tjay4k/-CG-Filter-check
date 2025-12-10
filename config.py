"""
Configuration loader for CG Filter Bot
Loads settings from config.yaml
"""

import yaml
import os
from typing import Any

class Config:
    """Configuration manager that loads from YAML file"""
    
    def __init__(self, config_file: str = "config.yaml"):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_file = os.path.join(current_dir, config_file)
        self._config = self._load_config()
    
    def _load_config(self) -> dict:
        """Load configuration from YAML file"""
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(
                f"Configuration file '{self.config_file}' not found. "
                "Please create it from config.yaml.example"
            )
        
        with open(self.config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def reload(self):
        """Reload configuration from file"""
        self._config = self._load_config()
    
    def get(self, *keys, default=None) -> Any:
        """
        Get nested configuration value
        
        Usage:
            config.get('general', 'bot_owners')
            config.get('filter_check', 'thresholds', 'min_badge_count')
        """
        value = self._config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        return value
    
    # Convenience properties for commonly used values
    @property
    def bot_owners(self) -> list:
        """List of bot owner IDs"""
        return self.get('general', 'bot_owners', default=[])
    
    @property
    def test_servers(self) -> list:
        """List of test server IDs"""
        return self.get('general', 'test_servers', default=[])
    
    @property
    def error_webhook_url(self) -> str:
        """Error webhook URL"""
        return self.get('general', 'error_webhook_url', default='')
    
    # Helper methods
    def is_bot_owner(self, user_id: int) -> bool:
        """Check if user is a bot owner"""
        return user_id in self.bot_owners
    
    def is_test_server(self, guild_id: int) -> bool:
        """Check if guild is a test server"""
        return guild_id in self.test_servers
    
    def has_permission(self, user_id: int, user_roles: list, allowed_roles: list) -> bool:
        """
        Check if user has permission based on roles or owner status
        
        Args:
            user_id: Discord user ID
            user_roles: List of role IDs the user has
            allowed_roles: List of role IDs that are allowed (empty = everyone)
        
        Returns:
            True if user has permission
        """
        # Bot owners bypass all checks
        if self.is_bot_owner(user_id):
            return True
        
        # If no roles specified, everyone is allowed
        if not allowed_roles:
            return True
        
        # Check if user has any of the allowed roles
        return any(role_id in allowed_roles for role_id in user_roles)
    
    def is_server_allowed(self, guild_id: int, allowed_servers: list) -> bool:
        """
        Check if command can be used in this server
        
        Args:
            guild_id: Discord guild ID
            allowed_servers: List of allowed server IDs (empty = all servers)
        
        Returns:
            True if server is allowed
        """
        # Test servers are always allowed
        if self.is_test_server(guild_id):
            return True
        
        # If no servers specified, all servers are allowed
        if not allowed_servers:
            return True
        
        # Check if guild is in allowed list
        return guild_id in allowed_servers


# Create global config instance
config = Config()

# Export commonly used values for backward compatibility
BOT_OWNER_IDS = config.bot_owners
TEST_SERVER_IDS = config.test_servers
ERROR_WEBHOOK_URL = config.error_webhook_url

# Export cog-specific configs
FILTER_CHECK = {
    "allowed_servers": config.get('filter_check', 'allowed_servers', default=[]),
    "allowed_roles": config.get('filter_check', 'allowed_roles', default=[]),
    "result_channels": config.get('filter_check', 'result_channels', default={}),
    "main_group": config.get('filter_check', 'roblox', 'main_group'),
    "main_divisions": config.get('filter_check', 'roblox', 'main_divisions', default=[]),
    "sub_divisions": config.get('filter_check', 'roblox', 'sub_divisions', default=[]),
    "trello_board_id": config.get('filter_check', 'trello', 'board_id'),
    "major_blacklist_categories": config.get('filter_check', 'trello', 'major_blacklist_categories', default=[]),
    "deny_blacklist_categories": config.get('filter_check', 'trello', 'deny_blacklist_categories', default=[]),
    "skip_categories": config.get('filter_check', 'trello', 'skip_categories', default=[]),
    "min_discord_age_days": config.get('filter_check', 'thresholds', 'min_discord_age_days', default=90),
    "min_badge_count": config.get('filter_check', 'thresholds', 'min_badge_count', default=480),
}

BOT_MANAGEMENT = {
    "allowed_servers": config.get('bot_management', 'allowed_servers', default=[]),
    "allowed_roles": config.get('bot_management', 'allowed_roles', default=[]),
}

INVITE = {
    "target_guild_id": config.get('invite', 'target', 'guild_id'),
    "target_channel_id": config.get('invite', 'target', 'channel_id'),
    "control_servers": config.get('invite', 'control_servers', default=[]),
    "required_role_id": config.get('invite', 'required_role_id'),
    "admin_roles": config.get('invite', 'admin_roles', default=[]),
    "log_webhook_url": config.get('invite', 'log_webhook_url', default=''),
    "data_file": config.get('invite', 'data_file', default='invited_users.json'),
}

STAFF_RATING = {
   "spreadsheet_url": config.get('staff_rating', 'spreadsheet', 'url'),
   "credentials": config.get('staff_rating', 'spreadsheet', 'credentials_file', default='credentials.json'),
   "command_sheet": config.get('staff_rating', 'spreadsheet', 'sheets', 'high_command', default='Info2'),
   "company_command_sheet": config.get('staff_rating', 'spreadsheet', 'sheets', 'company_command', default='Officers'),
   "servers": config.get('staff_rating', 'servers', default={}),
   "admin_roles": config.get('staff_rating', 'admin_roles', default=[]),
   "reactions": config.get('staff_rating', 'reactions', default=["🟩", "🟨", "🟥"])    
}

# Export helper functions
is_bot_owner = config.is_bot_owner
is_test_server = config.is_test_server
has_permission = config.has_permission
is_server_allowed = config.is_server_allowed