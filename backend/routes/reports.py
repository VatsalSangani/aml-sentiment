import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/reports")
async def get_reports():
    """Return the pre-generated 30 XAI reports from JSON file."""
    from config import TRAINING_DIR

    xai_dir = os.path.join(TRAINING_DIR, "xai_reports")
    json_files = sorted(Path(xai_dir).glob("xai_reports_*.json"), reverse=True)

    if not json_files:
        raise HTTPException(
            status_code=404,
            detail="No XAI reports found. Run AML_XAI.ipynb first.",
        )

    with open(json_files[0], "r", encoding="utf-8") as f:
        reports = json.load(f)

    return {"reports": reports, "count": len(reports)}
