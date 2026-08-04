#!/usr/bin/env python3
"""Package a rendered Learn Loop HTML view with its fixed local assets."""

import argparse
import shutil
import sys
from pathlib import Path


CSS_TAG = '<link rel="stylesheet" href="template.css" />'
SCRIPT_TAG = '<script src="template.js"></script>'


def convert_checkboxes(html: str) -> str:
    """Convert literal [ ] and [x] inside <li> elements to disabled checkboxes."""
    import re

    def replacement(match):
        checked = match.group("state").lower() == "x"
        attribute = " checked" if checked else ""
        return f'{match.group(1)}<input type="checkbox"{attribute} disabled> '

    return re.sub(
        r'(<li\b[^>]*>\s*)\[(?P<state> |x)\]\s*',
        replacement,
        html,
        flags=re.IGNORECASE,
    )
ASSET_NAMES = ("template.css", "template.js")
PACKAGED_ASSETS = Path(__file__).resolve().parents[1] / "assets"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="已填充占位符的 HTML 文件")
    parser.add_argument("--output", required=True, help="输出 HTML 文件")
    parser.add_argument(
        "--inline",
        action="store_true",
        help="将相邻的 template.css 和 template.js 内联到输出 HTML",
    )
    return parser.parse_args()


def read_assets(source):
    assets = {}
    source_dir = source.parent.resolve()
    for name in ASSET_NAMES:
        path = (source_dir / name).resolve()
        if path.parent != source_dir or not path.is_file():
            path = PACKAGED_ASSETS / name
        if not path.is_file():
            raise ValueError(f"缺少同目录固定资源：{name}")
        assets[name] = path
    return assets


def inline_assets(html, assets):
    css = (
        '<style data-learn-loop="template.css">\n'
        + assets["template.css"].read_text(encoding="utf-8")
        + "\n    </style>"
    )
    script = (
        '<script data-learn-loop="template.js">\n'
        + assets["template.js"].read_text(encoding="utf-8")
        + "\n    </script>"
    )
    return html.replace(CSS_TAG, css).replace(SCRIPT_TAG, script)


def validate_asset_references(html):
    if html.count(CSS_TAG) != 1 or html.count(SCRIPT_TAG) != 1:
        raise ValueError("HTML 必须各包含一次 template.css 与 template.js 的固定相对引用")


def render(source, output, inline):
    html = source.read_text(encoding="utf-8")
    validate_asset_references(html)
    assets = read_assets(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    content = inline_assets(html, assets) if inline else html
    output.write_text(convert_checkboxes(content), encoding="utf-8")
    if not inline:
        for name in ASSET_NAMES:
            destination = output.parent / name
            if destination.resolve() != assets[name].resolve():
                shutil.copyfile(assets[name], destination)


def main():
    args = parse_args()
    source = Path(args.input).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    try:
        if not source.is_file():
            raise ValueError(f"输入 HTML 不存在：{source}")
        render(source, output, args.inline)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
