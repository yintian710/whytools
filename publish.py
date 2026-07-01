# -*- coding: utf-8 -*-
"""Build and publish the project with uv."""
import argparse
import re
import subprocess
from pathlib import Path

from ytools.version import is_main_version, update_version

ROOT = Path(__file__).resolve().parent
VERSION_FILE = ROOT / "ytools" / "VERSION"
PYPROJECT_FILE = ROOT / "pyproject.toml"


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def update_pyproject_version(version: str) -> None:
    content = PYPROJECT_FILE.read_text(encoding="utf-8")
    updated = re.sub(
        r'(?m)^(version\s*=\s*")[^"]+("\s*)$',
        rf'\g<1>{version}\2',
        content,
        count=1,
    )
    if content == updated:
        raise RuntimeError("未在 pyproject.toml 中找到 project.version")
    PYPROJECT_FILE.write_text(updated, encoding="utf-8")


def deal_version(update_type: str = "auto") -> str:
    current_version = VERSION_FILE.read_text(encoding="utf-8").strip()
    new_version = update_version(version=current_version, save=True, update_type=update_type)
    update_pyproject_version(new_version)
    return new_version


def sync_git(version: str) -> None:
    run("git", "add", "pyproject.toml", "ytools/VERSION")
    run("git", "commit", "-m", f"update from {version}")
    run("git", "push")

    if is_main_version(version):
        run("git", "tag", version)
        run("git", "push", "origin", version)


def py_test() -> bool:
    # pytest 退出码: 0=全部通过, 5=未收集到任何用例, 其余视为失败
    result = subprocess.run(
        ("uv", "run", "pytest", "test/", "--verbose"),
        cwd=ROOT,
    )
    if result.returncode == 5:
        print("未收集到测试用例, 视为通过")
        return True
    if result.returncode != 0:
        print("测试失败")
        return False
    print("测试通过")
    return True


def main(update_type: str = "auto", test_success: int = 1) -> None:
    if test_success and not py_test():
        print("停止打包")
        return

    new_version = deal_version(update_type)
    run("uv", "build")
    run("uv", "publish")
    sync_git(new_version)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "-t",
        "--update_type",
        help="""
    版本更新规则, 默认为 auto, 还可选:
    major:  大版本更新
    minor:  中版本更新
    micro:  小版本更新
    pre:    pre 版本更新
    pre@a:  alpha 版本更新
    pre@b:  beta 版本更新
""",
        default="auto",
    )
    ap.add_argument(
        "-ts",
        "--test_success",
        help="为 1 表示需要先 pytest 通过, 其余表示不需要",
        default=1,
        type=int,
    )
    args = ap.parse_args()
    main(args.update_type, args.test_success)
