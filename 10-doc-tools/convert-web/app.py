import os, uuid, json
import requests
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from markitdown import MarkItDown

app = FastAPI()
app.mount("/fonts", StaticFiles(directory=r"G:\工作台\10-doc-tools\convert-web"), name="fonts")

md = MarkItDown()
PROCESSED_DIR = Path(r"G:\工作台\_processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
CALENDAR_FILE = Path(r"G:\工作台\_workflow\calendar.json")

OPENWEBUI_URL = "http://127.0.0.1:8080"
API_KEY = "sk-e5c5eee1eb55429baba3498f5490cca4"
KB_ID = "85139fc7-3b2f-4216-bc14-9aadb34e9d94"

class CalendarData(BaseModel):
    data: dict

def upload_to_kb(filepath, filename):
    try:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        upload_url = f"{OPENWEBUI_URL}/api/v1/files/"
        with open(filepath, "rb") as f:
            files = {"file": (filename, f, "text/markdown")}
            upload_resp = requests.post(upload_url, headers=headers, files=files)
        if not upload_resp.ok: return f"HTTP {upload_resp.status_code}"
        file_id = upload_resp.json().get("id")
        link_url = f"{OPENWEBUI_URL}/api/v1/knowledge/{KB_ID}/file/add"
        link_resp = requests.post(link_url, headers={**headers, "Content-Type": "application/json"}, json={"file_id": file_id})
        return True if link_resp.ok else "关联失败"
    except Exception as e:
        return str(e)

@app.get("/")
async def index():
    return FileResponse(r"G:\工作台\10-doc-tools\convert-web\index.html")

@app.get("/calendar")
async def calendar_page():
    return FileResponse(r"G:\工作台\10-doc-tools\convert-web\calendar.html")

@app.get("/api/calendar")
async def get_calendar():
    if not CALENDAR_FILE.exists(): return {}
    with open(CALENDAR_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

@app.post("/api/calendar")
async def save_calendar(payload: CalendarData):
    CALENDAR_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CALENDAR_FILE, "w", encoding="utf-8") as f:
        json.dump(payload.data, f, ensure_ascii=False, indent=2)
    return {"status": "ok"}

@app.post("/convert")
async def convert(file: UploadFile = File(...)):
    tmp = Path(os.environ.get("TEMP", ".")) / f"{uuid.uuid4()}_{file.filename}"
    content = await file.read()
    tmp.write_bytes(content)
    try:
        result = md.convert(str(tmp))
        out_name = Path(file.filename).stem + ".md"
        out_path = PROCESSED_DIR / out_name
        out_path.write_text(result.text_content, encoding="utf-8")
        upload_res = upload_to_kb(out_path, out_name)
        return {"ok": True, "filename": out_name, "uploaded": (upload_res is True), "err_msg": "" if upload_res is True else upload_res}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        tmp.unlink(missing_ok=True)

@app.get("/files")
async def list_files():
    return [{"name": f.name, "size": f.stat().st_size} for f in sorted(PROCESSED_DIR.glob("*.md"))]

@app.get("/download/{name}")
async def download(name: str):
    p = PROCESSED_DIR / name
    if not p.exists(): raise HTTPException(404)
    return FileResponse(p, filename=name, media_type="text/markdown")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=13120)