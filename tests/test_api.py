import csv
import io

import pytest

import database as db


# --- GET / ---

async def test_index_returns_html(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "SnapLabel" in response.text


# --- POST /scan ---

async def test_scan_valid_directory(client, image_dir):
    response = await client.post("/scan", json={"directory": str(image_dir)})
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 3
    assert data["unlabeled"] == 3


async def test_scan_invalid_directory(client):
    response = await client.post("/scan", json={"directory": "/nonexistent/xyz"})
    assert response.status_code == 400


async def test_scan_resets_index(client, image_dir):
    # Navigate away then rescan — index resets to 0
    await client.post("/scan", json={"directory": str(image_dir)})
    await client.get("/images/next")
    await client.get("/images/next")
    await client.post("/scan", json={"directory": str(image_dir)})
    response = await client.get("/images/current")
    assert response.json()["index"] == 0


# --- GET /images/current ---

async def test_current_no_images(client):
    response = await client.get("/images/current")
    assert response.status_code == 200
    data = response.json()
    assert data["image"] is None
    assert data["total"] == 0


async def test_current_with_images(client_with_images):
    response = await client_with_images.get("/images/current")
    assert response.status_code == 200
    data = response.json()
    assert data["image"] is not None
    assert data["index"] == 0
    assert data["total"] == 3
    assert data["has_prev"] is False
    assert data["has_next"] is True


# --- GET /images/next & /images/prev ---

async def test_next_advances_index(client_with_images):
    await client_with_images.get("/images/next")
    response = await client_with_images.get("/images/current")
    assert response.json()["index"] == 1


async def test_prev_decrements_index(client_with_images):
    await client_with_images.get("/images/next")
    await client_with_images.get("/images/prev")
    response = await client_with_images.get("/images/current")
    assert response.json()["index"] == 0


async def test_next_clamps_at_end(client_with_images):
    for _ in range(10):
        await client_with_images.get("/images/next")
    response = await client_with_images.get("/images/current")
    assert response.json()["index"] == 2  # last index of 3 images


async def test_prev_clamps_at_start(client_with_images):
    for _ in range(5):
        await client_with_images.get("/images/prev")
    response = await client_with_images.get("/images/current")
    assert response.json()["index"] == 0


# --- GET /images/peek_next ---

async def test_peek_next_returns_next_image(client_with_images):
    response = await client_with_images.get("/images/peek_next")
    assert response.json()["image"] is not None


async def test_peek_next_does_not_change_current(client_with_images):
    before = (await client_with_images.get("/images/current")).json()["index"]
    await client_with_images.get("/images/peek_next")
    after = (await client_with_images.get("/images/current")).json()["index"]
    assert before == after


async def test_peek_next_at_end_returns_none(client_with_images):
    for _ in range(10):
        await client_with_images.get("/images/next")
    response = await client_with_images.get("/images/peek_next")
    assert response.json()["image"] is None


# --- POST /images/{id}/label ---

async def test_label_ok(client_with_images):
    image_id = (await client_with_images.get("/images/current")).json()["image"]["id"]
    response = await client_with_images.post(
        f"/images/{image_id}/label", json={"label": "OK"}
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
    updated = await db.get_image_by_id(image_id)
    assert updated["label"] == "OK"


async def test_label_ng(client_with_images):
    image_id = (await client_with_images.get("/images/current")).json()["image"]["id"]
    await client_with_images.post(f"/images/{image_id}/label", json={"label": "NG"})
    updated = await db.get_image_by_id(image_id)
    assert updated["label"] == "NG"


async def test_label_invalid_returns_400(client_with_images):
    image_id = (await client_with_images.get("/images/current")).json()["image"]["id"]
    response = await client_with_images.post(
        f"/images/{image_id}/label", json={"label": "MAYBE"}
    )
    assert response.status_code == 400


async def test_label_not_found_returns_404(client):
    response = await client.post("/images/9999/label", json={"label": "OK"})
    assert response.status_code == 404


async def test_label_can_be_overwritten(client_with_images):
    image_id = (await client_with_images.get("/images/current")).json()["image"]["id"]
    await client_with_images.post(f"/images/{image_id}/label", json={"label": "OK"})
    await client_with_images.post(f"/images/{image_id}/label", json={"label": "NG"})
    updated = await db.get_image_by_id(image_id)
    assert updated["label"] == "NG"


# --- GET /images/{id}/file ---

async def test_get_image_file(client_with_images):
    image_id = (await client_with_images.get("/images/current")).json()["image"]["id"]
    response = await client_with_images.get(f"/images/{image_id}/file")
    assert response.status_code == 200
    assert response.content == b"fake-image-data"


async def test_get_image_file_not_found(client):
    response = await client.get("/images/9999/file")
    assert response.status_code == 404


# --- GET /stats ---

async def test_stats_empty(client):
    response = await client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert data == {"total": 0, "ok": 0, "ng": 0, "unlabeled": 0, "labeled": 0}


async def test_stats_after_labeling(client_with_images):
    image_id = (await client_with_images.get("/images/current")).json()["image"]["id"]
    await client_with_images.post(f"/images/{image_id}/label", json={"label": "OK"})
    response = await client_with_images.get("/stats")
    data = response.json()
    assert data["total"] == 3
    assert data["ok"] == 1
    assert data["unlabeled"] == 2


# --- GET /export/csv ---

async def test_export_csv_headers(client_with_images):
    response = await client_with_images.get("/export/csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]


async def test_export_csv_content(client_with_images):
    image_id = (await client_with_images.get("/images/current")).json()["image"]["id"]
    await client_with_images.post(f"/images/{image_id}/label", json={"label": "OK"})

    response = await client_with_images.get("/export/csv")
    reader = csv.DictReader(io.StringIO(response.text))
    rows = list(reader)

    assert len(rows) == 3
    ok_rows = [r for r in rows if r["label"] == "OK"]
    assert len(ok_rows) == 1
    assert ok_rows[0]["labeled_at"] != ""
