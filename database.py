import aiosqlite
from pathlib import Path
from datetime import datetime
from typing import Optional
import os

DB_DIR = Path("db")
DB_PATH = DB_DIR / "labels.db"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


async def init_db():
    DB_DIR.mkdir(exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                label TEXT,
                labeled_at DATETIME
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_images_label ON images(label)
        """)
        await db.commit()


async def scan_directory(directory: str) -> int:
    """Scan directory and add images to database. Returns count of new images."""
    dir_path = Path(directory)
    if not dir_path.exists() or not dir_path.is_dir():
        raise ValueError(f"Directory not found: {directory}")

    count = 0
    async with aiosqlite.connect(DB_PATH) as db:
        for file_path in dir_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in ALLOWED_EXTENSIONS:
                try:
                    await db.execute(
                        "INSERT OR IGNORE INTO images (path, filename) VALUES (?, ?)",
                        (str(file_path.absolute()), file_path.name)
                    )
                    count += 1
                except Exception:
                    pass
        await db.commit()
    return count


async def get_all_images() -> list[dict]:
    """Get all images ordered by id."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM images ORDER BY id") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_unlabeled_images() -> list[dict]:
    """Get only unlabeled images ordered by id."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM images WHERE label IS NULL ORDER BY id"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_image_by_id(image_id: int) -> Optional[dict]:
    """Get single image by id."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM images WHERE id = ?", (image_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def set_label(image_id: int, label: str) -> bool:
    """Set label for an image. Label should be 'OK' or 'NG'."""
    if label not in ("OK", "NG"):
        raise ValueError("Label must be 'OK' or 'NG'")

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE images SET label = ?, labeled_at = ? WHERE id = ?",
            (label, datetime.now().isoformat(), image_id)
        )
        await db.commit()
        return db.total_changes > 0


async def get_stats() -> dict:
    """Get labeling statistics."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM images") as cursor:
            total = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM images WHERE label = 'OK'") as cursor:
            ok_count = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM images WHERE label = 'NG'") as cursor:
            ng_count = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM images WHERE label IS NULL") as cursor:
            unlabeled = (await cursor.fetchone())[0]

    return {
        "total": total,
        "ok": ok_count,
        "ng": ng_count,
        "unlabeled": unlabeled,
        "labeled": ok_count + ng_count
    }


async def clear_all():
    """Clear all images from database."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM images")
        await db.commit()
