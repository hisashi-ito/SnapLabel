from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from contextlib import asynccontextmanager
import csv
import io

import database as db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    yield


app = FastAPI(title="SnapLabel", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Session state for current image index
current_index = 0


class ScanRequest(BaseModel):
    directory: str


class LabelRequest(BaseModel):
    label: str


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/scan")
async def scan_directory(req: ScanRequest):
    global current_index
    try:
        count = await db.scan_directory(req.directory)
        current_index = 0
        stats = await db.get_stats()
        return {
            "message": f"Scanned {count} images ({stats['unlabeled']} unlabeled)",
            "count": count,
            "unlabeled": stats["unlabeled"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/images/current")
async def get_current_image():
    global current_index
    images = await db.get_unlabeled_images()
    stats = await db.get_stats()

    if not images:
        return {
            "image": None,
            "index": 0,
            "total": 0,
            "all_done": stats["total"] > 0 and stats["unlabeled"] == 0,
            "stats": stats
        }

    if current_index >= len(images):
        current_index = len(images) - 1
    if current_index < 0:
        current_index = 0

    image = images[current_index]
    return {
        "image": image,
        "index": current_index,
        "total": len(images),
        "has_prev": current_index > 0,
        "has_next": current_index < len(images) - 1,
        "stats": stats
    }


@app.get("/images/next")
async def next_image():
    global current_index
    images = await db.get_unlabeled_images()
    if images and current_index < len(images) - 1:
        current_index += 1
    return await get_current_image()


@app.get("/images/prev")
async def prev_image():
    global current_index
    if current_index > 0:
        current_index -= 1
    return await get_current_image()


@app.post("/images/{image_id}/label")
async def label_image(image_id: int, req: LabelRequest):
    try:
        success = await db.set_label(image_id, req.label)
        if not success:
            raise HTTPException(status_code=404, detail="Image not found")
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/images/{image_id}/file")
async def get_image_file(image_id: int):
    image = await db.get_image_by_id(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(
        image["path"],
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=3600"}
    )


@app.get("/stats")
async def get_stats():
    return await db.get_stats()


@app.get("/export/csv")
async def export_csv():
    images = await db.get_all_images()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["filename", "path", "label", "labeled_at"])

    for img in images:
        writer.writerow([
            img["filename"],
            img["path"],
            img["label"] or "",
            img["labeled_at"] or ""
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=labels.csv"}
    )
