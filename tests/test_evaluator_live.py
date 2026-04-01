"""
Live tests for the evaluator companion using real LLM models via OpenRouter.

Requires OPENROUTER_API_KEY to be set. Skipped automatically when missing.

Usage:
    export OPENROUTER_API_KEY="your-key"
    pytest tests/test_evaluator_live.py -v
    # or standalone:
    python tests/test_evaluator_live.py
"""

import asyncio
import os
import sys

import pytest

from wingent.providers.openrouter import OpenRouterProvider
from wingent.core.agent import CompanionAgent, CompanionConfig
from wingent.core.prompts import get_companion_prompt

MODEL = "google/gemini-2.0-flash-001"

needs_api_key = pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set",
)


def make_evaluator() -> CompanionAgent:
    provider = OpenRouterProvider()
    config = CompanionConfig(
        provider="openrouter",
        model=MODEL,
        temperature=0.2,
        max_tokens=256,
    )
    return CompanionAgent(
        purpose="evaluator",
        system_prompt=get_companion_prompt("evaluator"),
        provider=provider,
        config=config,
    )


@needs_api_key
def test_pass_correct_answer():
    """A correct, complete answer should PASS."""
    async def _run():
        evaluator = make_evaluator()
        verdict = await evaluator.run(
            "## Task Goal\nCalculate 2 + 2\n\n"
            "## Completion Criteria\nReturn the correct numerical answer\n\n"
            "## Agent's Result\nThe answer is 4."
        )
        assert verdict.strip().upper().startswith("PASS"), f"Expected PASS, got: {verdict.strip()}"
    asyncio.run(_run())


@needs_api_key
def test_fail_wrong_answer():
    """A wrong answer should FAIL."""
    async def _run():
        evaluator = make_evaluator()
        verdict = await evaluator.run(
            "## Task Goal\nCalculate 2 + 2\n\n"
            "## Completion Criteria\nReturn the correct numerical answer\n\n"
            "## Agent's Result\nThe answer is 5."
        )
        assert verdict.strip().upper().startswith("FAIL"), f"Expected FAIL, got: {verdict.strip()}"
    asyncio.run(_run())


@needs_api_key
def test_fail_incomplete_output():
    """An incomplete result that doesn't meet criteria should FAIL."""
    async def _run():
        evaluator = make_evaluator()
        verdict = await evaluator.run(
            "## Task Goal\nWrite a Python function that sorts a list using merge sort\n\n"
            "## Completion Criteria\nReturn working Python code with the function definition\n\n"
            "## Agent's Result\nMerge sort is a divide-and-conquer algorithm that "
            "divides the input array into two halves, recursively sorts them, "
            "and then merges the sorted halves."
        )
        assert verdict.strip().upper().startswith("FAIL"), f"Expected FAIL, got: {verdict.strip()}"
    asyncio.run(_run())


@needs_api_key
def test_pass_complete_code():
    """A complete code answer should PASS."""
    async def _run():
        evaluator = make_evaluator()
        verdict = await evaluator.run(
            "## Task Goal\nWrite a Python function that sorts a list using merge sort\n\n"
            "## Completion Criteria\nReturn working Python code with the function definition\n\n"
            "## Agent's Result\n"
            "```python\n"
            "def merge_sort(arr):\n"
            "    if len(arr) <= 1:\n"
            "        return arr\n"
            "    mid = len(arr) // 2\n"
            "    left = merge_sort(arr[:mid])\n"
            "    right = merge_sort(arr[mid:])\n"
            "    return merge(left, right)\n\n"
            "def merge(left, right):\n"
            "    result = []\n"
            "    i = j = 0\n"
            "    while i < len(left) and j < len(right):\n"
            "        if left[i] <= right[j]:\n"
            "            result.append(left[i])\n"
            "            i += 1\n"
            "        else:\n"
            "            result.append(right[j])\n"
            "            j += 1\n"
            "    result.extend(left[i:])\n"
            "    result.extend(right[j:])\n"
            "    return result\n"
            "```"
        )
        assert verdict.strip().upper().startswith("PASS"), f"Expected PASS, got: {verdict.strip()}"
    asyncio.run(_run())


@needs_api_key
def test_fail_off_topic():
    """A result that ignores the task entirely should FAIL."""
    async def _run():
        evaluator = make_evaluator()
        verdict = await evaluator.run(
            "## Task Goal\nSummarize the key points of the French Revolution\n\n"
            "## Completion Criteria\nA 3-5 sentence summary covering causes, key events, and outcomes\n\n"
            "## Agent's Result\nPython is a popular programming language created by Guido van Rossum."
        )
        assert verdict.strip().upper().startswith("FAIL"), f"Expected FAIL, got: {verdict.strip()}"
    asyncio.run(_run())


@needs_api_key
def test_fail_partial_criteria():
    """A result that meets some but not all criteria should FAIL."""
    async def _run():
        evaluator = make_evaluator()
        verdict = await evaluator.run(
            "## Task Goal\nCreate a project plan\n\n"
            "## Completion Criteria\nMust include: (1) timeline with dates, "
            "(2) budget estimate, (3) team assignments\n\n"
            "## Agent's Result\nProject Plan:\n"
            "- Phase 1 (Jan-Feb): Research\n"
            "- Phase 2 (Mar-Apr): Development\n"
            "- Phase 3 (May): Testing\n"
            "Note: Budget and team assignments to be determined."
        )
        assert verdict.strip().upper().startswith("FAIL"), f"Expected FAIL, got: {verdict.strip()}"
    asyncio.run(_run())


# Standalone runner
if __name__ == "__main__":
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("OPENROUTER_API_KEY not set. Skipping live evaluator tests.")
        sys.exit(0)

    print(f"Live Evaluator Tests (model: {MODEL})\n")

    tests = [
        test_pass_correct_answer,
        test_fail_wrong_answer,
        test_fail_incomplete_output,
        test_pass_complete_code,
        test_fail_off_topic,
        test_fail_partial_criteria,
    ]

    passed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS: {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {test.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR: {test.__name__}: {e}")

    print(f"\n{passed}/{len(tests)} tests passed")
    if passed < len(tests):
        sys.exit(1)
