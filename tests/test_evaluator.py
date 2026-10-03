# tests/test_evaluator.py
"""Tests for FilterEvaluator metrics and reporting (agent judgments are stubbed)."""
import json
from pathlib import Path

import pytest

from src.evaluation.evaluator import FilterEvaluator

GOLDEN_DATASET = Path(__file__).resolve().parents[1] / "data" / "evaluation" / "golden_dataset.json"


def _result(expected, predicted, case_id=1):
    return {
        "test_case_id": case_id,
        "title": f"Case {case_id}",
        "expected": expected,
        "predicted": predicted,
        "correct": expected == predicted,
        "score": 8 if predicted else 2,
        "reasoning": "r",
    }


@pytest.fixture
def golden_path(tmp_path):
    path = tmp_path / "golden.json"
    path.write_text(json.dumps({"test_cases": [
        {"id": 1, "title": "GPT-5 released", "summary": "New LLM", "expected_relevant": True},
        {"id": 2, "title": "Vue 4 released", "summary": "JS framework", "expected_relevant": False},
        {"id": 3, "title": "Diffusion paper", "summary": "Image models", "expected_relevant": True},
        {"id": 4, "title": "Docker update", "summary": "Containers", "expected_relevant": False},
    ]}))
    return path


@pytest.fixture
def evaluator(llm_model, golden_path):
    return FilterEvaluator(str(golden_path))


# --- _calculate_metrics -----------------------------------------------------


def test_metrics_known_confusion_matrix(evaluator):
    # TP=2, FN=1, FP=1, TN=1
    results = [
        _result(True, True, 1),
        _result(True, True, 2),
        _result(True, False, 3),
        _result(False, True, 4),
        _result(False, False, 5),
    ]

    metrics = evaluator._calculate_metrics(results)

    assert metrics["accuracy"] == pytest.approx(3 / 5)
    assert metrics["precision"] == pytest.approx(2 / 3)
    assert metrics["recall"] == pytest.approx(2 / 3)
    assert metrics["f1_score"] == pytest.approx(2 / 3)
    assert (metrics["correct"], metrics["total"]) == (3, 5)


def test_metrics_perfect_score(evaluator):
    metrics = evaluator._calculate_metrics([_result(True, True, 1), _result(False, False, 2)])

    assert metrics["accuracy"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1_score"] == 1.0


def test_metrics_no_positive_predictions(evaluator):
    """Precision/recall/F1 fall back to 0 instead of dividing by zero."""
    metrics = evaluator._calculate_metrics([_result(False, False, 1), _result(True, False, 2)])

    assert metrics["accuracy"] == 0.5
    assert metrics["precision"] == 0
    assert metrics["recall"] == 0
    assert metrics["f1_score"] == 0


# --- evaluate ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_scores_agent_against_golden_dataset(evaluator, monkeypatch):
    judgments = {
        "GPT-5 released": {"relevant": True, "relevance_score": 9, "reasoning": "LLM"},
        "Vue 4 released": {"relevant": True, "relevance_score": 7, "reasoning": "Wrongly AI"},
        "Diffusion paper": {"relevant": True, "relevance_score": 5, "reasoning": "Below threshold"},
        "Docker update": {"relevant": False, "relevance_score": 2, "reasoning": "DevOps"},
    }
    monkeypatch.setattr(evaluator.agent, "_judge_relevance",
                        lambda article: judgments[article["title"]])

    evaluation = await evaluator.evaluate()

    assert evaluation["test_cases"] == 4
    results = evaluation["results"]
    assert [r["predicted"] for r in results] == [True, True, False, False]
    assert [r["correct"] for r in results] == [True, False, False, True]
    assert results[2]["score"] == 5
    assert results[2]["reasoning"] == "Below threshold"
    # TP=1 (GPT), FP=1 (Vue), FN=1 (Diffusion), TN=1 (Docker)
    assert evaluation["metrics"]["accuracy"] == 0.5
    assert evaluation["metrics"]["precision"] == 0.5
    assert evaluation["metrics"]["recall"] == 0.5


# --- save_report ------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_report(evaluator, tmp_path):
    results = [_result(True, True, 1), _result(False, True, 2)]
    evaluation = {
        "results": results,
        "metrics": evaluator._calculate_metrics(results),
        "test_cases": 2,
    }
    output = tmp_path / "reports" / "report.md"

    await evaluator.save_report(evaluation, str(output))

    content = output.read_text()
    assert "- **Accuracy:** 50.0%" in content
    assert "- **Precision:** 50.0%" in content
    assert "- **Recall:** 100.0%" in content
    assert "- **F1 Score:** 0.667" in content
    assert "- **Test Cases:** 1/2 correct" in content
    assert "### [1] ✅ PASS" in content
    assert "### [2] ❌ FAIL" in content
    assert "- Expected: Not Relevant" in content
    assert "- Predicted: Relevant (score: 8)" in content


# --- Golden dataset sanity check (read-only) --------------------------------


def test_golden_dataset_is_well_formed():
    cases = json.loads(GOLDEN_DATASET.read_text())["test_cases"]

    assert cases
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids)), "test case ids must be unique"
    for case in cases:
        assert {"id", "title", "summary", "expected_relevant"} <= set(case)
        assert isinstance(case["expected_relevant"], bool)
    labels = {c["expected_relevant"] for c in cases}
    assert labels == {True, False}, "dataset needs both relevant and irrelevant cases"
