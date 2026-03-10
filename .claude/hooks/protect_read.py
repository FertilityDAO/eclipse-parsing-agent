import json
import sys
from pathlib import Path

def main():
    log_file = Path(".claude/hooks/read_hook_debug.json")

    try:
        data = json.load(sys.stdin)
    except Exception as e:
        log_file.write_text(json.dumps({"error": str(e)}), encoding="utf-8")
        sys.exit(0)

    log_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    file_path = (
        data.get("tool_input", {}).get("file_path", "")
        or data.get("file_path", "")
        or ""
    ).lower()

    blocked_patterns = [
        ".env",
        "\\keys\\",
        "/keys/",
        "\\secrets\\",
        "/secrets/",
        "\\tokens\\",
        "/tokens/",
    ]

    if any(pattern in file_path for pattern in blocked_patterns):
        print("Reading sensitive files is not allowed.", file=sys.stderr)

        sys.exit(2)

    sys.exit(0)

if __name__ == "__main__":
    main()