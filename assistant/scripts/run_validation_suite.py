from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from urllib import request

API_URL = "http://localhost:8000/chat"
ROOT_DIR = Path(__file__).resolve().parents[1]
RESULTS_ROOT = ROOT_DIR / "artifacts" / "test-results"

TESTS = [
    {
        "name": "english_basic",
        "language": "en",
        "text": "Say hello and count to 3",
        "expected_voice_contains": "AriaNeural",
    },
    {
        "name": "spanish_basic",
        "language": "es",
        "text": "¡Hola! Cuéntame un chiste en español",
        "expected_voice_contains": "DaliaNeural",
    },
    {
        "name": "spanish_accents",
        "language": "es",
        "text": "¿Cómo estás? También quiero información útil sobre México.",
        "expected_voice_contains": "DaliaNeural",
    },
]


def has_mojibake(text: str) -> bool:
    return any(ch in text for ch in ["Ã", "Â", "â", "┐", "≤", "ß", "φ", "Θ", "ⁿ", "·"])


def post_chat(payload: dict) -> tuple[int, dict]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        API_URL,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json; charset=utf-8",
        },
    )
    with request.urlopen(req, timeout=45) as resp:
        status = resp.status
        raw = resp.read()
    text = raw.decode("utf-8")
    return status, json.loads(text)


def resolve_audio_exists(audio_path: str) -> bool:
    if not audio_path:
        return False
    relative = audio_path.lstrip("/").replace("/", os.sep)
    absolute = ROOT_DIR / relative
    return absolute.exists()


def main() -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = RESULTS_ROOT / timestamp
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    results = []
    all_passed = True

    for test in TESTS:
        payload = {
            "session_id": f"validation-{test['name']}-{timestamp}",
            "actor": "user",
            "text": test["text"],
            "language": test["language"],
            "permissions": ["*"],
        }

        try:
            status, response = post_chat(payload)
            audio = response.get("audio") or {}
            voice_id = audio.get("voice_id", "")
            response_text = response.get("text", "")
            audio_path = audio.get("audio_path") or audio.get("wav_path", "")

            checks = {
                "status_200": status == 200,
                "voice_match": test["expected_voice_contains"] in voice_id,
                "encoding_clean": not has_mojibake(response_text),
                "audio_exists": resolve_audio_exists(audio_path),
                "duration_positive": (audio.get("duration_seconds") or 0) > 0,
            }
            passed = all(checks.values())
            all_passed = all_passed and passed

            result = {
                "test": test["name"],
                "input_language": test["language"],
                "input_text": test["text"],
                "http_status": status,
                "voice_id": voice_id,
                "audio_language": audio.get("language"),
                "duration_seconds": audio.get("duration_seconds"),
                "audio_path": audio_path,
                "response_text_preview": response_text[:180],
                "checks": checks,
                "passed": passed,
            }
            results.append(result)

            with (raw_dir / f"{test['name']}.json").open("w", encoding="utf-8") as f:
                json.dump(response, f, ensure_ascii=False, indent=2)

        except Exception as exc:
            all_passed = False
            results.append(
                {
                    "test": test["name"],
                    "input_language": test["language"],
                    "input_text": test["text"],
                    "passed": False,
                    "error": str(exc),
                }
            )

    summary = {
        "timestamp": timestamp,
        "overall_passed": all_passed,
        "tests": results,
    }

    summary_json = run_dir / "summary.json"
    summary_txt = run_dir / "summary.txt"
    latest_txt = RESULTS_ROOT / "LATEST.txt"

    with summary_json.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    lines = [
        "Validation Suite Results",
        "=" * 80,
        f"Timestamp: {timestamp}",
        f"Overall passed: {all_passed}",
        "",
    ]
    for item in results:
        lines.append(f"- {item['test']}: {'PASS' if item.get('passed') else 'FAIL'}")
        if "error" in item:
            lines.append(f"  error: {item['error']}")
        else:
            lines.append(f"  voice_id: {item.get('voice_id')}")
            lines.append(f"  audio_language: {item.get('audio_language')}")
            lines.append(f"  duration_seconds: {item.get('duration_seconds')}")
            lines.append(f"  audio_path: {item.get('audio_path')}")
            lines.append(f"  response_preview: {item.get('response_text_preview')}")
            lines.append(f"  checks: {item.get('checks')}")
        lines.append("")

    summary_txt.write_text("\n".join(lines), encoding="utf-8")
    latest_txt.write_text(str(run_dir), encoding="utf-8")

    print(f"Results written to: {run_dir}")
    print(f"Summary JSON: {summary_json}")
    print(f"Summary TXT:  {summary_txt}")


if __name__ == "__main__":
    main()
