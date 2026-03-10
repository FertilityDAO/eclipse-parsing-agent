import json
import sys
from pathlib import Path

def main():
    log_file = Path(".claude/hooks/hook_debug.json")

    try:
        data = json.load(sys.stdin)
    except Exception as e:
        log_file.write_text(json.dumps({"error": str(e)}), encoding="utf-8")
        sys.exit(0)

    log_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    file_path = (
        data.get("tool_input", {}).get("file_path", "")
        or data.get("file_path", "")
    ).lower()

    if "\\data\\" in file_path or "/data/" in file_path:
        print("Editing files inside /data is not allowed.", file=sys.stderr)
        sys.exit(2)

    sys.exit(0)

if __name__ == "__main__":
    main()