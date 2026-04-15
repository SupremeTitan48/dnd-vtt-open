import json
from pathlib import Path
from typing import Union

from pydantic import BaseModel, Field


class TutorialScenario(BaseModel):
    tutorial_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    estimated_minutes: int = Field(ge=1)
    steps: list[str] = Field(min_length=1)


def load_tutorial(path: Union[str, Path]) -> TutorialScenario:
    payload = json.loads(Path(path).read_text())
    return TutorialScenario.model_validate(payload)
