"""Read-only pre-submission smoke check for 银龄智伴."""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
REQUIRED_KEYS = {"profile", "medications", "health_records", "daily_status", "care_actions"}
STALE_TEXT = ("课表已复制到剪贴板", "学校指定平台提交记录", "课堂签到", "第 5 章")


def fail(message: str) -> None:
    print(f"FAIL  {message}")
    raise SystemExit(1)


def main() -> None:
    for filename in ("server.py", "reset_demo.py"):
        source = (ROOT / filename).read_text(encoding="utf-8")
        try:
            compile(source, filename, "exec")
        except SyntaxError as exc:
            fail(f"{filename} 语法错误：{exc}")
        print(f"PASS  {filename} 语法")

    for filename in ("elder_profile.json", "demo_profile.json"):
        try:
            data = json.loads((ROOT / filename).read_text(encoding="utf-8"))
        except Exception as exc:
            fail(f"{filename} 不是有效 JSON：{exc}")
        missing = REQUIRED_KEYS - set(data)
        if missing:
            fail(f"{filename} 缺少字段：{', '.join(sorted(missing))}")
        print(f"PASS  {filename} 数据结构")

    html = (ROOT / "dist/index.html").read_text(encoding="utf-8")
    for marker in ("todayDate", "demoBtn", "recordFeedback", "recordReminder", "deleteTask", "openFamily", "openAi", "openReminder", "本次建议依据"):
        if marker not in html:
            fail(f"网页缺少关键功能：{marker}")
    for text in STALE_TEXT:
        if text in html:
            fail(f"网页仍有旧场景文案：{text}")
    if "DASHSCOPE_API_KEY" in html or re.search(r"sk-[A-Za-z0-9]{16,}", html):
        fail("前端疑似包含 API Key")
    print("PASS  网页关键功能与文案")

    try:
        with urllib.request.urlopen("http://127.0.0.1:4173/", timeout=5) as response:
            if response.status != 200:
                fail(f"网站返回 HTTP {response.status}")
        with urllib.request.urlopen("http://127.0.0.1:4173/api/profile", timeout=5) as response:
            profile = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        fail(f"本地服务器不可访问：{exc}")
    if not isinstance(profile.get("health_records"), list):
        fail("/api/profile 返回格式不正确")
    print("PASS  本地网站与 /api/profile")
    print("提交前检查通过")


if __name__ == "__main__":
    main()
