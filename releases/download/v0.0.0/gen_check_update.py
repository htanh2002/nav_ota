#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone
import re


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def infer_version(bin_path: Path, explicit_version: str | None) -> str:
    if explicit_version:
        return explicit_version

    # Try parent folders like v1.0.1 or 1.0.1
    for p in [bin_path.parent.name, bin_path.stem, bin_path.name]:
        m = re.search(r'v?(\d+\.\d+\.\d+(?:[.-][A-Za-z0-9]+)?)', p)
        if m:
            return m.group(1)

    raise SystemExit(
        "Không suy ra được version. Hãy truyền --version, ví dụ --version 1.0.2"
    )


def infer_url(bin_path: Path, explicit_url: str | None, raw_base: str | None) -> str:
    if explicit_url:
        return explicit_url

    if raw_base:
        rel = bin_path.as_posix().lstrip('./')
        return raw_base.rstrip('/') + '/' + rel

    raise SystemExit(
        "Thiếu URL tải file .bin. Hãy truyền --url hoặc --raw-base."
    )


def build_payload(version: str, url: str, bin_path: Path, message: str, code: int) -> dict:
    stat = bin_path.stat()
    return {
        "code": code,
        "message": message,
        "firmware": {
            "version": version,
            "url": url,
            "name": bin_path.name,
            "sha256": sha256_file(bin_path),
            "size": stat.st_size,
        },
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tạo check_update.json từ file firmware .bin"
    )
    parser.add_argument(
        "bin_file",
        nargs="?",
        default=None,
        help="Đường dẫn file .bin. Nếu bỏ trống, script sẽ tự tìm 1 file .bin trong thư mục hiện tại.",
    )
    parser.add_argument(
        "--version",
        help="Version firmware, ví dụ 1.0.2. Nếu không truyền, script thử suy ra từ tên thư mục/file.",
    )
    parser.add_argument(
        "--url",
        help="URL tải trực tiếp file .bin. Nếu có thì ưu tiên dùng URL này.",
    )
    parser.add_argument(
        "--raw-base",
        help=(
            "Base URL raw để ghép với đường dẫn file .bin, ví dụ: "
            "https://raw.githubusercontent.com/htanh2002/nav_ota/main"
        ),
    )
    parser.add_argument(
        "--message",
        default="New firmware available",
        help="Nội dung field message trong JSON.",
    )
    parser.add_argument(
        "--code",
        type=int,
        default=2101,
        help="Nội dung field code trong JSON. Mặc định: 2101",
    )
    parser.add_argument(
        "--output",
        default="check_update.json",
        help="Tên file JSON đầu ra. Mặc định: check_update.json",
    )
    args = parser.parse_args()

    if args.bin_file:
        bin_path = Path(args.bin_file)
        if not bin_path.exists():
            raise SystemExit(f"Không tìm thấy file: {bin_path}")
    else:
        bins = sorted(Path('.').glob('*.bin'))
        if len(bins) == 0:
            raise SystemExit("Không tìm thấy file .bin nào trong thư mục hiện tại")
        if len(bins) > 1:
            names = ', '.join(b.name for b in bins)
            raise SystemExit(
                f"Có nhiều file .bin trong thư mục hiện tại: {names}. Hãy chỉ rõ file cần dùng."
            )
        bin_path = bins[0]

    version = infer_version(bin_path, args.version)
    url = infer_url(bin_path, args.url, args.raw_base)

    payload = build_payload(version=version, url=url, bin_path=bin_path, message=args.message, code=args.code)

    output_path = Path(args.output)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding='utf-8')

    print(f"Đã tạo: {output_path}")
    print(f"version : {payload['firmware']['version']}")
    print(f"name    : {payload['firmware']['name']}")
    print(f"size    : {payload['firmware']['size']} bytes")
    print(f"sha256  : {payload['firmware']['sha256']}")
    print(f"url     : {payload['firmware']['url']}")


if __name__ == '__main__':
    main()
