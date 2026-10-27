"""Step 5: the calculator. Every ratio is computed here, in code, with its arithmetic.

The definitions are the report audit's: operating margin on total revenue,
return on AVERAGE equity, debt including its current portion.
"""

import ast
import operator


def _val(facts: dict, concept: str, which: str = "current"):
    point = (facts.get(concept) or {}).get(which)
    return None if point is None else point["value"]


def _m(x: float) -> str:
    """Dollars in millions, as the statements print them."""
    return f"{x / 1e6:,.0f}"


def ratio(name: str, value, arithmetic: str, definition: str) -> dict:
    return {"name": name, "value": value, "arithmetic": arithmetic, "definition": definition}


def core_ratios(facts: dict, price: float | None) -> list[dict]:
    out = []
    rev, rev_prior = _val(facts, "total_revenue"), _val(facts, "total_revenue", "prior")
    if rev and rev_prior:
        g = rev / rev_prior - 1
        out.append(ratio("revenue_growth", g,
                         f"{_m(rev)} / {_m(rev_prior)} - 1 = {g:.2%}",
                         "total revenue this year / total revenue prior year - 1"))
    op = _val(facts, "operating_income")
    if op is not None and rev:
        m = op / rev
        out.append(ratio("operating_margin", m, f"{_m(op)} / {_m(rev)} = {m:.2%}",
                         "operating income / total revenue"))
    ni = _val(facts, "net_income")
    eq, eq_prior = _val(facts, "stockholders_equity"), _val(facts, "stockholders_equity", "prior")
    if ni is not None and eq and eq_prior:
        avg = (eq + eq_prior) / 2
        r = ni / avg
        out.append(ratio("return_on_average_equity", r,
                         f"{_m(ni)} / (({_m(eq)} + {_m(eq_prior)}) / 2 = {_m(avg)}) = {r:.2%}",
                         "net income / average of this and last year-end stockholders' equity"))
    debt_nc, debt_c = _val(facts, "long_term_debt_noncurrent"), _val(facts, "long_term_debt_current")
    if debt_nc is not None and eq:
        debt = debt_nc + (debt_c or 0)
        d = debt / eq
        out.append(ratio("debt_to_equity", d,
                         f"({_m(debt_nc)} + {_m(debt_c or 0)} current) / {_m(eq)} = {d:.2f}x",
                         "long-term debt including current portion / stockholders' equity"))
    cfo, capex = _val(facts, "cash_from_operations"), _val(facts, "capex")
    if cfo is not None and capex is not None:
        fcf = cfo - capex
        out.append(ratio("free_cash_flow", fcf, f"{_m(cfo)} - {_m(capex)} = {_m(fcf)} (USD millions)",
                         "cash from operations - additions to property and equipment"))
    eps = _val(facts, "diluted_eps")
    if price and eps:
        pe = price / eps
        out.append(ratio("pe_ratio", pe, f"{price:,.2f} / {eps:,.2f} = {pe:.1f}x",
                         "price given to the desk / latest fiscal year GAAP diluted EPS"))
    return out


def peer_margin(facts: dict) -> dict | None:
    rev, op = _val(facts, "total_revenue"), _val(facts, "operating_income")
    if not rev or op is None:
        return None
    m = op / rev
    return ratio("operating_margin", m, f"{_m(op)} / {_m(rev)} = {m:.2%}",
                 "operating income / total revenue")


# --- The calculator the Financial Analyst may call for more ratios -----------

_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def evaluate(expression: str) -> float:
    """Arithmetic only: numbers, + - * / and parentheses. Nothing else runs."""
    def walk(node):
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](walk(node.left), walk(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](walk(node.operand))
        raise ValueError("only numbers, + - * / and parentheses are allowed")
    return walk(ast.parse(expression.replace(",", ""), mode="eval"))
