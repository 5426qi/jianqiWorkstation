import os, uuid, tempfile, subprocess
import requests
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from markitdown import MarkItDown
import whisper

app = FastAPI()
BASE_DIR = Path(__file__).parent
app.mount("/fonts", StaticFiles(directory=str(BASE_DIR / "fonts")), name="fonts")
md = MarkItDown()
PROCESSED_DIR = Path(str(Path(__file__).parent.parent.parent / "_processed"))
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

OPENWEBUI_URL = "http://127.0.0.1:8080"
API_KEY = "sk-YOUR_ZHIPU_API_KEY"
KB_ID = "YOUR_KNOWLEDGE_BASE_ID"

_whisper_model = None
def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        print("正在加载 OpenAI Whisper 模型 (自动使用 GPU)...")
        # 优先尝试 CUDA，如果失败自动回退 CPU
        try:
            _whisper_model = whisper.load_model("small", device="cuda")
            print("✅ 模型加载成功，显卡加速可用！")
        except Exception as e:
            print(f"CUDA 加载失败 ({e})，回退到 CPU 模式...")
            _whisper_model = whisper.load_model("small", device="cpu")
    return _whisper_model

def upload_to_kb(filepath, filename):
    try:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        upload_url = f"{OPENWEBUI_URL}/api/v1/files/"
        with open(filepath, "rb") as f:
            files = {"file": (filename, f, "text/markdown")}
            r = requests.post(upload_url, headers=headers, files=files)
        if not r.ok: return f"HTTP {r.status_code}"
        file_id = r.json().get("id")
        link_url = f"{OPENWEBUI_URL}/api/v1/knowledge/{KB_ID}/file/add"
        l = requests.post(link_url, headers={**headers, "Content-Type": "application/json"}, json={"file_id": file_id})
        return True if l.ok else "关联失败"
    except Exception as e: return str(e)

@app.get("/")
async def index(): return FileResponse(BASE_DIR / "index.html")

@app.post("/convert")
async def convert(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext in [".mp4", ".mp3", ".wav", ".m4a", ".mkv", ".avi"]:
        return {"ok": False, "error": "检测到音视频文件，请切换到【🎬 音视频分析】标签页上传！"}

    tmp = Path(os.environ.get("TEMP", ".")) / f"{uuid.uuid4()}_{file.filename}"
    tmp.write_bytes(await file.read())
    try:
        res = md.convert(str(tmp))
        out_name = Path(file.filename).stem + ".md"
        out_path = PROCESSED_DIR / out_name
        out_path.write_text(res.text_content, encoding="utf-8")
        upload_res = upload_to_kb(out_path, out_name)
        return {"ok": True, "filename": out_name, "uploaded": (upload_res is True), "err_msg": "" if upload_res is True else upload_res}
    except Exception as e: 
        return {"ok": False, "error": str(e)}
    finally: 
        tmp.unlink(missing_ok=True)

@app.post("/convert_media")
async def convert_media(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in [".mp4", ".mp3", ".wav", ".m4a", ".mkv", ".avi"]:
        return {"ok": False, "error": "不支持的格式"}
    
    tmp_dir = Path("C:/temp_whisper")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_video = tmp_dir / f"{uuid.uuid4()}{ext}"
    tmp_audio = tmp_dir / f"{uuid.uuid4()}.wav"
    
    tmp_video.write_bytes(await file.read())
    try:
        # 提取音频
        cmd = ["ffmpeg", "-y", "-i", str(tmp_video), "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", str(tmp_audio), "-loglevel", "error"]
        res = subprocess.run(cmd, capture_output=True, check=False)
        if res.returncode != 0:
            return {"ok": False, "error": f"FFmpeg 报错: {res.stderr.decode('utf-8', errors='ignore')}"}
        
        if not tmp_audio.exists() or tmp_audio.stat().st_size == 0:
            return {"ok": False, "error": "提取的音频为空"}

        # 调用 PyTorch Whisper
        model = get_whisper_model()
        result = model.transcribe(str(tmp_audio), language="zh")
        
        md_text = f"# 音视频转录稿：{file.filename}\n\n"
        for seg in result["segments"]:
            start = int(seg["start"] // 60)
            md_text += f"**[{start:02d}:{int(seg['start']%60):02d}]** {seg['text']}\n\n"
            
        out_name = Path(file.filename).stem + "_转录.md"
        out_path = PROCESSED_DIR / out_name
        out_path.write_text(md_text, encoding="utf-8")
        
        upload_res = upload_to_kb(out_path, out_name)
        return {"ok": True, "filename": out_name, "uploaded": (upload_res is True), "err_msg": "" if upload_res is True else upload_res}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        tmp_video.unlink(missing_ok=True)
        tmp_audio.unlink(missing_ok=True)

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