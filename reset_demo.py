"""Reset the local profile before a competition demo.

The seeded judge walkthrough lives in demo_profile.json; transient demo actions are cleared.
"""
import json
from pathlib import Path

PROFILE_PATH = Path(__file__).parent / "elder_profile.json"
DEMO_PATH = Path(__file__).parent / "demo_profile.json"
EMPTY_PROFILE = {
    "profile": {
        "name": "",
        "age": None,
        "conditions": [],
        "allergies": [],
        "emergency_contact": "",
    },
    "medications": [],
    "health_records": [],
    "daily_status": {},
    "care_actions": [],
}

PROFILE_PATH.write_text(
    json.dumps(EMPTY_PROFILE, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
if DEMO_PATH.exists():
    demo = json.loads(DEMO_PATH.read_text(encoding="utf-8"))
    # Seeded demo records have no source field; remove records created during a walkthrough.
    demo["health_records"] = [item for item in demo.get("health_records", []) if not item.get("source")]
    demo["medications"] = [item for item in demo.get("medications", []) if item.get("status") != "待确认"]
    demo["care_actions"] = []
    demo.pop("deleted_tasks", None)
    DEMO_PATH.write_text(json.dumps(demo, ensure_ascii=False, indent=2), encoding="utf-8")
print("已清空本地真实档案；演示档案保留示例数据并清除临时任务")
