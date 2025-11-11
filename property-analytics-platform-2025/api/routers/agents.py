from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ...ai_engine.agents.property_analyst import analyze_property

router = APIRouter()

@router.get("/ping")
async def ping():
    return {"agents": "ok"}

class AnalyzeRequest(BaseModel):
    text: str = Field(..., description="Raw text to analyze with Claude")

@router.post("/analyze")
async def analyze(body: AnalyzeRequest):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Empty text")
    try:
        result = analyze_property(body.text)
        return {"analysis": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


