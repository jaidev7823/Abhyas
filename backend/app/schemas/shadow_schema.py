from pydantic import BaseModel

from typing import List


class WordSchema(BaseModel):

    word: str
    start: float
    end: float


class ReferenceResponse(BaseModel):

    times: List[float]
    rms: List[float]
    pitch: List[float]
    pause_mask: List[bool]
    cps: List[float]
    words: List[WordSchema]


class CompareResponse(BaseModel):

    score: float

