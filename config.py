"""
config.py
Shared constants used across the bot. Safe to edit freely.
"""

# Embed color scheme
COLOR_SUCCESS = 0x57F287
COLOR_ERROR = 0xED4245
COLOR_WARNING = 0xFEE75C
COLOR_INFO = 0x5865F2
COLOR_DEFAULT = 0x2B2D31

# Credit line shown in embed footers and bot presence.
BOT_CREDIT = "Made by Fritz"

# Ticket system options
TICKET_CATEGORIES = ["General Support", "Technical Issue", "Billing", "Report a User", "Other"]
TICKET_PRIORITIES = ["Low", "Medium", "High", "Urgent"]

PRIORITY_EMOJI = {
    "Low": "🟢",
    "Medium": "🟡",
    "High": "🟠",
    "Urgent": "🔴",
}
