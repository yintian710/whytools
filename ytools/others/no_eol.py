# -*- coding: utf-8 -*-
"""
@File    : no_eol
@Author  : yintian
@Date    : 2026/5/7 14:35
@Software: PyCharm
@Desc    : 行尾标准化工具
"""

import argparse
import os
import sys
from pathlib import Path

DEFAULT_EXCLUDES = {'.git', 'node_modules', 'dist', 'coverage', '__pycache__'}
SCRIPT_DIR = Path(__file__).resolve().parent


def parse_args():
    parser = argparse.ArgumentParser(
        description='Normalize line endings recursively for files in a directory.'
    )
    parser.add_argument(
        'path',
        nargs='?',
        default=str(SCRIPT_DIR),
        help='Target directory, defaults to the script directory.',
    )
    parser.add_argument(
        '--eol',
        choices=('lf', 'crlf'),
        default='crlf' if os.name == 'nt' else 'lf',
        help='Target line ending. Defaults to lf on macOS/Linux and crlf on Windows.',
    )
    parser.add_argument(
        '--include',
        help='Comma-separated file extensions to include, like py,js,vue.',
    )
    parser.add_argument(
        '--exclude',
        help='Comma-separated directory names to exclude.',
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Only report files that would change without writing them.',
    )
    parser.add_argument(
        '--print-all',
        action='store_true',
        help='Print every scanned file and its current line ending style.',
    )
    return parser.parse_args()


def build_include_set(raw_value):
    if not raw_value:
        return None
    return {
        item.strip().lower().lstrip('.')
        for item in raw_value.split(',')
        if item.strip()
    }


def build_exclude_set(raw_value):
    if not raw_value:
        return set(DEFAULT_EXCLUDES)
    return {
        item.strip()
        for item in raw_value.split(',')
        if item.strip()
    }


def is_binary_file(file_path):
    try:
        with file_path.open('rb') as file:
            chunk = file.read(8192)
    except OSError:
        return True
    return b'\x00' in chunk


def should_include(file_path, include_set):
    if include_set is None:
        return True
    suffix = file_path.suffix.lower().lstrip('.')
    return suffix in include_set


def normalize_content(text, target_eol):
    unified = text.replace('\r\n', '\n').replace('\r', '\n')
    return unified.replace('\n', target_eol)


def detect_line_ending(data):
    has_crlf = b'\r\n' in data
    has_lf = b'\n' in data.replace(b'\r\n', b'')
    has_cr = b'\r' in data.replace(b'\r\n', b'')

    if has_crlf and not has_lf and not has_cr:
        return 'CRLF'
    if has_lf and not has_crlf and not has_cr:
        return 'LF'
    if has_cr and not has_crlf and not has_lf:
        return 'CR'
    if has_crlf or has_lf or has_cr:
        return 'MIXED'
    return 'NO_EOL'


def iter_files(root_path, exclude_dirs, include_set):
    for current_root, dir_names, file_names in os.walk(root_path):
        dir_names[:] = [name for name in dir_names if name not in exclude_dirs]
        current_root_path = Path(current_root)
        for file_name in sorted(file_names):
            file_path = current_root_path / file_name
            if should_include(file_path, include_set):
                yield file_path


def main():
    args = parse_args()
    root_path = Path(args.path).resolve()

    if not root_path.exists():
        print(f'Target path does not exist: {root_path}', file=sys.stderr)
        return 1

    if not root_path.is_dir():
        print(f'Target path is not a directory: {root_path}', file=sys.stderr)
        return 1

    include_set = build_include_set(args.include)
    exclude_dirs = build_exclude_set(args.exclude)
    target_eol = '\r\n' if args.eol == 'crlf' else '\n'
    target_eol_name = args.eol.upper()

    changed_files = []
    skipped_files = []
    scanned_files = []

    for file_path in iter_files(root_path, exclude_dirs, include_set):
        relative_path = str(file_path.relative_to(root_path))

        if is_binary_file(file_path):
            skipped_files.append(relative_path)
            continue

        try:
            raw_data = file_path.read_bytes()
            original = raw_data.decode('utf-8')
        except (OSError, UnicodeDecodeError):
            skipped_files.append(relative_path)
            continue

        current_eol = detect_line_ending(raw_data)
        normalized = normalize_content(original, target_eol)
        will_change = normalized != original
        scanned_files.append((relative_path, current_eol, will_change))

        if not will_change:
            continue

        changed_files.append((relative_path, current_eol, target_eol_name))
        if not args.check:
            file_path.write_text(normalized, encoding='utf-8', newline='')

    if args.print_all:
        print('Scanned files and detected line endings:')
        for relative_path, current_eol, will_change in scanned_files:
            if will_change:
                print(f'- {relative_path}: {current_eol} -> {target_eol_name}')
            else:
                print(f'- {relative_path}: {current_eol}')
        if skipped_files:
            print('Skipped files:')
            for item in skipped_files:
                print(f'- {item}')

    if args.check:
        if changed_files:
            print(f'Found {len(changed_files)} file(s) not using {target_eol_name}:')
            for relative_path, current_eol, target_name in changed_files:
                print(f'- {relative_path}: {current_eol} -> {target_name}')
            if skipped_files:
                print(f'Skipped {len(skipped_files)} binary or non-UTF-8 file(s).')
            return 1

        print(f'All checked files already use {target_eol_name}.')
        if skipped_files:
            print(f'Skipped {len(skipped_files)} binary or non-UTF-8 file(s).')
        return 0

    if changed_files:
        print(f'Normalized {len(changed_files)} file(s) to {target_eol_name}:')
        for relative_path, current_eol, target_name in changed_files:
            print(f'- {relative_path}: {current_eol} -> {target_name}')
    else:
        print(f'No files needed changes. Target EOL: {target_eol_name}')

    if skipped_files:
        print(f'Skipped {len(skipped_files)} binary or non-UTF-8 file(s).')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())

if __name__ == '__main__':
    pass
