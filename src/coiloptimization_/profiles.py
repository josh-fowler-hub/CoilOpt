from __future__ import annotations

import ast
import math
from typing import Callable, Dict, List, Tuple


# Simple safe expression evaluator supporting math funcs and variable x
_ALLOWED_MATH_FUNCS = {k: getattr(math, k) for k in [
    'sin','cos','tan','asin','acos','atan','sinh','cosh','exp','log','log10','sqrt','pow','fabs'
]}
_ALLOWED_NAMES = set(_ALLOWED_MATH_FUNCS.keys()) | {'x', 'z'}


class _EvalError(ValueError):
    pass


def _eval_node(node, names):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, names)
    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left, names)
        right = _eval_node(node.right, names)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Pow):
            return left ** right
        if isinstance(node.op, ast.Mod):
            return left % right
        raise _EvalError(f"Unsupported op: {node.op}")
    if isinstance(node, ast.UnaryOp):
        val = _eval_node(node.operand, names)
        if isinstance(node.op, ast.UAdd):
            return +val
        if isinstance(node.op, ast.USub):
            return -val
        raise _EvalError(f"Unsupported unary op: {node.op}")
    if hasattr(ast, 'Constant'):
        if isinstance(node, ast.Constant):
            return node.value
    else:
        if isinstance(node, ast.Num):
            return node.n
    if isinstance(node, ast.Name):
        if node.id in names:
            return names[node.id]
        raise _EvalError(f"Name {node.id} not allowed")
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in _ALLOWED_MATH_FUNCS:
            func = _ALLOWED_MATH_FUNCS[node.func.id]
            args = [_eval_node(a, names) for a in node.args]
            return func(*args)
        raise _EvalError("Only simple math function calls allowed")
    raise _EvalError(f"Unsupported AST node: {type(node)}")


def eval_expr(expr: str, x: float, z: float | None = None) -> float:
    """Evaluate expression string safely with variables x and optionally z."""
    try:
        node = ast.parse(expr, mode='eval')
    except Exception as e:
        raise _EvalError(str(e))
    # security: traverse AST to check names
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            if n.id not in _ALLOWED_NAMES:
                raise _EvalError(f"Name {n.id} not allowed in expression")
        if isinstance(n, ast.Call):
            if not isinstance(n.func, ast.Name) or n.func.id not in _ALLOWED_MATH_FUNCS:
                raise _EvalError("Only whitelisted math functions allowed")
    names = {'x': x}
    if z is not None:
        names['z'] = z
    # If expression references 'z' but z not provided, default it to x for backward compatibility
    if 'z' not in names:
        names['z'] = x
    return float(_eval_node(node, names))


def make_profile_from_equation(equation: str) -> Callable[[float], float]:
    def profile(x: float, z: float | None = None) -> float:
        return eval_expr(equation, x, z)

    return profile


def make_profile_from_points(points: List[Dict[str, float]]) -> Callable[[float], float]:
    # points: list of dicts with keys x_m (or z_m) and temp_c
    # accept either x_m or z_m as coordinate key
    pts_raw = []
    for p in points:
        if 'x_m' in p:
            pts_raw.append((float(p['x_m']), float(p['temp_c'])))
        elif 'z_m' in p:
            pts_raw.append((float(p['z_m']), float(p['temp_c'])))
        else:
            raise _EvalError('Points must have x_m or z_m keys')
    pts = sorted(pts_raw, key=lambda t: t[0])

    def profile(x: float, z: float | None = None) -> float:
        # use z if provided (vertical coordinate), else x
        coord = z if z is not None else x
        coord = coord
        if coord <= pts[0][0]:
            return pts[0][1]
        if coord >= pts[-1][0]:
            return pts[-1][1]
        # find interval
        for i in range(len(pts) - 1):
            x0, t0 = pts[i]
            x1, t1 = pts[i + 1]
            if x0 <= coord <= x1:
                # linear interpolation
                if x1 == x0:
                    return t0
                return t0 + (t1 - t0) * ((coord - x0) / (x1 - x0))
        # fallback
        return pts[-1][1]

    return profile