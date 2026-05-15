from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.shadow import router as shadow_router

app = FastAPI(title="Shadowing Coach API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(shadow_router, prefix="/shadow", tags=["Shadow"])


@app.get("/health")
async def health():
    return {"status": "ok"}
