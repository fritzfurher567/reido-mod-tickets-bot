# Mod + Tickets Bot

A stripped-down build of Nexus with just the moderation and ticket/modmail
systems wired up — nothing else loads.

## Setup

1. Install Python 3.10+.
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and paste your bot's token into `DISCORD_TOKEN`.
4. `python main.py`

The bot creates its own `bot_data.db` (SQLite) on first run — no external
database or dashboard needed.

## What's included

**Moderation** (`moderation.py`, `moderation2.py`, `modextra.py`)
`/kick` `/ban` `/unban` `/unbanid` `/timeout` `/untimeout` `/warn` `/warnings`
`/clearwarnings` `/removewarning` `/purge` `/purgeuser` `/lock` `/unlock`
`/lockdown` `/slowmode` `/nickname` `/forcenick` `/resetnick` `/addrole`
`/removerole` `/softban` `/nuke` `/banlist` `/muterole-setup` `/muterole-apply`
`/setmodlog`

**Auto-moderation** (`automod.py`, `wordfilter.py`, `honeypot.py`, `security.py`)
Banned-word filters, mention-spam limits, a trap channel that auto-bans
anyone who posts in it, and `/emergency-lockdown` for a full server freeze.

**Tickets** (`tickets.py`) — channel-based support tickets with categories
(General Support, Technical Issue, Billing, Report a User, Other) and
priority levels (Low/Medium/High/Urgent). `/ticket-setup`, `/ticket-panel`
posts the button members click to open one, plus claim/add/remove/close
with a saved transcript.

**ModMail** (`modmail.py`) — members DM the bot directly and it opens a
private staff channel; replies there relay back to the member's DMs.
`/modmail-setup`, `/modmail-close`, `/modmail-reply`.

**Permissions & audit** (`permissions.py`, `audit.py`) — restrict any
command to specific roles with `/permission-restrict`, and log who ran
what with `/auditlog-channel`.

**Appeals** (`appeals.py`) — `/appeal` lets a banned/muted user submit an
appeal for staff to accept or deny.

## Notes

- `database.py` is the full Nexus database module (it also defines tables
  for economy, leveling, etc. from the rest of the bot). Nothing outside
  the cogs above is loaded, so none of that surfaces as commands — it's
  just unused schema sitting in the file. Say the word if you want it
  trimmed down to only what these cogs touch.
- Every cog here was dry-run loaded against a live `discord.py` bot
  instance to confirm it imports and registers cleanly; the only thing
  not tested is an actual Discord token/connection.
- `config.py` has the ticket categories, priorities, and the embed footer
  credit line — all safe to edit.
