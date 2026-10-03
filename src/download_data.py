"""Fetch the public M5 source from Zenodo and verify MD5 checksums.

Run: python -m src.download_data
"""
from pathlib import Path
import urllib.request

from .pipeline import FILES, md5

BASE = "https://zenodo.org/records/10203108/files/"


def download(directory: Path = Path("data/raw")) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, expected in FILES.items():
        dest = directory / name
        if dest.exists() and md5(dest) == expected:
            print(f"Verified existing {name}")
            continue
        partial = directory / f"{name}.partial"
        try:
            print(f"Downloading {name} from Zenodo...")
            with (urllib.request.urlopen(BASE + name + "?download=1", timeout=90) as source,
                  partial.open("wb") as target):
                while block := source.read(4 * 1024 * 1024):
                    target.write(block)
            if md5(partial) != expected:
                raise ValueError(f"Downloaded {name} failed checksum verification")
            partial.replace(dest)
            print(f"Verified {name}")
        finally:
            partial.unlink(missing_ok=True)


if __name__ == "__main__":
    download()
