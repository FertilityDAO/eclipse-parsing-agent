
import json
import subprocess
import sys
from pathlib import Path

def main():
    log_file = Path(".claude/hooks/validate_src_debug.json")

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

    if "\\src\\" not in file_path and "/src/" not in file_path:
        sys.exit(0)

    result = subprocess.run(
        ["python", "src/analyze_calendar_patterns.py"],
        capture_output=True,
        text=True
    )

    output = {
        "validated_file": file_path,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr
    }

    Path(".claude/hooks/validate_src_result.json").write_text(
        json.dumps(output, indent=2),
        encoding="utf-8"
    )

    if result.returncode != 0:
        print("Validation failed after src edit:", file=sys.stderr)
        if result.stderr.strip():
            print(result.stderr, file=sys.stderr)
        elif result.stdout.strip():
            print(result.stdout, file=sys.stderr)


    sys.exit(0)

if __name__ == "__main__":
    main()