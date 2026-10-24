import json, os
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()
BASE_DIR = Path(__file__).parent
app.mount("/fonts", StaticFiles(directory=str(BASE_DIR / "fonts")), name="fonts")
CALENDAR_FILE = Path(str(Path(__file__).parent.parent.parent / "_workflow" / "calendar.json"))

class CalendarData(BaseModel):
    data: dict

@app.get("/")
async def index(): return FileResponse(BASE_DIR / "index.html")

@app.get("/api/calendar")
async def get_calendar():
    if not CALENDAR_FILE.exists(): return {}
    with open(CALENDAR_FILE, "r", encoding="utf-8") as f: return json.load(f)

@app.post("/api/calendar")
async def save_calendar(payload: CalendarData):
    CALENDAR_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CALENDAR_FILE, "w", encoding="utf-8") as f:
        json.dump(payload.data, f, ensure_ascii=False, indent=2)
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=13121)