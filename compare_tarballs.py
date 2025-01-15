import tarfile
import os
import hashlib
import tempfile
import shutil
from pathlib import Path
from typing import Set, Tuple

def get_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def sanitize_filename(name: str) -> str:
    """Sanitize file name to be valid on both Unix and Windows."""
    # Replace invalid characters with underscore
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    return name

def safe_extractall(tar_obj, path):
    """Safely extract tar contents with filtering."""
    def filter_func(tar_info, extract_path):
        # Skip symlinks and hardlinks on Windows
        if tar_info.islnk() or tar_info.issym():
            return None

        # Skip special directory entries
        if tar_info.name in ['.', './']:
            return None

        # Sanitize the path
        tar_info.name = sanitize_filename(tar_info.name)

        # Skip absolute paths and parent directory references
        if tar_info.name.startswith(('/', '\\')) or '..' in tar_info.name:
            return None

        return tar_info

    # Extract files one by one, skipping problematic ones
    for member in tar_obj.getmembers():
        try:
            if filter_func(member, path):
                tar_obj.extract(member, path=path)
        except (OSError, IOError) as e:
            print(f"Skipping problematic file {member.name}: {e}")
            continue

def process_directory(dir_path: Path, base_path: Path) -> Set[Tuple[str, str]]:
    """
    Recursively process directory and return set of (relative_path, hash) tuples.
    """
    results = set()

    for item in dir_path.rglob('*'):
        if not item.is_file():
            continue

        # Get path relative to base directory
        rel_path = str(item.relative_to(base_path))

        # If file is a tarball, extract and process it
        if item.suffix == '.tar':
            with tempfile.TemporaryDirectory() as nested_temp_dir:
                nested_temp_path = Path(nested_temp_dir)
                try:
                    with tarfile.open(item) as tar:
                        safe_extractall(tar, nested_temp_path)
                    results.update(process_directory(nested_temp_path, nested_temp_path))
                except tarfile.ReadError:
                    # If not a valid tar, treat as regular file
                    results.add((rel_path, get_file_hash(item)))
        else:
            results.add((rel_path, get_file_hash(item)))

    return results

def compare_tarballs(tarball1_path: str, tarball2_path: str):
    """Compare contents of two tarballs by extracting to temp directories."""
    print(f"Comparing {tarball1_path} and {tarball2_path}")

    # Create temporary directories
    with tempfile.TemporaryDirectory() as temp_dir1, tempfile.TemporaryDirectory() as temp_dir2:
        temp_path1 = Path(temp_dir1)
        temp_path2 = Path(temp_dir2)

        # Extract tarballs
        print("Extracting tarballs...")
        with tarfile.open(tarball1_path) as tar1, tarfile.open(tarball2_path) as tar2:
            safe_extractall(tar1, temp_path1)
            safe_extractall(tar2, temp_path2)

        # Process directories
        print("Comparing contents...")
        files1 = process_directory(temp_path1, temp_path1)
        files2 = process_directory(temp_path2, temp_path2)

        paths1 = {path for path, _ in files1}
        paths2 = {path for path, _ in files2}

        # Find unique files in each tarball
        only_in_1 = paths1 - paths2
        only_in_2 = paths2 - paths1

        # Find files with different content
        common_paths = paths1 & paths2
        different_content = {
            path for path in common_paths
            if next(h for p, h in files1 if p == path) != next(h for p, h in files2 if p == path)
        }

        # Print results
        if only_in_1:
            print("\nFiles only in first tarball:")
            for path in sorted(only_in_1):
                print(f"  {path}")

        if only_in_2:
            print("\nFiles only in second tarball:")
            for path in sorted(only_in_2):
                print(f"  {path}")

        if different_content:
            print("\nFiles with different content:")
            for path in sorted(different_content):
                print(f"  {path}")

        if not (only_in_1 or only_in_2 or different_content):
            print("\nTarballs are identical!")

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python compare_tarballs.py <tarball1> <tarball2>")
        sys.exit(1)

    compare_tarballs(sys.argv[1], sys.argv[2])
