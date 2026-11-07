import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.services.scheduler import scheduler
from app.routers import (
    campaigns,
    calls,
    orders,
    callbacks,
    public_forms,
    twilio_media,
    simulator
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("barta_ai")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing BARTA AI Voice Platform...")
    # 1. Initialize SQLite / PostgreSQL DB & seed products
    await init_db()
    # 2. Start callback scheduler
    scheduler.start()
    logger.info("BARTA AI successfully started.")
    yield
    # Shutdown
    logger.info("Shutting down BARTA AI...")
    scheduler.stop()

app = FastAPI(
    title="BARTA AI - Voice Agent Platform",
    description="Autonomous Outbound AI Voice Agent for B2B & B2C Sales, powered by Gnani AI (Prisma STT & Timbre TTS) and Google Gemini.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(campaigns.router)
app.include_router(calls.router)
app.include_router(orders.router)
app.include_router(callbacks.router)
app.include_router(public_forms.router)
app.include_router(twilio_media.router)
app.include_router(simulator.router)

@app.api_route("/twilio/voice", methods=["GET", "POST"])
async def twilio_voice(request: Request):
    # This TwiML script tells Twilio what to do when the call connects
    twiml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Connect>
            <Stream url="wss://unstable-roundish-giblet.ngrok-free.dev/twilio/media" />
        </Connect>
    </Response>"""
    
    # Return as XML so Twilio reads it, and if you load it in Chrome it will render cleanly
    return HTMLResponse(content=twiml_content, media_type="application/xml")

@app.get("/")
async def root():
    return {
        "platform": "BARTA AI",
        "tagline": "Upload a customer list, press start, and watch orders arrive on your dashboard.",
        "status": "online",
        "gnani_models": {
            "stt": "Gnani Prisma v2.5 / v3",
            "tts": "Gnani Timbre v2.0"
        },
        "llm": settings.GEMINI_MODEL,
        "docs_url": "/docs"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "twilio_configured": bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN),
        "gnani_configured": bool(settings.GNANI_API_KEY),
        "gemini_configured": bool(settings.GEMINI_API_KEY),
        "resend_configured": bool(settings.RESEND_API_KEY)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)

