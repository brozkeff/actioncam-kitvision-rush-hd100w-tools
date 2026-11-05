"""Inspect relevant printable APK strings without extraction or execution."""

import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERN = re.compile(
    rb"192\.168\.|http://|Java_com_action_aremote_WiFiJNI_|Protocol[A-Za-z]+|tcp_client_"
)


def main() -> None:
    """Print relevant ASCII strings from selected APK members without executing them."""
    path = ROOT / "apps/android-apk/actionplusremote.apk"
    with zipfile.ZipFile(path) as archive:
        for name in ("classes.dex", "lib/armeabi/libaction.so"):
            print(f"[{name}]")
            for value in re.findall(rb"[\x20-\x7e]{4,}", archive.read(name)):
                if PATTERN.search(value):
                    print(value.decode("ascii"))


if __name__ == "__main__":
    main()
