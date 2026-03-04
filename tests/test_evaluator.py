import pytest

from inkcalc.evaluator import ExpressionError, calculate


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("(9 + 2) × 3", "33"),
        ("12+3*4", "24"),
        ("-5 + 2", "-3"),
        ("0.1 + 0.2", "0.3"),
        ("1,5 ÷ 2", "0.75"),
        ("1/3", "0.333333333333"),
        ("-(2+3)", "-5"),
        ("0 * -2", "0"),
        ("2--3", "5"),
    ],
)
def test_arithmetic(expression, expected):
    assert calculate(expression).result == expected


@pytest.mark.parametrize(
    "expression",
    [
        "",
        "1/0",
        "2**10",
        "7//2",
        "__import__('os')",
        "True",
        "1e9",
        "[1]",
        "(1+2",
        "2(3)",
        "9" * 257,
        "999999999999999*9",
        "0x12",
        "1_000",
        ".",
    ],
)
def test_rejects_invalid_or_unbounded_input(expression):
    with pytest.raises(ExpressionError):
        calculate(expression)


def test_steps_follow_precedence():
    assert calculate("2+3*4").steps == ["3 × 4 = 12", "2 + 12 = 14"]


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("09+02", "11"),
        ("000.5+.25", "0.75"),
        ("00.", "0"),
    ],
)
def test_accepts_handwritten_leading_zeroes(expression, expected):
    assert calculate(expression).result == expected
