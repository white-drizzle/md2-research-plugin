#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the research-mode slide_contract.json.

Usage:
  python verify_contract.py slide_contract.json [slide_plan.json]

Exit code 0 means the contract is structurally valid. The validator checks
identity and required planning fields; it deliberately does not judge prose
quality with regular expressions.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REQUIRED_SLIDE_FIELDS = (
    "slide_id",
    "section",
    "one_sentence_message",
    "audience_question",
    "must_show",
    "must_not_show",
    "evidence",
)
SLIDE_ID_RE = re.compile(r"^s(\d+)$")


def _fail(errors: List[str], message: str) -> None:
    errors.append(message)


def _validate_contiguous_ids(ids: List[str], errors: List[str]) -> None:
    numbers: List[int] = []
    for sid in ids:
        match = SLIDE_ID_RE.fullmatch(sid)
        if not match:
            _fail(errors, f"非法 slide_id: {sid}")
            continue
        numbers.append(int(match.group(1)))
    if numbers and numbers != list(range(numbers[0], numbers[0] + len(numbers))):
        _fail(errors, "slide_id 必须按数字连续编号")


def validate_contract(contract: Any, plan: Optional[Dict[str, Any]] = None) -> List[str]:
    errors: List[str] = []
    if not isinstance(contract, dict):
        return ["contract 顶层必须是 object"]
    if not isinstance(contract.get("meta"), dict):
        _fail(errors, "缺少 meta object")
    if not isinstance(contract.get("workflow"), list) or not contract["workflow"]:
        _fail(errors, "workflow 必须是非空数组")
    slides = contract.get("slides")
    if not isinstance(slides, list) or not slides:
        return errors + ["slides 必须是非空数组"]

    ids: List[str] = []
    valid_contract_slides: List[Dict[str, Any]] = []
    for index, slide in enumerate(slides):
        prefix = f"slides[{index}]"
        if not isinstance(slide, dict):
            _fail(errors, f"{prefix} 必须是 object")
            continue
        sid = slide.get("slide_id")
        if isinstance(sid, str) and sid.strip():
            ids.append(sid)
        else:
            _fail(errors, f"{prefix}.slide_id 必须是非空字符串")
        missing = [field for field in REQUIRED_SLIDE_FIELDS if field not in slide]
        if missing:
            _fail(errors, f"{prefix} 缺少字段: {', '.join(missing)}")
            continue
        valid_contract_slides.append(slide)
        if not isinstance(slide["section"], str) or not slide["section"].strip():
            _fail(errors, f"{prefix}.section 必须是非空字符串")
        for field in ("one_sentence_message", "audience_question"):
            if not isinstance(slide[field], str) or not slide[field].strip():
                _fail(errors, f"{prefix}.{field} 必须是非空字符串")
        for field in ("must_show", "must_not_show", "evidence"):
            value = slide[field]
            if not isinstance(value, list) or not value or not all(
                isinstance(item, str) and item.strip() for item in value
            ):
                _fail(errors, f"{prefix}.{field} 必须是非空字符串数组")
        if index > 0 and "bridge_from_previous" in slide:
            if not isinstance(slide["bridge_from_previous"], str) or not slide["bridge_from_previous"].strip():
                _fail(errors, f"{prefix}.bridge_from_previous 不能为空")
        if index < len(slides) - 1 and "bridge_to_next" in slide:
            if not isinstance(slide["bridge_to_next"], str) or not slide["bridge_to_next"].strip():
                _fail(errors, f"{prefix}.bridge_to_next 不能为空")

    if len(ids) != len(set(ids)):
        _fail(errors, "slides.slide_id 必须唯一")
    _validate_contiguous_ids(ids, errors)

    if plan is not None:
        if not isinstance(plan, dict) or not isinstance(plan.get("slides"), list):
            _fail(errors, "slide_plan 顶层必须包含 slides 数组")
            return errors
        plan_slides = plan["slides"]
        if not all(isinstance(slide, dict) for slide in plan_slides):
            _fail(errors, "slide_plan.slides 每项必须是 object")
            return errors
        plan_ids = [slide.get("slide_id") for slide in plan_slides]
        if ids != plan_ids:
            _fail(errors, "contract 与 slide_plan 的 slide_id 顺序不一致")
        contract_sections = {
            slide["slide_id"]: slide["section"]
            for slide in valid_contract_slides
            if isinstance(slide.get("slide_id"), str)
            and isinstance(slide.get("section"), str)
        }
        for slide in plan_slides:
            sid = slide.get("slide_id")
            if not isinstance(sid, str):
                _fail(errors, "slide_plan.slides[].slide_id 必须是字符串")
                continue
            if sid in contract_sections and slide.get("section") != contract_sections[sid]:
                _fail(errors, f"{sid} 的 section 与 slide_plan 不一致")
    return errors


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument("slide_plan", type=Path, nargs="?")
    args = parser.parse_args(argv)
    try:
        contract = json.loads(args.contract.read_text(encoding="utf-8"))
        plan = json.loads(args.slide_plan.read_text(encoding="utf-8")) if args.slide_plan else None
    except (OSError, json.JSONDecodeError) as exc:
        print(f"contract 读取失败: {exc}", file=sys.stderr)
        return 2
    errors = validate_contract(contract, plan)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    count = len(contract["slides"])
    print(f"contract 通过 ✓ ({count} 页)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
