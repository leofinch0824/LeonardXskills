#!/usr/bin/env python3
"""paper-trail 离线抽取 worker:把解析后的论文正文按模板抽成结构化抽取卡。

不经过 agent 上下文,一次 API 调用产出几 KB 结果,token 用量打印到 stdout(供 ledger)。
端点为 OpenAI 兼容接口,通过环境变量配置:

  PAPER_TRAIL_WORKER_BASE_URL  如 https://your-relay/v1
  PAPER_TRAIL_WORKER_KEY       该端点 key
  PAPER_TRAIL_WORKER_MODEL     最便宜档模型名

用法:
  extract_paper.py --paper <正文.md> --template <extraction.md> --profile <profile.md> --out <抽取卡.md>
                   [--desensitized]
  extract_paper.py --selftest
"""
import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

from worker_boundary import classify_worker_endpoint

MAX_CHARS = 120_000

RULES = """你是论文结构化抽取器。按用户给的模板逐字段抽取,输出一张 markdown 抽取卡。
规则:
- 模板里每个字段都要填;论文没说的写"论文未述"。
- 数字、模型规模、数据集、资源需求逐字摘原文,不做概括换算。
- 可适用性只对照用户给的 profile 硬约束。约束齐备时打四档:直接可用 / 需微调(算力内)/ API 辅助(脱敏后)/ 不适用。
- 判定所需的 profile 约束为 TBD 时不得假设满足,先标记"待确认",并指出待确认字段。
- 引用论文证据,区分"论文已证明"与"对该场景的外推"。
- 只依据所给正文,正文没有的依据不补。"""


def chat(base, key, model, user_msg):
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions",
        data=json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": RULES},
                {"role": "user", "content": user_msg},
            ],
            "temperature": 0,
        }).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


def get_config():
    base = os.environ.get("PAPER_TRAIL_WORKER_BASE_URL", "")
    key = os.environ.get("PAPER_TRAIL_WORKER_KEY", "")
    model = os.environ.get("PAPER_TRAIL_WORKER_MODEL", "")
    if not all([base, key, model]):
        sys.exit(
            "worker 未配置:请设置 PAPER_TRAIL_WORKER_BASE_URL / _KEY / _MODEL "
            "(OpenAI 兼容端点 + 最便宜档模型)。未配置时按 reference/extract.md 的降级梯处理。"
        )
    return base, key, model


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--paper")
    parser.add_argument("--template")
    parser.add_argument("--profile")
    parser.add_argument("--out")
    parser.add_argument(
        "--desensitized",
        action="store_true",
        help="确认 paper 与 profile 可发送到外部 HTTPS worker",
    )
    args = parser.parse_args()
    if args.selftest:
        return args
    for name in ("paper", "template", "profile", "out"):
        if not getattr(args, name):
            parser.error(f"缺少参数 --{name};见文件头用法")
    return args


def classify_configured_worker(base):
    return classify_worker_endpoint(
        base,
        os.environ.get("PAPER_TRAIL_WORKER_TRUSTED_HOSTS", ""),
    )


def enforce_data_boundary(base, desensitized):
    boundary = classify_configured_worker(base)
    classification = boundary["classification"]
    if classification == "invalid":
        sys.exit("PAPER_TRAIL_WORKER_BASE_URL 必须是有效且不含凭据的 http(s) URL")
    if classification == "unconfigured":
        sys.exit("PAPER_TRAIL_WORKER_BASE_URL 未配置")
    if boundary["trusted"]:
        return
    if boundary["requires_desensitized"] and not desensitized:
        sys.exit(
            "外部 worker 端点需要 --desensitized，"
            "用于确认 paper 与 profile 已脱敏且允许出内网"
        )
    if not boundary["transport_allowed"]:
        sys.exit("外部 worker 端点只允许 HTTPS")


def main():
    args = parse_args()
    if args.selftest:
        base, key, model = get_config()
        # Self-test does not send paper/profile, but still refuses an invalid or
        # external plaintext endpoint so credentials are never sent over it.
        enforce_data_boundary(base, desensitized=True)
        resp = chat(base, key, model, "回复两个字:正常")
        content = resp["choices"][0]["message"]["content"]
        print(f"selftest OK: model={model} reply={content!r} usage={resp.get('usage')}")
        return

    paper = Path(args.paper).read_text(encoding="utf-8")
    if len(paper) > MAX_CHARS:
        sys.exit(
            f"正文超过 {MAX_CHARS} 字符；拒绝静默截断。"
            "请按章节筛选机制/结果/局限/资源需求后重试，或走 reference/extract.md 的降级梯。"
        )
    template = Path(args.template).read_text(encoding="utf-8")
    profile = Path(args.profile).read_text(encoding="utf-8")

    user_msg = (
        "## 抽取模板(逐字段填)\n" + template
        + "\n\n## profile 硬约束(可适用性判定依据)\n" + profile
        + "\n\n## 论文正文\n" + paper
    )

    base, key, model = get_config()
    enforce_data_boundary(base, args.desensitized)
    resp = chat(base, key, model, user_msg)
    card = resp["choices"][0]["message"]["content"]
    Path(args.out).write_text(
        card if card.endswith("\n") else card + "\n",
        encoding="utf-8",
    )
    print(
        f"worker OK: out={args.out} model={model} "
        f"usage={json.dumps(resp.get('usage'))}"
    )


if __name__ == "__main__":
    main()
