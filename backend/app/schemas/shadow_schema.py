from pydantic import BaseModel
from typing import List


class WordSchema(BaseModel):
    word: str
    start: float
    end: float


class PauseRegion(BaseModel):
    start: float
    end: float


class ReferenceResponse(BaseModel):
    words: List[WordSchema]
    times: List[float]
    rms: List[float]
    pitch: List[float]
    pause_mask: List[bool]
    pause_regions: List[PauseRegion]
    cps: List[float]
    duration: float
    sample_rate: int


class CompareResponse(BaseModel):
    overall: float
    timing: float
    pitch: float
    rhythm: float
    pacing: float
