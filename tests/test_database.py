import pytest
from pathlib import Path

import database as db


# --- scan_directory ---

async def test_scan_counts_new_images(image_dir):
    count = await db.scan_directory(str(image_dir))
    assert count == 3


async def test_scan_ignores_non_image_files(tmp_path):
    (tmp_path / "notes.txt").write_bytes(b"text")
    (tmp_path / "data.csv").write_bytes(b"csv")
    (tmp_path / "photo.jpg").write_bytes(b"img")
    count = await db.scan_directory(str(tmp_path))
    assert count == 1


async def test_scan_no_duplicates_on_rescan(image_dir):
    await db.scan_directory(str(image_dir))
    count = await db.scan_directory(str(image_dir))
    assert count == 0  # all already exist


async def test_scan_invalid_path_raises():
    with pytest.raises(ValueError, match="Directory not found"):
        await db.scan_directory("/nonexistent/path/xyz")


async def test_scan_file_path_raises(tmp_path):
    file = tmp_path / "file.txt"
    file.write_bytes(b"x")
    with pytest.raises(ValueError):
        await db.scan_directory(str(file))


# --- get_all_images / get_unlabeled_images ---

async def test_get_all_images_empty():
    images = await db.get_all_images()
    assert images == []


async def test_get_all_images_returns_scanned(image_dir):
    await db.scan_directory(str(image_dir))
    images = await db.get_all_images()
    assert len(images) == 3


async def test_get_unlabeled_images_excludes_labeled(image_dir):
    await db.scan_directory(str(image_dir))
    images = await db.get_all_images()
    await db.set_label(images[0]["id"], "OK")

    unlabeled = await db.get_unlabeled_images()
    assert len(unlabeled) == 2
    assert all(img["label"] is None for img in unlabeled)


# --- get_image_by_id ---

async def test_get_image_by_id_found(image_dir):
    await db.scan_directory(str(image_dir))
    images = await db.get_all_images()
    image = await db.get_image_by_id(images[0]["id"])
    assert image is not None
    assert image["filename"] == images[0]["filename"]


async def test_get_image_by_id_not_found():
    image = await db.get_image_by_id(9999)
    assert image is None


# --- set_label ---

async def test_set_label_ok(image_dir):
    await db.scan_directory(str(image_dir))
    images = await db.get_all_images()
    success = await db.set_label(images[0]["id"], "OK")
    assert success is True
    updated = await db.get_image_by_id(images[0]["id"])
    assert updated["label"] == "OK"
    assert updated["labeled_at"] is not None


async def test_set_label_ng(image_dir):
    await db.scan_directory(str(image_dir))
    images = await db.get_all_images()
    await db.set_label(images[0]["id"], "NG")
    updated = await db.get_image_by_id(images[0]["id"])
    assert updated["label"] == "NG"


async def test_set_label_invalid_raises(image_dir):
    await db.scan_directory(str(image_dir))
    images = await db.get_all_images()
    with pytest.raises(ValueError, match="Label must be"):
        await db.set_label(images[0]["id"], "GOOD")


async def test_set_label_can_overwrite(image_dir):
    await db.scan_directory(str(image_dir))
    images = await db.get_all_images()
    await db.set_label(images[0]["id"], "OK")
    await db.set_label(images[0]["id"], "NG")
    updated = await db.get_image_by_id(images[0]["id"])
    assert updated["label"] == "NG"


# --- get_stats ---

async def test_get_stats_empty():
    stats = await db.get_stats()
    assert stats == {"total": 0, "ok": 0, "ng": 0, "unlabeled": 0, "labeled": 0}


async def test_get_stats_after_labeling(image_dir):
    await db.scan_directory(str(image_dir))
    images = await db.get_all_images()
    await db.set_label(images[0]["id"], "OK")
    await db.set_label(images[1]["id"], "NG")

    stats = await db.get_stats()
    assert stats["total"] == 3
    assert stats["ok"] == 1
    assert stats["ng"] == 1
    assert stats["unlabeled"] == 1
    assert stats["labeled"] == 2


# --- clear_all ---

async def test_clear_all(image_dir):
    await db.scan_directory(str(image_dir))
    await db.clear_all()
    images = await db.get_all_images()
    assert images == []
