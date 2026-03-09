"""Bounded arithmetic interpreter; no eval, calls, attributes or names."""

import ast
import re
from dataclasses import dataclass
from decimal import Decimal, DecimalException, localcontext


class ExpressionError(ValueError):
    """An expression is invalid or outside the calculator's limits."""


@dataclass(frozen=True)
class Calculation:
    expression: str
    result: str
    steps: list[str]


def format_number(value: Decimal) -> str:
    text = format(value, ".12f").rstrip("0").rstrip(".")
    return "0" if text in {"", "-0"} else text


def calculate(expression: str) -> Calculation:
    normalized = expression.strip().translate(
        str.maketrans({"×": "*", "÷": "/", "−": "-", ",": "."})
    )
    if not normalized or len(normalized) > 256:
        raise ExpressionError("Enter an expression between 1 and 256 characters.")
    if any(char not in "0123456789.+-*/() \t" for char in normalized):
        raise ExpressionError("Use only numbers, +, −, ×, ÷ and parentheses.")

    # Handwritten numbers may contain leading zeroes, which Python's parser rejects.
    def canonical_number(match: re.Match) -> str:
        integer, dot, fraction = match.group().partition(".")
        return str(int(integer or "0")) + dot + fraction

    normalized = re.sub(r"\d+(?:\.\d*)?|\.\d+", canonical_number, normalized)
    try:
        tree = ast.parse(normalized, mode="eval")
    except (SyntaxError, ValueError, RecursionError) as exc:
        raise ExpressionError(
            "The expression is incomplete or the parentheses are misplaced."
        ) from exc
    if sum(1 for _ in ast.walk(tree)) > 96:
        raise ExpressionError("The expression contains too many operations.")
    steps: list[str] = []

    def visit(node: ast.AST, depth: int = 0) -> Decimal:
        if depth > 24:
            raise ExpressionError("The expression is nested too deeply.")
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            value = Decimal(ast.get_source_segment(normalized, node) or "0")
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            operand = visit(node.operand, depth + 1)
            value = -operand if isinstance(node.op, ast.USub) else operand
        elif isinstance(node, ast.BinOp) and type(node.op) in (ast.Add, ast.Sub, ast.Mult, ast.Div):
            left, right = visit(node.left, depth + 1), visit(node.right, depth + 1)
            if isinstance(node.op, ast.Add):
                value, symbol = left + right, "+"
            elif isinstance(node.op, ast.Sub):
                value, symbol = left - right, "−"
            elif isinstance(node.op, ast.Mult):
                value, symbol = left * right, "×"
            else:
                if right == 0:
                    raise ExpressionError("Division by zero is undefined.")
                value, symbol = left / right, "÷"
            steps.append(
                f"{format_number(left)} {symbol} {format_number(right)} = {format_number(value)}"
            )
        else:
            raise ExpressionError("This operation is not supported.")
        if not value.is_finite() or abs(value) > Decimal("1e15"):
            raise ExpressionError("The result exceeds the limit of 10¹⁵.")
        return value

    try:
        with localcontext() as context:
            context.prec = 40
            value = visit(tree.body)
    except (DecimalException, OverflowError) as exc:
        raise ExpressionError("This calculation exceeds the numerical limits.") from exc
    return Calculation(normalized, format_number(value), steps)
