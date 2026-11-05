"""Hash local reference apps without executing them (Python 3.11+)."""

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Print SHA-256 hashes of local reference applications without executing them."""
    for path in sorted((ROOT / "apps").rglob("*")):
        if path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            print(f"{digest}  {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
