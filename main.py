import os
from typing import List, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MelodyPreviewRequest(BaseModel):
    lyrics: str
    tempo: Optional[int] = 96
    key: Optional[str] = "C"
    style: Optional[str] = "pop"


class TimestampItem(BaseModel):
    lineText: str
    start_ms: int
    end_ms: int


class MelodyPreviewResponse(BaseModel):
    midiJson: dict
    guideAudioUrl: Optional[str] = None
    timestamps: List[TimestampItem]


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        from database import db
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


@app.post("/api/generate/melody-preview", response_model=MelodyPreviewResponse)
def generate_melody_preview(req: MelodyPreviewRequest):
    # In MOCK_MODE, synthesize quick melody & timestamps
    lines = [l.strip() for l in (req.lyrics or "").splitlines() if l.strip()]
    if not lines:
        lines = ["la la la", "dum dum"]
    beat_sec = 60.0 / max(60, min(req.tempo or 96, 180))
    # Simple mapping: each line = 2 beats
    timestamps: List[TimestampItem] = []
    t = 0.0
    notes = []
    midi_base = 60  # C4
    for i, line in enumerate(lines):
        start = int(t * 1000)
        dur_beats = 2
        end = int((t + dur_beats * beat_sec) * 1000)
        timestamps.append(TimestampItem(lineText=line, start_ms=start, end_ms=end))
        # Create a few stepping notes within the region
        step = 0.5
        steps = int(dur_beats / step)
        for s in range(steps):
          notes.append({
              "midi": midi_base + (i % 5) * 2 + (s % 3),
              "time": round(t + s * step * beat_sec, 3),
              "duration": round(step * beat_sec * 0.9, 3)
          })
        t += dur_beats * beat_sec
    midiJson = {"notes": notes, "tempo": req.tempo, "key": req.key, "style": req.style}

    guideAudioUrl = None
    if MOCK_MODE:
        guideAudioUrl = "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAACJWAAACABYAAAAAAACAgICAgP//"
    else:
        pass
    return MelodyPreviewResponse(midiJson=midiJson, guideAudioUrl=guideAudioUrl, timestamps=timestamps)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
