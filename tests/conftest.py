import pytest
from httpx import AsyncClient, ASGITransport

import database
import main as main_module
from main import app


@pytest.fixture(autouse=True)
async def isolated_db(tmp_path, monkeypatch):
    """Patch DB to a temp directory and reset global state between tests."""
    monkeypatch.setattr(database, "DB_DIR", tmp_path)
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(main_module, "current_index", 0)
    await database.init_db()


@pytest.fixture
def image_dir(tmp_path):
    """Create a temporary directory with dummy image files."""
    img_dir = tmp_path / "images"
    img_dir.mkdir()
    for name in ["img1.jpg", "img2.png", "img3.jpeg"]:
        (img_dir / name).write_bytes(b"fake-image-data")
    return img_dir


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest.fixture
async def client_with_images(client, image_dir):
    """Client with images already scanned."""
    await client.post("/scan", json={"directory": str(image_dir)})
    yield client
