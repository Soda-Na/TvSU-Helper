import aiosqlite
import asyncio
from datetime import datetime

from .types import User, Points

class BaseTable:
    def __init__(self, db_path="database.db"):
        self.db_path = db_path

    async def execute(self, query: str, *args):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, args) as cursor:
                return await cursor.fetchall()

    async def execute_commit(self, query: str, *args):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, args) as cursor:
                await db.commit()
                return await cursor.fetchall()

    async def fetchone(self, query: str, *args):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, args) as cursor:
                return await cursor.fetchone()

    async def fetchall(self, query: str, *args):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, args) as cursor:
                return await cursor.fetchall()

    async def fetchval(self, query: str, *args):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, args) as cursor:
                return await cursor.fetchone()

    async def add_column(self, table: str, column: str, col_type: str):
        await self.execute_commit(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")

class UsersTable(BaseTable):
    def __init__(self, db_path="database.db"):
        super().__init__(db_path)
        asyncio.run(self.create_table())

    async def create_table(self):
        await self.execute_commit(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                "group" TEXT
            )
            """
        )

    async def add_user(self, user: User):
        await self.execute_commit(
            """
            INSERT INTO users (id, "group")
            VALUES (?, ?)
            """,
            user.id,
            user.group
        )

    async def get_user(self, user_id: int):
        row = await self.fetchone(
            """
            SELECT * FROM users
            WHERE id = ?
            """,
            user_id
        )
        return User(**dict(row)) if row else None

    async def get_users(self):
        rows = await self.fetchall(
            """
            SELECT * FROM users
            """
        )
        return [User(**dict(row)) for row in rows] if rows else None

    async def update_group(self, user_id: int, group: str):
        await self.execute_commit(
            """
            UPDATE users
            SET "group" = ?
            WHERE id = ?
            """,
            group,
            user_id
        )

class PointsTable(BaseTable):
    def __init__(self, db_path="database.db"):
        super().__init__(db_path)
        asyncio.run(self.create_table())

    async def create_table(self):
        await self.execute_commit(
            """
            CREATE TABLE IF NOT EXISTS points (
                id INTEGER,
                count INTEGER,
                course TEXT,
                timestamp INTEGER DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
            """
        )

    async def get_points(self, user_id: int, course: str):
        row = await self.fetchone(
            """
            SELECT * FROM points
            WHERE id = ? AND course = ?
            """,
            user_id,
            course
        )
        return Points(**dict(row)) if row else None

    async def get_all_points(self):
        rows = await self.fetchall(
            """
            SELECT * FROM points
            """
        )
        return [Points(**dict(row)) for row in rows] if rows else None

    async def delete_points(self, user_id: int, course: str, timestamp: datetime):
        await self.execute_commit(
            """
            DELETE FROM points
            WHERE id = ? AND course = ? AND timestamp = ?
            """,
            user_id,
            course,
            timestamp
        )

    async def delete_all_points_by_course(self, user_id: int, course: str):
        await self.execute_commit(
            """
            DELETE FROM points
            WHERE id = ? AND course = ?
            """,
            user_id,
            course
        )

    async def get_all_by_user(self, user_id: int):
        rows = await self.fetchall(
            """
            SELECT * FROM points
            WHERE id = ?
            """,
            user_id
        )
        return [Points(**dict(row)) for row in rows] if rows else None
    
    async def get_all_by_course(self, user_id: int, course: str):
        rows = await self.fetchall(
            """
            SELECT * FROM points
            WHERE id = ? AND course = ?
            """,
            user_id,
            course
        )
        return [Points(**dict(row)) for row in rows] if rows else None
    
    async def add_points(self, points: Points):
        await self.execute_commit(
            """
            INSERT INTO points (id, count, course, description)
            VALUES (?, ?, ?, ?)
            """,
            points.id,
            points.count,
            points.course,
            points.description
        )

        row = await self.fetchone(
            """
            SELECT * FROM points
            WHERE id = ? AND course = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            points.id,
            points.course
        )
        
        return Points(**dict(row))
    
    async def edit_description(self, user_id: int, course: str, timestamp: int, description: str):
        await self.execute_commit(
            """
            UPDATE points
            SET description = ?
            WHERE id = ? AND course = ? AND timestamp = ?
            """,
            description,
            user_id,
            course,
            timestamp
        )

    async def get_sorted_points(self, user_id: int) -> dict[str, list[int]]:
        rows = await self.fetchall(
            """
            SELECT * FROM points
            WHERE id = ?
            """,
            user_id
        )
        if not rows:
            return None
        points = [Points(**dict(row)) for row in rows]
        sorted_by_course = {}
        for point in points:
            sorted_by_course.setdefault(point.course, []).append(point.count)
        return sorted_by_course
    
    async def get_point(self, user_id: int, course: str, timestamp: int):
        row = await self.fetchone(
            """
            SELECT * FROM points
            WHERE id = ? AND course = ? AND timestamp = ?
            """,
            user_id,
            course,
            timestamp
        )
        return Points(**dict(row)) if row else None