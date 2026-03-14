"""Local API, with an optional built React app served from the same origin."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator
from starlette.concurrency import run_in_threadpool

from inkcalc.evaluator import ExpressionError, calculate
from inkcalc.recognition import ModelUnavailableError, Recognizer

Coordinate = Annotated[float, Field(ge=0, le=1000, allow_inf_nan=False)]
Point = tuple[Coordinate, Coordinate]
Stroke = Annotated[list[Point], Field(min_length=1, max_length=4000)]


class InkRequest(BaseModel):
    strokes: list[Stroke] = Field(min_length=1, max_length=256)
    model: Literal["svm", "cnn", "compare"] = "svm"

    @model_validator(mode="after")
    def point_budget(self):
        if sum(map(len, self.strokes)) > 20000:
            raise ValueError("The drawing exceeds 20,000 points.")
        return self


class ExpressionRequest(BaseModel):
    expression: str = Field(min_length=1, max_length=256)


class ExplanationRequest(InkRequest):
    symbol_index: int = Field(ge=0, le=63, strict=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.recognizer = None
    app.state.model_error = None
    try:
        app.state.recognizer = await run_in_threadpool(Recognizer)
    except (FileNotFoundError, ValueError, KeyError) as exc:
        app.state.model_error = str(exc)
    yield


app = FastAPI(title="InkCalc", version="0.1.0", lifespan=lifespan)


@app.get("/api/health")
def health():
    recognizer = app.state.recognizer
    return {
        "status": "ok",
        "recognition_ready": recognizer is not None,
        "model": recognizer.metadata if recognizer else None,
        "model_error": app.state.model_error,
        "models": recognizer.models_status if recognizer else {},
    }


@app.post("/api/calculate")
def evaluate(request: ExpressionRequest):
    try:
        return calculate(request.expression)
    except ExpressionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/recognize")
def recognize(request: InkRequest):
    if app.state.recognizer is None:
        raise HTTPException(
            status_code=503, detail=app.state.model_error or "The recognition model is unavailable."
        )
    try:
        tokens = app.state.recognizer.recognize(request.strokes, request.model)
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "tokens": tokens,
        "expression": "".join(token["label"] for token in tokens),
        "model": request.model,
    }


@app.post("/api/explain")
def explain(request: ExplanationRequest):
    if app.state.recognizer is None:
        raise HTTPException(status_code=503, detail="The recognition model is unavailable.")
    try:
        return app.state.recognizer.explain(request.strokes, request.symbol_index, request.model)
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


build = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if build.is_dir():
    app.mount("/", StaticFiles(directory=build, html=True), name="workspace")
