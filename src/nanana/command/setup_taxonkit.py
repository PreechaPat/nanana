import os
import requests
import tarfile
from pathlib import Path
import shutil
import sys
import argparse

TAXDUMP_URL = "https://ftp.ncbi.nih.gov/pub/taxonomy/taxdump.tar.gz"
TAXDUMP_FILE = "taxdump.tar.gz"
TARGET_FILES = {"names.dmp", "nodes.dmp", "delnodes.dmp", "merged.dmp"}
TAXONKIT_DIR = Path.home() / ".taxonkit"
CHUNK_SIZE = 8192

TEMP_DIR = Path.cwd() / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)
TEMP_TAR_PATH = TEMP_DIR / TAXDUMP_FILE

def download_with_resume(url, dest):
    headers = {}
    if dest.exists():
        existing_size = dest.stat().st_size
        headers['Range'] = f"bytes={existing_size}-"
    else:
        existing_size = 0

    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        mode = 'ab' if 'Range' in headers else 'wb'
        with open(dest, mode) as f:
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    f.write(chunk)

def extract_tar(file_path, extract_to):
    with tarfile.open(file_path, 'r:gz') as tar:
        tar.extractall(path=extract_to)

def move_target_files(src_dir, dest_dir, target_files):
    dest_dir.mkdir(parents=True, exist_ok=True)
    for fname in target_files:
        src_file = Path(src_dir) / fname
        dest_file = dest_dir / fname
        if src_file.exists():
            shutil.copy2(src_file, dest_file)
        else:
            print(f"Warning: {fname} not found in extracted archive.")

def check_overwrite(force: bool):
    existing_files = [TAXONKIT_DIR / fname for fname in ("names.dmp", "nodes.dmp")]
    if any(f.exists() for f in existing_files):
        if not force:
            print(f"Found existing files in {TAXONKIT_DIR}. Use --force to overwrite.")
            sys.exit(1)
        else:
            print("Overwriting existing files as --force is specified.")

def parse_args():
    parser = argparse.ArgumentParser(description="Download and extract NCBI taxonomy DMP files into ~/.taxonkit")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files without prompting"
    )
    return parser.parse_args()

def main():
    args = parse_args()
    check_overwrite(force=args.force)

    print(f"Downloading {TAXDUMP_FILE} into {TEMP_DIR}...")
    download_with_resume(TAXDUMP_URL, TEMP_TAR_PATH)

    print(f"Extracting tarball into {TEMP_DIR}...")
    extract_tar(TEMP_TAR_PATH, TEMP_DIR)

    print(f"Moving DMP files to {TAXONKIT_DIR}...")
    move_target_files(TEMP_DIR, TAXONKIT_DIR, TARGET_FILES)

    print("Done.")

if __name__ == "__main__":
    main()

