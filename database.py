"""
database.py
Handles all persistent storage using SQLite (via aiosqlite).
Stores per-guild settings, warnings, and ticket records.
"""

import aiosqlite

DB_PATH = "bot_data.db"


async def init_db():
    """Create all tables if they don't already exist. Call this once on bot startup."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Migration: add bank column to economy table if it doesn't exist yet
        # (existing DBs created before this feature won't have it).
        try:
            await db.execute("ALTER TABLE economy ADD COLUMN bank INTEGER DEFAULT 0")
            await db.commit()
        except Exception:
            pass  # column already exists

        try:
            await db.execute("ALTER TABLE economy ADD COLUMN last_crime TEXT")
            await db.commit()
        except Exception:
            pass

        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id INTEGER PRIMARY KEY,
                welcome_channel INTEGER,
                welcome_message TEXT DEFAULT 'Welcome {user} to {server}! We now have {membercount} members.',
                goodbye_channel INTEGER,
                goodbye_message TEXT DEFAULT '{user} has left {server}. We now have {membercount} members.',
                dm_on_join INTEGER DEFAULT 0,
                dm_on_join_message TEXT DEFAULT 'Welcome to {server}! Glad to have you here.',
                dm_on_leave INTEGER DEFAULT 0,
                dm_on_leave_message TEXT DEFAULT 'Sorry to see you leave {server}!',
                mod_log_channel INTEGER,
                mute_role_id INTEGER,
                ticket_category_id INTEGER,
                ticket_log_channel INTEGER,
                ticket_panel_channel INTEGER,
                server_log_channel INTEGER,
                levelup_channel INTEGER,
                verified_role_id INTEGER,
                awards_channel INTEGER,
                loa_channel INTEGER,
                discharge_channel INTEGER,
                audit_log_channel INTEGER,
                birthday_channel INTEGER
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT,
                timestamp TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                category TEXT,
                priority TEXT,
                status TEXT DEFAULT 'open',
                claimed_by INTEGER,
                created_at TEXT NOT NULL
            )
        """)

        # ---- Leveling ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS levels (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 0,
                last_xp_time TEXT,
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS level_roles (
                guild_id INTEGER NOT NULL,
                level INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                PRIMARY KEY (guild_id, level)
            )
        """)

        # ---- Reaction roles ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reaction_roles (
                guild_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                emoji TEXT NOT NULL,
                role_id INTEGER NOT NULL,
                PRIMARY KEY (message_id, emoji)
            )
        """)

        # ---- Auto-moderation ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS automod_config (
                guild_id INTEGER PRIMARY KEY,
                banned_words TEXT DEFAULT '',
                anti_invite INTEGER DEFAULT 0,
                caps_filter INTEGER DEFAULT 0,
                mention_limit INTEGER DEFAULT 0
            )
        """)

        # ---- Custom commands ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS custom_commands (
                guild_id INTEGER NOT NULL,
                trigger TEXT NOT NULL,
                response TEXT NOT NULL,
                PRIMARY KEY (guild_id, trigger)
            )
        """)

        # ---- Reminders ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                guild_id INTEGER,
                remind_at TEXT NOT NULL,
                message TEXT
            )
        """)

        # ---- Economy ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS economy (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                balance INTEGER DEFAULT 0,
                last_daily TEXT,
                last_work TEXT,
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS shop_items (
                guild_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                price INTEGER NOT NULL,
                role_id INTEGER,
                PRIMARY KEY (guild_id, item_name)
            )
        """)

        # ---- Social alerts ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS youtube_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                yt_channel_id TEXT NOT NULL,
                last_video_id TEXT,
                UNIQUE(guild_id, yt_channel_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS twitch_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                twitch_username TEXT NOT NULL,
                is_live INTEGER DEFAULT 0,
                UNIQUE(guild_id, twitch_username)
            )
        """)

        # ---- Command permissions (role restrictions) ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS command_permissions (
                guild_id INTEGER NOT NULL,
                command_name TEXT NOT NULL,
                role_id INTEGER NOT NULL,
                PRIMARY KEY (guild_id, command_name, role_id)
            )
        """)

        # ---- Roblox verification ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS roblox_verifications (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                roblox_id INTEGER NOT NULL,
                roblox_username TEXT NOT NULL,
                verified_at TEXT NOT NULL,
                PRIMARY KEY (guild_id, user_id)
            )
        """)

        # ---- Awards ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS awards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                awarded_by INTEGER NOT NULL,
                title TEXT NOT NULL,
                reason TEXT,
                timestamp TEXT NOT NULL
            )
        """)

        # ---- Leave of Absence ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS loa_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                reason TEXT,
                status TEXT DEFAULT 'pending',
                reviewed_by INTEGER,
                requested_at TEXT NOT NULL
            )
        """)

        # ---- Rank hierarchy ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ranks (
                guild_id INTEGER NOT NULL,
                rank_name TEXT NOT NULL,
                role_id INTEGER NOT NULL,
                rank_order INTEGER NOT NULL,
                PRIMARY KEY (guild_id, rank_name)
            )
        """)

        # ---- Divisions (for transfers) ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS divisions (
                guild_id INTEGER NOT NULL,
                division_name TEXT NOT NULL,
                role_id INTEGER NOT NULL,
                PRIMARY KEY (guild_id, division_name)
            )
        """)

        # ---- Discharges (includes desertions) ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS discharges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                discharged_by INTEGER,
                reason TEXT,
                is_desertion INTEGER DEFAULT 0,
                timestamp TEXT NOT NULL
            )
        """)

        # ---- Events ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                host_id INTEGER NOT NULL,
                event_time TEXT,
                channel_id INTEGER,
                message_id INTEGER,
                status TEXT DEFAULT 'scheduled',
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS event_rsvps (
                event_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                PRIMARY KEY (event_id, user_id)
            )
        """)

        # ---- Audit log ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                command_name TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)

        # ---- Honeypot ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS honeypot_config (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER,
                ban_on_trigger INTEGER DEFAULT 1
            )
        """)

        # ---- Economy: inventory + bounties ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                quantity INTEGER DEFAULT 1,
                PRIMARY KEY (guild_id, user_id, item_name)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bounties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                placed_by INTEGER NOT NULL,
                status TEXT DEFAULT 'open',
                claimed_by INTEGER,
                created_at TEXT NOT NULL
            )
        """)

        # ---- Giveaways ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS giveaways (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER,
                prize TEXT NOT NULL,
                winner_count INTEGER DEFAULT 1,
                ends_at TEXT NOT NULL,
                host_id INTEGER NOT NULL,
                status TEXT DEFAULT 'running',
                last_winners TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS giveaway_entries (
                giveaway_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                PRIMARY KEY (giveaway_id, user_id)
            )
        """)

        # ---- AFK ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS afk_status (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                reason TEXT,
                since TEXT NOT NULL,
                PRIMARY KEY (guild_id, user_id)
            )
        """)

        # ---- Starboard ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS starboard_config (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER,
                threshold INTEGER DEFAULT 3,
                emoji TEXT DEFAULT '⭐'
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS starboard_posts (
                original_message_id INTEGER PRIMARY KEY,
                guild_id INTEGER NOT NULL,
                board_message_id INTEGER NOT NULL
            )
        """)

        # ---- Birthdays ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS birthdays (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                month INTEGER NOT NULL,
                day INTEGER NOT NULL,
                PRIMARY KEY (guild_id, user_id)
            )
        """)

        # ---- Invite tracking ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS invite_uses (
                guild_id INTEGER NOT NULL,
                invite_code TEXT NOT NULL,
                inviter_id INTEGER,
                uses INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, invite_code)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS joined_via (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                invite_code TEXT,
                inviter_id INTEGER,
                PRIMARY KEY (guild_id, user_id)
            )
        """)

        # ---- Suggestions ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                channel_id INTEGER,
                message_id INTEGER,
                content TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS suggestions_config (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER
            )
        """)

        # ---- Duty / patrol logs (Northwind) ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS duty_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                clock_in TEXT NOT NULL,
                clock_out TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS inspections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                inspector_id INTEGER NOT NULL,
                result TEXT NOT NULL,
                notes TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS patrol_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                route TEXT,
                incidents TEXT,
                duration_minutes INTEGER,
                timestamp TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                answers TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                reviewed_by INTEGER,
                channel_id INTEGER,
                message_id INTEGER,
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS applications_config (
                guild_id INTEGER PRIMARY KEY,
                review_channel_id INTEGER
            )
        """)

        # ---- Heists (multiplayer economy event) ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS heists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER,
                organizer_id INTEGER NOT NULL,
                buy_in INTEGER NOT NULL,
                status TEXT DEFAULT 'open',
                starts_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS heist_participants (
                heist_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                PRIMARY KEY (heist_id, user_id)
            )
        """)

        # ---- Quotes ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                author_id INTEGER,
                content TEXT NOT NULL,
                added_by INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # ---- Word filter / blacklist ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS blacklisted_words (
                guild_id INTEGER NOT NULL,
                word TEXT NOT NULL,
                PRIMARY KEY (guild_id, word)
            )
        """)

        # ---- Voice + message activity tracking ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS voice_time (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                seconds INTEGER DEFAULT 0,
                session_start TEXT,
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS message_counts (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                count INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )
        """)

        # ---- Verification gate ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS verification_config (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER,
                verified_role_id INTEGER
            )
        """)

        # ---- Ban appeals ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS appeals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                reviewed_by INTEGER,
                channel_id INTEGER,
                message_id INTEGER,
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS appeals_config (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER
            )
        """)

        # ---- Temp roles / tags / self-roles ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS temp_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                guild_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (guild_id, name)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS selfroles (
                guild_id INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                PRIMARY KEY (guild_id, role_id)
            )
        """)

        # ---- Lottery ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS lottery_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                purchased_at TEXT NOT NULL
            )
        """)

        # ---- Pets ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pets (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                species TEXT NOT NULL,
                hunger INTEGER DEFAULT 50,
                happiness INTEGER DEFAULT 50,
                adopted_at TEXT NOT NULL,
                PRIMARY KEY (guild_id, user_id)
            )
        """)

        # ---- Marriage ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS marriages (
                guild_id INTEGER NOT NULL,
                user1_id INTEGER NOT NULL,
                user2_id INTEGER NOT NULL,
                married_at TEXT NOT NULL
            )
        """)

        # ---- Reputation ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reputation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                from_user_id INTEGER NOT NULL,
                given_at TEXT NOT NULL
            )
        """)

        # ---- Confessions ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS confessions_config (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER,
                counter INTEGER DEFAULT 0
            )
        """)

        # ---- Autoresponders ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS autoresponders (
                guild_id INTEGER NOT NULL,
                trigger TEXT NOT NULL,
                response TEXT NOT NULL,
                PRIMARY KEY (guild_id, trigger)
            )
        """)

        # ---- ModMail ----
        await db.execute("""
            CREATE TABLE IF NOT EXISTS modmail_config (
                guild_id INTEGER PRIMARY KEY,
                category_id INTEGER,
                log_channel_id INTEGER
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS modmail_threads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                status TEXT DEFAULT 'open',
                created_at TEXT NOT NULL
            )
        """)

        await db.commit()


async def get_guild_config(guild_id: int) -> dict:
    """Return the config row for a guild as a dict, creating a default row if missing."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,))
        row = await cursor.fetchone()
        if row is None:
            await db.execute("INSERT INTO guild_config (guild_id) VALUES (?)", (guild_id,))
            await db.commit()
            cursor = await db.execute("SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,))
            row = await cursor.fetchone()
        return dict(row)


async def update_guild_config(guild_id: int, **kwargs):
    """Update arbitrary columns in guild_config for a guild. Pass column=value kwargs."""
    if not kwargs:
        return
    await get_guild_config(guild_id)  # ensure row exists
    columns = ", ".join(f"{key} = ?" for key in kwargs.keys())
    values = list(kwargs.values())
    values.append(guild_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE guild_config SET {columns} WHERE guild_id = ?", values)
        await db.commit()


async def add_warning(guild_id: int, user_id: int, moderator_id: int, reason: str, timestamp: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO warnings (guild_id, user_id, moderator_id, reason, timestamp) VALUES (?, ?, ?, ?, ?)",
            (guild_id, user_id, moderator_id, reason, timestamp)
        )
        await db.commit()
        return cursor.lastrowid


async def get_warnings(guild_id: int, user_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY id DESC",
            (guild_id, user_id)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def clear_warnings(guild_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM warnings WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        await db.commit()


async def remove_warning(guild_id: int, warning_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM warnings WHERE guild_id = ? AND id = ?", (guild_id, warning_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def create_ticket(guild_id: int, channel_id: int, user_id: int, category: str, priority: str, timestamp: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO tickets (guild_id, channel_id, user_id, category, priority, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'open', ?)",
            (guild_id, channel_id, user_id, category, priority, timestamp)
        )
        await db.commit()
        return cursor.lastrowid


async def get_ticket_by_channel(channel_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM tickets WHERE channel_id = ?", (channel_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def claim_ticket(channel_id: int, moderator_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tickets SET claimed_by = ? WHERE channel_id = ?", (moderator_id, channel_id))
        await db.commit()


async def close_ticket(channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tickets SET status = 'closed' WHERE channel_id = ?", (channel_id,))
        await db.commit()


async def set_ticket_priority(channel_id: int, priority: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tickets SET priority = ? WHERE channel_id = ?", (priority, channel_id))
        await db.commit()


async def get_open_ticket_for_user(guild_id: int, user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM tickets WHERE guild_id = ? AND user_id = ? AND status = 'open'",
            (guild_id, user_id)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


# ==================== LEVELING ====================

async def get_level_data(guild_id: int, user_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM levels WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        row = await cursor.fetchone()
        if row is None:
            await db.execute("INSERT INTO levels (guild_id, user_id, xp, level) VALUES (?, ?, 0, 0)", (guild_id, user_id))
            await db.commit()
            return {"guild_id": guild_id, "user_id": user_id, "xp": 0, "level": 0, "last_xp_time": None}
        return dict(row)


async def update_xp(guild_id: int, user_id: int, xp: int, level: int, last_xp_time: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE levels SET xp = ?, level = ?, last_xp_time = ? WHERE guild_id = ? AND user_id = ?",
            (xp, level, last_xp_time, guild_id, user_id)
        )
        await db.commit()


async def get_level_leaderboard(guild_id: int, limit: int = 10) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM levels WHERE guild_id = ? ORDER BY xp DESC LIMIT ?", (guild_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def set_level_role(guild_id: int, level: int, role_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO level_roles (guild_id, level, role_id) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, level) DO UPDATE SET role_id = excluded.role_id",
            (guild_id, level, role_id)
        )
        await db.commit()


async def get_level_roles(guild_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM level_roles WHERE guild_id = ? ORDER BY level ASC", (guild_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def remove_level_role(guild_id: int, level: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM level_roles WHERE guild_id = ? AND level = ?", (guild_id, level))
        await db.commit()
        return cursor.rowcount > 0


# ==================== REACTION ROLES ====================

async def add_reaction_role(guild_id: int, message_id: int, emoji: str, role_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO reaction_roles (guild_id, message_id, emoji, role_id) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(message_id, emoji) DO UPDATE SET role_id = excluded.role_id",
            (guild_id, message_id, emoji, role_id)
        )
        await db.commit()


async def remove_reaction_role(message_id: int, emoji: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM reaction_roles WHERE message_id = ? AND emoji = ?", (message_id, emoji))
        await db.commit()
        return cursor.rowcount > 0


async def get_reaction_role(message_id: int, emoji: str) -> int | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT role_id FROM reaction_roles WHERE message_id = ? AND emoji = ?", (message_id, emoji))
        row = await cursor.fetchone()
        return row[0] if row else None


# ==================== AUTOMOD ====================

async def get_automod_config(guild_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM automod_config WHERE guild_id = ?", (guild_id,))
        row = await cursor.fetchone()
        if row is None:
            await db.execute("INSERT INTO automod_config (guild_id) VALUES (?)", (guild_id,))
            await db.commit()
            cursor = await db.execute("SELECT * FROM automod_config WHERE guild_id = ?", (guild_id,))
            row = await cursor.fetchone()
        return dict(row)


async def update_automod_config(guild_id: int, **kwargs):
    if not kwargs:
        return
    await get_automod_config(guild_id)
    columns = ", ".join(f"{key} = ?" for key in kwargs.keys())
    values = list(kwargs.values())
    values.append(guild_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE automod_config SET {columns} WHERE guild_id = ?", values)
        await db.commit()


# ==================== CUSTOM COMMANDS ====================

async def add_custom_command(guild_id: int, trigger: str, response: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO custom_commands (guild_id, trigger, response) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, trigger) DO UPDATE SET response = excluded.response",
            (guild_id, trigger.lower(), response)
        )
        await db.commit()


async def remove_custom_command(guild_id: int, trigger: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM custom_commands WHERE guild_id = ? AND trigger = ?", (guild_id, trigger.lower())
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_custom_command(guild_id: int, trigger: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT response FROM custom_commands WHERE guild_id = ? AND trigger = ?", (guild_id, trigger.lower())
        )
        row = await cursor.fetchone()
        return row[0] if row else None


async def list_custom_commands(guild_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM custom_commands WHERE guild_id = ? ORDER BY trigger ASC", (guild_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ==================== REMINDERS ====================

async def add_reminder(user_id: int, channel_id: int, guild_id: int, remind_at: str, message: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO reminders (user_id, channel_id, guild_id, remind_at, message) VALUES (?, ?, ?, ?, ?)",
            (user_id, channel_id, guild_id, remind_at, message)
        )
        await db.commit()
        return cursor.lastrowid


async def get_due_reminders(now_iso: str) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM reminders WHERE remind_at <= ?", (now_iso,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def delete_reminder(reminder_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        await db.commit()


# ==================== ECONOMY ====================

async def get_balance_data(guild_id: int, user_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM economy WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        row = await cursor.fetchone()
        if row is None:
            await db.execute("INSERT INTO economy (guild_id, user_id, balance) VALUES (?, ?, 0)", (guild_id, user_id))
            await db.commit()
            return {"guild_id": guild_id, "user_id": user_id, "balance": 0, "last_daily": None, "last_work": None}
        return dict(row)


async def update_balance(guild_id: int, user_id: int, new_balance: int):
    await get_balance_data(guild_id, user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE economy SET balance = ? WHERE guild_id = ? AND user_id = ?", (new_balance, guild_id, user_id)
        )
        await db.commit()


async def set_last_daily(guild_id: int, user_id: int, timestamp: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE economy SET last_daily = ? WHERE guild_id = ? AND user_id = ?", (timestamp, guild_id, user_id))
        await db.commit()


async def set_last_work(guild_id: int, user_id: int, timestamp: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE economy SET last_work = ? WHERE guild_id = ? AND user_id = ?", (timestamp, guild_id, user_id))
        await db.commit()


async def get_economy_leaderboard(guild_id: int, limit: int = 10) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM economy WHERE guild_id = ? ORDER BY balance DESC LIMIT ?", (guild_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def add_shop_item(guild_id: int, item_name: str, price: int, role_id: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO shop_items (guild_id, item_name, price, role_id) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(guild_id, item_name) DO UPDATE SET price = excluded.price, role_id = excluded.role_id",
            (guild_id, item_name.lower(), price, role_id)
        )
        await db.commit()


async def get_shop_items(guild_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM shop_items WHERE guild_id = ? ORDER BY price ASC", (guild_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_shop_item(guild_id: int, item_name: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM shop_items WHERE guild_id = ? AND item_name = ?", (guild_id, item_name.lower())
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def remove_shop_item(guild_id: int, item_name: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM shop_items WHERE guild_id = ? AND item_name = ?", (guild_id, item_name.lower())
        )
        await db.commit()
        return cursor.rowcount > 0


# ==================== SOCIAL ALERTS ====================

async def add_youtube_alert(guild_id: int, channel_id: int, yt_channel_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO youtube_alerts (guild_id, channel_id, yt_channel_id) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, yt_channel_id) DO UPDATE SET channel_id = excluded.channel_id",
            (guild_id, channel_id, yt_channel_id)
        )
        await db.commit()


async def get_youtube_alerts() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM youtube_alerts")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def update_youtube_last_video(alert_id: int, video_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE youtube_alerts SET last_video_id = ? WHERE id = ?", (video_id, alert_id))
        await db.commit()


async def remove_youtube_alert(guild_id: int, yt_channel_id: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM youtube_alerts WHERE guild_id = ? AND yt_channel_id = ?", (guild_id, yt_channel_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def add_twitch_alert(guild_id: int, channel_id: int, twitch_username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO twitch_alerts (guild_id, channel_id, twitch_username) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, twitch_username) DO UPDATE SET channel_id = excluded.channel_id",
            (guild_id, channel_id, twitch_username.lower())
        )
        await db.commit()


async def get_twitch_alerts() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM twitch_alerts")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def update_twitch_live_state(alert_id: int, is_live: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE twitch_alerts SET is_live = ? WHERE id = ?", (int(is_live), alert_id))
        await db.commit()


async def remove_twitch_alert(guild_id: int, twitch_username: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM twitch_alerts WHERE guild_id = ? AND twitch_username = ?", (guild_id, twitch_username.lower())
        )
        await db.commit()
        return cursor.rowcount > 0


# ==================== COMMAND PERMISSIONS (ROLE RESTRICTIONS) ====================

async def add_command_restriction(guild_id: int, command_name: str, role_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO command_permissions (guild_id, command_name, role_id) VALUES (?, ?, ?)",
            (guild_id, command_name.lower(), role_id)
        )
        await db.commit()


async def remove_command_restriction(guild_id: int, command_name: str, role_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM command_permissions WHERE guild_id = ? AND command_name = ? AND role_id = ?",
            (guild_id, command_name.lower(), role_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def clear_command_restrictions(guild_id: int, command_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM command_permissions WHERE guild_id = ? AND command_name = ?", (guild_id, command_name.lower())
        )
        await db.commit()


async def get_command_restrictions(guild_id: int, command_name: str) -> list:
    """Return the list of role IDs allowed to use this command. Empty list = no restriction configured."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT role_id FROM command_permissions WHERE guild_id = ? AND command_name = ?",
            (guild_id, command_name.lower())
        )
        rows = await cursor.fetchall()
        return [r[0] for r in rows]


async def get_all_command_restrictions(guild_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM command_permissions WHERE guild_id = ? ORDER BY command_name ASC", (guild_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ==================== ROBLOX VERIFICATION ====================

async def add_roblox_verification(guild_id: int, user_id: int, roblox_id: int, roblox_username: str, verified_at: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO roblox_verifications (guild_id, user_id, roblox_id, roblox_username, verified_at) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT(guild_id, user_id) DO UPDATE SET "
            "roblox_id = excluded.roblox_id, roblox_username = excluded.roblox_username, verified_at = excluded.verified_at",
            (guild_id, user_id, roblox_id, roblox_username, verified_at)
        )
        await db.commit()


async def get_roblox_verification(guild_id: int, user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM roblox_verifications WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def remove_roblox_verification(guild_id: int, user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM roblox_verifications WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
        )
        await db.commit()
        return cursor.rowcount > 0


# ==================== AWARDS ====================

async def add_award(guild_id: int, user_id: int, awarded_by: int, title: str, reason: str, timestamp: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO awards (guild_id, user_id, awarded_by, title, reason, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (guild_id, user_id, awarded_by, title, reason, timestamp)
        )
        await db.commit()
        return cursor.lastrowid


async def get_awards(guild_id: int, user_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM awards WHERE guild_id = ? AND user_id = ? ORDER BY id DESC", (guild_id, user_id)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ==================== LEAVE OF ABSENCE ====================

async def add_loa_request(guild_id: int, user_id: int, start_date: str, end_date: str, reason: str, requested_at: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO loa_requests (guild_id, user_id, start_date, end_date, reason, requested_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (guild_id, user_id, start_date, end_date, reason, requested_at)
        )
        await db.commit()
        return cursor.lastrowid


async def set_loa_status(loa_id: int, status: str, reviewed_by: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE loa_requests SET status = ?, reviewed_by = ? WHERE id = ?", (status, reviewed_by, loa_id)
        )
        await db.commit()


async def get_loa_request(loa_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM loa_requests WHERE id = ?", (loa_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_active_loas(guild_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM loa_requests WHERE guild_id = ? AND status = 'approved' ORDER BY start_date ASC", (guild_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ==================== RANK HIERARCHY ====================

async def add_rank(guild_id: int, rank_name: str, role_id: int, rank_order: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO ranks (guild_id, rank_name, role_id, rank_order) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(guild_id, rank_name) DO UPDATE SET role_id = excluded.role_id, rank_order = excluded.rank_order",
            (guild_id, rank_name, role_id, rank_order)
        )
        await db.commit()


async def get_ranks(guild_id: int) -> list:
    """Return all configured ranks ordered from lowest to highest."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM ranks WHERE guild_id = ? ORDER BY rank_order ASC", (guild_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def remove_rank(guild_id: int, rank_name: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM ranks WHERE guild_id = ? AND rank_name = ?", (guild_id, rank_name))
        await db.commit()
        return cursor.rowcount > 0


# ==================== DIVISIONS ====================

async def add_division(guild_id: int, division_name: str, role_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO divisions (guild_id, division_name, role_id) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, division_name) DO UPDATE SET role_id = excluded.role_id",
            (guild_id, division_name, role_id)
        )
        await db.commit()


async def get_divisions(guild_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM divisions WHERE guild_id = ? ORDER BY division_name ASC", (guild_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def remove_division(guild_id: int, division_name: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM divisions WHERE guild_id = ? AND division_name = ?", (guild_id, division_name))
        await db.commit()
        return cursor.rowcount > 0


# ==================== DISCHARGES / DESERTIONS ====================

async def add_discharge(guild_id: int, user_id: int, discharged_by: int | None, reason: str, is_desertion: bool, timestamp: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO discharges (guild_id, user_id, discharged_by, reason, is_desertion, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (guild_id, user_id, discharged_by, reason, int(is_desertion), timestamp)
        )
        await db.commit()
        return cursor.lastrowid


async def get_discharges(guild_id: int, user_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM discharges WHERE guild_id = ? AND user_id = ? ORDER BY id DESC", (guild_id, user_id)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_recent_desertions(guild_id: int, limit: int = 10) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM discharges WHERE guild_id = ? AND is_desertion = 1 ORDER BY id DESC LIMIT ?",
            (guild_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ==================== EVENTS ====================

async def create_event(guild_id: int, name: str, description: str, host_id: int, event_time: str, channel_id: int, created_at: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO events (guild_id, name, description, host_id, event_time, channel_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (guild_id, name, description, host_id, event_time, channel_id, created_at)
        )
        await db.commit()
        return cursor.lastrowid


async def set_event_message(event_id: int, message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE events SET message_id = ? WHERE id = ?", (message_id, event_id))
        await db.commit()


async def get_event(event_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_upcoming_events(guild_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM events WHERE guild_id = ? AND status = 'scheduled' ORDER BY id DESC", (guild_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def set_rsvp(event_id: int, user_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO event_rsvps (event_id, user_id, status) VALUES (?, ?, ?) "
            "ON CONFLICT(event_id, user_id) DO UPDATE SET status = excluded.status",
            (event_id, user_id, status)
        )
        await db.commit()


async def get_rsvps(event_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM event_rsvps WHERE event_id = ?", (event_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ==================== AUDIT LOG ====================

async def add_audit_entry(guild_id: int, user_id: int, command_name: str, timestamp: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO audit_log (guild_id, user_id, command_name, timestamp) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, command_name, timestamp)
        )
        await db.commit()


async def get_recent_audit_entries(guild_id: int, limit: int = 15) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM audit_log WHERE guild_id = ? ORDER BY id DESC LIMIT ?", (guild_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ==================== HONEYPOT ====================

async def get_honeypot_config(guild_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM honeypot_config WHERE guild_id = ?", (guild_id,))
        row = await cursor.fetchone()
        if row is None:
            await db.execute("INSERT INTO honeypot_config (guild_id) VALUES (?)", (guild_id,))
            await db.commit()
            cursor = await db.execute("SELECT * FROM honeypot_config WHERE guild_id = ?", (guild_id,))
            row = await cursor.fetchone()
        return dict(row)


async def set_honeypot_channel(guild_id: int, channel_id: int):
    await get_honeypot_config(guild_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE honeypot_config SET channel_id = ? WHERE guild_id = ?", (channel_id, guild_id))
        await db.commit()


# ==================== INVENTORY / BOUNTIES ====================

async def add_inventory_item(guild_id: int, user_id: int, item_name: str, qty: int = 1):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO inventory (guild_id, user_id, item_name, quantity) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(guild_id, user_id, item_name) DO UPDATE SET quantity = quantity + excluded.quantity",
            (guild_id, user_id, item_name.lower(), qty)
        )
        await db.commit()


async def get_inventory(guild_id: int, user_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM inventory WHERE guild_id = ? AND user_id = ? AND quantity > 0", (guild_id, user_id)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def add_bounty(guild_id: int, target_id: int, amount: int, placed_by: int, timestamp: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO bounties (guild_id, target_id, amount, placed_by, created_at) VALUES (?, ?, ?, ?, ?)",
            (guild_id, target_id, amount, placed_by, timestamp)
        )
        await db.commit()
        return cursor.lastrowid


async def get_open_bounties(guild_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM bounties WHERE guild_id = ? AND status = 'open' ORDER BY amount DESC", (guild_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def claim_bounty(bounty_id: int, claimed_by: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE bounties SET status = 'claimed', claimed_by = ? WHERE id = ? AND status = 'open'",
            (claimed_by, bounty_id)
        )
        await db.commit()
        return cursor.rowcount > 0


# ==================== GIVEAWAYS ====================

async def create_giveaway(guild_id: int, channel_id: int, prize: str, winner_count: int, ends_at: str, host_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO giveaways (guild_id, channel_id, prize, winner_count, ends_at, host_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (guild_id, channel_id, prize, winner_count, ends_at, host_id)
        )
        await db.commit()
        return cursor.lastrowid


async def set_giveaway_message(giveaway_id: int, message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE giveaways SET message_id = ? WHERE id = ?", (message_id, giveaway_id))
        await db.commit()


async def get_giveaway(giveaway_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM giveaways WHERE id = ?", (giveaway_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_giveaway_by_message(message_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM giveaways WHERE message_id = ?", (message_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_due_giveaways(now_iso: str) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM giveaways WHERE status = 'running' AND ends_at <= ?", (now_iso,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def add_giveaway_entry(giveaway_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO giveaway_entries (giveaway_id, user_id) VALUES (?, ?)",
            (giveaway_id, user_id)
        )
        await db.commit()


async def get_giveaway_entries(giveaway_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM giveaway_entries WHERE giveaway_id = ?", (giveaway_id,))
        rows = await cursor.fetchall()
        return [r[0] for r in rows]


async def finish_giveaway(giveaway_id: int, winners: list[int]):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE giveaways SET status = 'ended', last_winners = ? WHERE id = ?",
            (",".join(str(w) for w in winners), giveaway_id)
        )
        await db.commit()


# ==================== AFK ====================

async def set_afk(guild_id: int, user_id: int, reason: str, since: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO afk_status (guild_id, user_id, reason, since) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET reason = excluded.reason, since = excluded.since",
            (guild_id, user_id, reason, since)
        )
        await db.commit()


async def get_afk(guild_id: int, user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM afk_status WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def clear_afk(guild_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM afk_status WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        await db.commit()


# ==================== STARBOARD ====================

async def get_starboard_config(guild_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM starboard_config WHERE guild_id = ?", (guild_id,))
        row = await cursor.fetchone()
        if row is None:
            await db.execute("INSERT INTO starboard_config (guild_id) VALUES (?)", (guild_id,))
            await db.commit()
            cursor = await db.execute("SELECT * FROM starboard_config WHERE guild_id = ?", (guild_id,))
            row = await cursor.fetchone()
        return dict(row)


async def update_starboard_config(guild_id: int, **kwargs):
    await get_starboard_config(guild_id)
    columns = ", ".join(f"{k} = ?" for k in kwargs.keys())
    values = list(kwargs.values())
    values.append(guild_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE starboard_config SET {columns} WHERE guild_id = ?", values)
        await db.commit()


async def get_starboard_post(original_message_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM starboard_posts WHERE original_message_id = ?", (original_message_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def add_starboard_post(original_message_id: int, guild_id: int, board_message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO starboard_posts (original_message_id, guild_id, board_message_id) VALUES (?, ?, ?)",
            (original_message_id, guild_id, board_message_id)
        )
        await db.commit()


# ==================== BIRTHDAYS ====================

async def set_birthday(guild_id: int, user_id: int, month: int, day: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO birthdays (guild_id, user_id, month, day) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET month = excluded.month, day = excluded.day",
            (guild_id, user_id, month, day)
        )
        await db.commit()


async def get_birthdays_on(guild_id: int, month: int, day: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT user_id FROM birthdays WHERE guild_id = ? AND month = ? AND day = ?", (guild_id, month, day)
        )
        rows = await cursor.fetchall()
        return [r[0] for r in rows]


async def get_all_birthdays(guild_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM birthdays WHERE guild_id = ? ORDER BY month ASC, day ASC", (guild_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ==================== INVITES ====================

async def upsert_invite_use(guild_id: int, invite_code: str, inviter_id: int | None, uses: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO invite_uses (guild_id, invite_code, inviter_id, uses) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(guild_id, invite_code) DO UPDATE SET uses = excluded.uses, inviter_id = excluded.inviter_id",
            (guild_id, invite_code, inviter_id, uses)
        )
        await db.commit()


async def get_invite_uses(guild_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM invite_uses WHERE guild_id = ?", (guild_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def record_join_via(guild_id: int, user_id: int, invite_code: str | None, inviter_id: int | None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO joined_via (guild_id, user_id, invite_code, inviter_id) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET invite_code = excluded.invite_code, inviter_id = excluded.inviter_id",
            (guild_id, user_id, invite_code, inviter_id)
        )
        await db.commit()


async def get_inviter_leaderboard(guild_id: int, limit: int = 10) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT inviter_id, SUM(uses) as total FROM invite_uses WHERE guild_id = ? "
            "GROUP BY inviter_id ORDER BY total DESC LIMIT ?",
            (guild_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ==================== SUGGESTIONS ====================

async def get_suggestions_config(guild_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM suggestions_config WHERE guild_id = ?", (guild_id,))
        row = await cursor.fetchone()
        if row is None:
            await db.execute("INSERT INTO suggestions_config (guild_id) VALUES (?)", (guild_id,))
            await db.commit()
            cursor = await db.execute("SELECT * FROM suggestions_config WHERE guild_id = ?", (guild_id,))
            row = await cursor.fetchone()
        return dict(row)


async def set_suggestions_channel(guild_id: int, channel_id: int):
    await get_suggestions_config(guild_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE suggestions_config SET channel_id = ? WHERE guild_id = ?", (channel_id, guild_id))
        await db.commit()


async def add_suggestion(guild_id: int, user_id: int, channel_id: int, content: str, timestamp: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO suggestions (guild_id, user_id, channel_id, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (guild_id, user_id, channel_id, content, timestamp)
        )
        await db.commit()
        return cursor.lastrowid


async def set_suggestion_message(suggestion_id: int, message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE suggestions SET message_id = ? WHERE id = ?", (message_id, suggestion_id))
        await db.commit()


async def set_suggestion_status(suggestion_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE suggestions SET status = ? WHERE id = ?", (status, suggestion_id))
        await db.commit()


async def get_suggestion(suggestion_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM suggestions WHERE id = ?", (suggestion_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


# ==================== DUTY / INSPECTIONS / PATROLS / APPLICATIONS ====================

async def clock_in(guild_id: int, user_id: int, timestamp: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO duty_sessions (guild_id, user_id, clock_in) VALUES (?, ?, ?)",
            (guild_id, user_id, timestamp)
        )
        await db.commit()
        return cursor.lastrowid


async def get_open_duty_session(guild_id: int, user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM duty_sessions WHERE guild_id = ? AND user_id = ? AND clock_out IS NULL "
            "ORDER BY id DESC LIMIT 1",
            (guild_id, user_id)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def clock_out(session_id: int, timestamp: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE duty_sessions SET clock_out = ? WHERE id = ?", (timestamp, session_id))
        await db.commit()


async def get_duty_hours(guild_id: int, user_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM duty_sessions WHERE guild_id = ? AND user_id = ? AND clock_out IS NOT NULL",
            (guild_id, user_id)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def add_inspection(guild_id: int, user_id: int, inspector_id: int, result: str, notes: str, timestamp: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO inspections (guild_id, user_id, inspector_id, result, notes, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (guild_id, user_id, inspector_id, result, notes, timestamp)
        )
        await db.commit()
        return cursor.lastrowid


async def add_patrol_log(guild_id: int, user_id: int, route: str, incidents: str, duration_minutes: int, timestamp: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO patrol_logs (guild_id, user_id, route, incidents, duration_minutes, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (guild_id, user_id, route, incidents, duration_minutes, timestamp)
        )
        await db.commit()
        return cursor.lastrowid


async def get_applications_config(guild_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM applications_config WHERE guild_id = ?", (guild_id,))
        row = await cursor.fetchone()
        if row is None:
            await db.execute("INSERT INTO applications_config (guild_id) VALUES (?)", (guild_id,))
            await db.commit()
            cursor = await db.execute("SELECT * FROM applications_config WHERE guild_id = ?", (guild_id,))
            row = await cursor.fetchone()
        return dict(row)


async def set_applications_channel(guild_id: int, channel_id: int):
    await get_applications_config(guild_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE applications_config SET review_channel_id = ? WHERE guild_id = ?", (channel_id, guild_id))
        await db.commit()


async def add_application(guild_id: int, user_id: int, answers: str, timestamp: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO applications (guild_id, user_id, answers, created_at) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, answers, timestamp)
        )
        await db.commit()
        return cursor.lastrowid


async def set_application_message(application_id: int, channel_id: int, message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE applications SET channel_id = ?, message_id = ? WHERE id = ?",
            (channel_id, message_id, application_id)
        )
        await db.commit()


async def set_application_status(application_id: int, status: str, reviewed_by: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE applications SET status = ?, reviewed_by = ? WHERE id = ?",
            (status, reviewed_by, application_id)
        )
        await db.commit()


async def get_application(application_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM applications WHERE id = ?", (application_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


# ==================== LOCKDOWN ====================

async def get_lockdown_state(guild_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM lockdown_state WHERE guild_id = ?", (guild_id,))
        row = await cursor.fetchone()
        if row is None:
            await db.execute("INSERT INTO lockdown_state (guild_id) VALUES (?)", (guild_id,))
            await db.commit()
            cursor = await db.execute("SELECT * FROM lockdown_state WHERE guild_id = ?", (guild_id,))
            row = await cursor.fetchone()
        return dict(row)


async def set_lockdown_state(guild_id: int, is_locked: bool, locked_channels: str = "", previous_verification_level: str = ""):
    await get_lockdown_state(guild_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE lockdown_state SET is_locked = ?, locked_channels = ?, previous_verification_level = ? WHERE guild_id = ?",
            (int(is_locked), locked_channels, previous_verification_level, guild_id)
        )
        await db.commit()


# ==================== BANK / CRIME / HEISTS ====================

async def get_bank(guild_id: int, user_id: int) -> int:
    row = await get_balance_data(guild_id, user_id)
    return row.get("bank", 0) or 0


async def set_bank(guild_id: int, user_id: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE economy SET bank = ? WHERE guild_id = ? AND user_id = ?", (amount, guild_id, user_id))
        await db.commit()


async def set_last_crime(guild_id: int, user_id: int, timestamp: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE economy SET last_crime = ? WHERE guild_id = ? AND user_id = ?", (timestamp, guild_id, user_id))
        await db.commit()


async def create_heist(guild_id: int, channel_id: int, organizer_id: int, buy_in: int, starts_at: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO heists (guild_id, channel_id, organizer_id, buy_in, starts_at) VALUES (?, ?, ?, ?, ?)",
            (guild_id, channel_id, organizer_id, buy_in, starts_at)
        )
        await db.commit()
        return cursor.lastrowid


async def set_heist_message(heist_id: int, message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE heists SET message_id = ? WHERE id = ?", (message_id, heist_id))
        await db.commit()


async def get_heist(heist_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM heists WHERE id = ?", (heist_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def join_heist(heist_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO heist_participants (heist_id, user_id) VALUES (?, ?)", (heist_id, user_id))
        await db.commit()


async def get_heist_participants(heist_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM heist_participants WHERE heist_id = ?", (heist_id,))
        rows = await cursor.fetchall()
        return [r[0] for r in rows]


async def close_heist(heist_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE heists SET status = ? WHERE id = ?", (status, heist_id))
        await db.commit()


# ==================== QUOTES ====================

async def add_quote(guild_id: int, author_id: int | None, content: str, added_by: int, timestamp: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO quotes (guild_id, author_id, content, added_by, created_at) VALUES (?, ?, ?, ?, ?)",
            (guild_id, author_id, content, added_by, timestamp)
        )
        await db.commit()
        return cursor.lastrowid


async def get_random_quote(guild_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM quotes WHERE guild_id = ? ORDER BY RANDOM() LIMIT 1", (guild_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_all_quotes(guild_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM quotes WHERE guild_id = ? ORDER BY id DESC", (guild_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def delete_quote(guild_id: int, quote_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM quotes WHERE guild_id = ? AND id = ?", (guild_id, quote_id))
        await db.commit()
        return cursor.rowcount > 0


# ==================== WORD FILTER ====================

async def add_blacklisted_word(guild_id: int, word: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO blacklisted_words (guild_id, word) VALUES (?, ?)", (guild_id, word.lower()))
        await db.commit()


async def remove_blacklisted_word(guild_id: int, word: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM blacklisted_words WHERE guild_id = ? AND word = ?", (guild_id, word.lower()))
        await db.commit()
        return cursor.rowcount > 0


async def get_blacklisted_words(guild_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT word FROM blacklisted_words WHERE guild_id = ?", (guild_id,))
        rows = await cursor.fetchall()
        return [r[0] for r in rows]


# ==================== VOICE / MESSAGE ACTIVITY ====================

async def start_voice_session(guild_id: int, user_id: int, timestamp: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO voice_time (guild_id, user_id, session_start) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET session_start = excluded.session_start",
            (guild_id, user_id, timestamp)
        )
        await db.commit()


async def end_voice_session(guild_id: int, user_id: int, elapsed_seconds: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE voice_time SET seconds = seconds + ?, session_start = NULL WHERE guild_id = ? AND user_id = ?",
            (elapsed_seconds, guild_id, user_id)
        )
        await db.commit()


async def get_voice_session_start(guild_id: int, user_id: int) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT session_start FROM voice_time WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        row = await cursor.fetchone()
        return row[0] if row else None


async def get_voice_leaderboard(guild_id: int, limit: int = 10) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM voice_time WHERE guild_id = ? ORDER BY seconds DESC LIMIT ?", (guild_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def increment_message_count(guild_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO message_counts (guild_id, user_id, count) VALUES (?, ?, 1) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET count = count + 1",
            (guild_id, user_id)
        )
        await db.commit()


async def get_message_leaderboard(guild_id: int, limit: int = 10) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM message_counts WHERE guild_id = ? ORDER BY count DESC LIMIT ?", (guild_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ==================== VERIFICATION ====================

async def get_verification_config(guild_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM verification_config WHERE guild_id = ?", (guild_id,))
        row = await cursor.fetchone()
        if row is None:
            await db.execute("INSERT INTO verification_config (guild_id) VALUES (?)", (guild_id,))
            await db.commit()
            cursor = await db.execute("SELECT * FROM verification_config WHERE guild_id = ?", (guild_id,))
            row = await cursor.fetchone()
        return dict(row)


async def set_verification_config(guild_id: int, channel_id: int, verified_role_id: int):
    await get_verification_config(guild_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE verification_config SET channel_id = ?, verified_role_id = ? WHERE guild_id = ?",
            (channel_id, verified_role_id, guild_id)
        )
        await db.commit()


# ==================== TEMP ROLES / TAGS / SELF-ROLES ====================

async def add_temprole(guild_id: int, user_id: int, role_id: int, expires_at: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO temp_roles (guild_id, user_id, role_id, expires_at) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, role_id, expires_at)
        )
        await db.commit()
        return cursor.lastrowid


async def get_due_temproles(now_iso: str) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM temp_roles WHERE expires_at <= ?", (now_iso,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def remove_temprole_row(row_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM temp_roles WHERE id = ?", (row_id,))
        await db.commit()


async def add_tag(guild_id: int, name: str, content: str, created_by: int, timestamp: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO tags (guild_id, name, content, created_by, created_at) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(guild_id, name) DO UPDATE SET content = excluded.content",
            (guild_id, name.lower(), content, created_by, timestamp)
        )
        await db.commit()


async def get_tag(guild_id: int, name: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM tags WHERE guild_id = ? AND name = ?", (guild_id, name.lower()))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def delete_tag(guild_id: int, name: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM tags WHERE guild_id = ? AND name = ?", (guild_id, name.lower()))
        await db.commit()
        return cursor.rowcount > 0


async def get_all_tags(guild_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT name FROM tags WHERE guild_id = ?", (guild_id,))
        rows = await cursor.fetchall()
        return [r[0] for r in rows]


async def add_selfrole(guild_id: int, role_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO selfroles (guild_id, role_id) VALUES (?, ?)", (guild_id, role_id))
        await db.commit()


async def remove_selfrole(guild_id: int, role_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM selfroles WHERE guild_id = ? AND role_id = ?", (guild_id, role_id))
        await db.commit()
        return cursor.rowcount > 0


async def get_selfroles(guild_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT role_id FROM selfroles WHERE guild_id = ?", (guild_id,))
        rows = await cursor.fetchall()
        return [r[0] for r in rows]


# ==================== BAN APPEALS ====================

async def add_appeal(guild_id: int, user_id: int, reason: str, timestamp: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO appeals (guild_id, user_id, reason, created_at) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, reason, timestamp)
        )
        await db.commit()
        return cursor.lastrowid


async def set_appeal_message(appeal_id: int, channel_id: int, message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE appeals SET channel_id = ?, message_id = ? WHERE id = ?", (channel_id, message_id, appeal_id))
        await db.commit()


async def get_appeal(appeal_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM appeals WHERE id = ?", (appeal_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def set_appeal_status(appeal_id: int, status: str, reviewed_by: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE appeals SET status = ?, reviewed_by = ? WHERE id = ?", (status, reviewed_by, appeal_id))
        await db.commit()


async def get_appeals_config(guild_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM appeals_config WHERE guild_id = ?", (guild_id,))
        row = await cursor.fetchone()
        if row is None:
            await db.execute("INSERT INTO appeals_config (guild_id) VALUES (?)", (guild_id,))
            await db.commit()
            cursor = await db.execute("SELECT * FROM appeals_config WHERE guild_id = ?", (guild_id,))
            row = await cursor.fetchone()
        return dict(row)


async def set_appeals_channel(guild_id: int, channel_id: int):
    await get_appeals_config(guild_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE appeals_config SET channel_id = ? WHERE guild_id = ?", (channel_id, guild_id))
        await db.commit()


# ==================== LOTTERY ====================

async def buy_lottery_ticket(guild_id: int, user_id: int, timestamp: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO lottery_tickets (guild_id, user_id, purchased_at) VALUES (?, ?, ?)",
            (guild_id, user_id, timestamp)
        )
        await db.commit()


async def get_lottery_tickets(guild_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM lottery_tickets WHERE guild_id = ?", (guild_id,))
        rows = await cursor.fetchall()
        return [r[0] for r in rows]


async def clear_lottery_tickets(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM lottery_tickets WHERE guild_id = ?", (guild_id,))
        await db.commit()


# ==================== PETS ====================

async def get_pet(guild_id: int, user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM pets WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def adopt_pet(guild_id: int, user_id: int, name: str, species: str, timestamp: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO pets (guild_id, user_id, name, species, hunger, happiness, adopted_at) VALUES (?, ?, ?, ?, 50, 50, ?)",
            (guild_id, user_id, name, species, timestamp)
        )
        await db.commit()


async def update_pet_stats(guild_id: int, user_id: int, hunger: int, happiness: int):
    hunger = max(0, min(100, hunger))
    happiness = max(0, min(100, happiness))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE pets SET hunger = ?, happiness = ? WHERE guild_id = ? AND user_id = ?",
            (hunger, happiness, guild_id, user_id)
        )
        await db.commit()


async def release_pet(guild_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM pets WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        await db.commit()


# ==================== MARRIAGE ====================

async def get_marriage(guild_id: int, user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM marriages WHERE guild_id = ? AND (user1_id = ? OR user2_id = ?)",
            (guild_id, user_id, user_id)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def create_marriage(guild_id: int, user1_id: int, user2_id: int, timestamp: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO marriages (guild_id, user1_id, user2_id, married_at) VALUES (?, ?, ?, ?)",
            (guild_id, user1_id, user2_id, timestamp)
        )
        await db.commit()


async def end_marriage(guild_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM marriages WHERE guild_id = ? AND (user1_id = ? OR user2_id = ?)",
            (guild_id, user_id, user_id)
        )
        await db.commit()


# ==================== REPUTATION ====================

async def add_reputation(guild_id: int, user_id: int, from_user_id: int, timestamp: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO reputation_log (guild_id, user_id, from_user_id, given_at) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, from_user_id, timestamp)
        )
        await db.commit()


async def get_reputation_count(guild_id: int, user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM reputation_log WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


async def has_given_rep_today(guild_id: int, from_user_id: int, today_date: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM reputation_log WHERE guild_id = ? AND from_user_id = ? AND given_at LIKE ?",
            (guild_id, from_user_id, f"{today_date}%")
        )
        row = await cursor.fetchone()
        return row[0] > 0


async def get_reputation_leaderboard(guild_id: int, limit: int = 10) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT user_id, COUNT(*) as total FROM reputation_log WHERE guild_id = ? GROUP BY user_id ORDER BY total DESC LIMIT ?",
            (guild_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ==================== CONFESSIONS ====================

async def get_confessions_config(guild_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM confessions_config WHERE guild_id = ?", (guild_id,))
        row = await cursor.fetchone()
        if row is None:
            await db.execute("INSERT INTO confessions_config (guild_id) VALUES (?)", (guild_id,))
            await db.commit()
            cursor = await db.execute("SELECT * FROM confessions_config WHERE guild_id = ?", (guild_id,))
            row = await cursor.fetchone()
        return dict(row)


async def set_confessions_channel(guild_id: int, channel_id: int):
    await get_confessions_config(guild_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE confessions_config SET channel_id = ? WHERE guild_id = ?", (channel_id, guild_id))
        await db.commit()


async def next_confession_number(guild_id: int) -> int:
    config = await get_confessions_config(guild_id)
    next_num = (config["counter"] or 0) + 1
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE confessions_config SET counter = ? WHERE guild_id = ?", (next_num, guild_id))
        await db.commit()
    return next_num


# ==================== AUTORESPONDER ====================

async def add_autoresponder(guild_id: int, trigger: str, response: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO autoresponders (guild_id, trigger, response) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, trigger) DO UPDATE SET response = excluded.response",
            (guild_id, trigger.lower(), response)
        )
        await db.commit()


async def remove_autoresponder(guild_id: int, trigger: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM autoresponders WHERE guild_id = ? AND trigger = ?", (guild_id, trigger.lower())
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_autoresponders(guild_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM autoresponders WHERE guild_id = ?", (guild_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ==================== XP ADMIN ====================

async def set_xp(guild_id: int, user_id: int, xp: int, level: int):
    await get_level_data(guild_id, user_id)  # ensure row exists
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE levels SET xp = ?, level = ? WHERE guild_id = ? AND user_id = ?",
            (xp, level, guild_id, user_id)
        )
        await db.commit()


# ==================== MODMAIL ====================

async def get_modmail_config(guild_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM modmail_config WHERE guild_id = ?", (guild_id,))
        row = await cursor.fetchone()
        if row is None:
            await db.execute("INSERT INTO modmail_config (guild_id) VALUES (?)", (guild_id,))
            await db.commit()
            cursor = await db.execute("SELECT * FROM modmail_config WHERE guild_id = ?", (guild_id,))
            row = await cursor.fetchone()
        return dict(row)


async def set_modmail_config(guild_id: int, category_id: int, log_channel_id: int):
    await get_modmail_config(guild_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE modmail_config SET category_id = ?, log_channel_id = ? WHERE guild_id = ?",
            (category_id, log_channel_id, guild_id)
        )
        await db.commit()


async def create_modmail_thread(guild_id: int, user_id: int, channel_id: int, timestamp: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO modmail_threads (guild_id, user_id, channel_id, status, created_at) VALUES (?, ?, ?, 'open', ?)",
            (guild_id, user_id, channel_id, timestamp)
        )
        await db.commit()
        return cursor.lastrowid


async def get_open_modmail_thread(guild_id: int, user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM modmail_threads WHERE guild_id = ? AND user_id = ? AND status = 'open'",
            (guild_id, user_id)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_modmail_thread_by_channel(channel_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM modmail_threads WHERE channel_id = ?", (channel_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def close_modmail_thread(channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE modmail_threads SET status = 'closed' WHERE channel_id = ?", (channel_id,))
        await db.commit()


async def find_modmail_thread_for_user_any_guild(user_id: int) -> list:
    """A user might DM the bot while having open threads in multiple mutual guilds."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM modmail_threads WHERE user_id = ? AND status = 'open'", (user_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
