import aiosqlite
import asyncio

from .types import User, Points

class BaseTable:
    def __init__(self, db_path = "database.db"):
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
            
    async def addcollumn(self, table: str, collumn: str, type: str):
        await self.execute_commit(f"ALTER TABLE {table} ADD COLUMN {collumn} {type}")

class UsersTable(BaseTable):
    def __init__(self, db_path = "database.db"):
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
        if row is None:
            return None
        print(row)
        return User(**dict(row))

    async def get_users(self):
        row = await self.fetchall(
            """
            SELECT * FROM users
            """
        )
        if row is None:
            return None
        return [User(**dict(i)) for i in row]

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
    def __init__(self, db_path = "database.db"):
        super().__init__(db_path)
        asyncio.run(self.create_table())

    async def create_table(self):
        await self.execute_commit(
            """
            CREATE TABLE IF NOT EXISTS points (
                id INTEGER PRIMARY KEY,
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
        if row is None:
            return None
        return Points(**dict(row))

    async def get_all_points(self):
        row = await self.fetchall(
            """
            SELECT * FROM points
            """
        )
        if row is None:
            return None
        return [Points(**dict(i)) for i in row]

    async def delete_points(self, user_id: int, course: str, timestamp: int):
        await self.execute_commit(
            """
            DELETE FROM points
            WHERE id = ? AND course = ?
            """,
            user_id,
            course
        ) 

    async def get_all_by_user(self, user_id: int):
        row = await self.fetchall(
            """
            SELECT * FROM points
            WHERE id = ?
            """,
            user_id
        )
        if row is None:
            return None
        return [Points(**dict(i)) for i in row]
    
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
        row = await self.fetchall(
            """
            SELECT * FROM points
            WHERE id = ?
            """,
            user_id
        )
        if row is None:
            return None
        points = [Points(**dict(i)) for i in row]
        sorted_by_course = {}
        for point in points:
            if point.course not in sorted_by_course:
                sorted_by_course[point.course] = []
            sorted_by_course[point.course].append(point.count)

        return sorted_by_course