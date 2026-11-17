import os
import asyncio
import aiosqlite as db

from pathlib import Path
from fastmcp import FastMCP

DB_PATH = Path(
    os.getenv("EXPENSES_DB_PATH", "/tmp/expenses.db")
)

CATEGORIES_PATH = Path(__file__).parent / "categories.json"

mcp = FastMCP("ExpenseTracker")


async def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with db.connect(str(DB_PATH)) as c:
        await c.execute("""
            CREATE TABLE IF NOT EXISTS expenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT ''
            )
        """)
        await c.commit()

    print(f"Database initialized at: {DB_PATH}")


@mcp.tool()
async def add_expense(date, amount, category, subcategory="", note=""):
    """Add a new expense entry to the database."""

    async with db.connect(str(DB_PATH)) as c:
        cursor = await c.execute(
            """
            INSERT INTO expenses
            (date, amount, category, subcategory, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (date, amount, category, subcategory, note)
        )

        await c.commit()

        return {"status": "ok", "id": cursor.lastrowid}


@mcp.tool()
async def list_expenses(start_date, end_date):
    """List expense entries within an inclusive date range."""

    async with db.connect(str(DB_PATH)) as c:
        cursor = await c.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (start_date, end_date)
        )

        rows = await cursor.fetchall()
        cols = [d[0] for d in cursor.description]

        return [dict(zip(cols, row)) for row in rows]


@mcp.tool()
async def summarize(start_date, end_date, category=None):
    """Summarize expenses by category within an inclusive date range."""

    async with db.connect(str(DB_PATH)) as c:
        query = """
            SELECT category, SUM(amount) AS total_amount
            FROM expenses
            WHERE date BETWEEN ? AND ?
        """

        params = [start_date, end_date]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " GROUP BY category ORDER BY category ASC"

        cursor = await c.execute(query, params)

        rows = await cursor.fetchall()
        cols = [d[0] for d in cursor.description]

        return [dict(zip(cols, row)) for row in rows]


@mcp.resource("expense://categories", mime_type="application/json")
async def categories():
    """Read expense categories."""

    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    asyncio.run(init_db())

    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8000
    )
