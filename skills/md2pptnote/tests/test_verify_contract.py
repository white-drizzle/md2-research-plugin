import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import verify_contract as v


def _contract(n=2):
    return {
        "meta": {"purpose": "test"},
        "workflow": ["问题", "结果"],
        "slides": [
            {
                "slide_id": f"s{i:02d}",
                "section": "01 · 测试",
                "one_sentence_message": f"页面{i}主旨",
                "audience_question": f"页面{i}回答什么？",
                "must_show": ["证据"],
                "must_not_show": ["无关内容"],
                "evidence": ["synthetic test"],
            }
            for i in range(1, n + 1)
        ],
        "global_guardrails": ["不得编造"],
    }


def test_valid_contract():
    assert v.validate_contract(_contract()) == []


def test_missing_required_field():
    contract = _contract()
    del contract["slides"][0]["one_sentence_message"]
    errors = v.validate_contract(contract)
    assert any("one_sentence_message" in error for error in errors)


def test_duplicate_or_non_contiguous_ids():
    contract = _contract()
    contract["slides"][1]["slide_id"] = "s01"
    errors = v.validate_contract(contract)
    assert any("唯一" in error for error in errors)
    assert any("连续" in error for error in errors)


def test_plan_identity_and_section_match():
    contract = _contract()
    plan = {"slides": [{"slide_id": "s01", "section": "01 · 测试"}, {"slide_id": "s02", "section": "错误"}]}
    errors = v.validate_contract(contract, plan)
    assert any("section" in error for error in errors)


def test_plan_order_mismatch():
    contract = _contract()
    plan = {"slides": [{"slide_id": "s02", "section": "01 · 测试"}, {"slide_id": "s01", "section": "01 · 测试"}]}
    errors = v.validate_contract(contract, plan)
    assert any("顺序" in error for error in errors)


def test_offset_ids_are_allowed_when_contiguous():
    contract = _contract()
    contract["slides"][0]["slide_id"] = "s07"
    contract["slides"][1]["slide_id"] = "s08"
    assert v.validate_contract(contract) == []


def test_malformed_plan_returns_errors_not_traceback():
    contract = _contract()
    errors = v.validate_contract(contract, {"slides": ["not-an-object"]})
    assert any("每项必须是 object" in error for error in errors)


def test_malformed_plan_unhashable_id_returns_errors_not_traceback():
    contract = _contract()
    errors = v.validate_contract(contract, {"slides": [{"slide_id": []}, {"slide_id": "s02"}]})
    assert any("必须是字符串" in error for error in errors)


def test_missing_contract_field_with_plan_returns_errors_not_traceback():
    contract = _contract()
    del contract["slides"][0]["section"]
    errors = v.validate_contract(contract, {"slides": [{"slide_id": "s01"}, {"slide_id": "s02"}]})
    assert any("section" in error for error in errors)
