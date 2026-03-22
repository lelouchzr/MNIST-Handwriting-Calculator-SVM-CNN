import pytest

from inkcalc.evaluator import ExpressionError, calculate


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("(9 + 2) × 3", "33"),
        ("12+3*4", "24"),
        ("-(2+3)", "-5"),
        ("1,5 ÷ 2", "0.75"),
        ("1/3", "0.333333333333"),
    ],
)
def test_arithmetic(expression, expected):
    assert calculate(expression).result == expected


@pytest.mark.parametrize(
    "expression", ["1/0", "2**10", "__import__('os')", "(1+2", "9" * 257, "999999999999999*9"]
)
def test_rejects_invalid_or_unbounded_input(expression):
    with pytest.raises(ExpressionError):
        calculate(expression)


def test_steps_follow_precedence():
    assert calculate("2+3*4").steps == ["3 × 4 = 12", "2 + 12 = 14"]


def test_accepts_handwritten_leading_zeroes():
    assert calculate("000.5+.25").result == "0.75"
