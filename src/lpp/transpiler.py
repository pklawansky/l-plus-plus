# src/lpp/transpiler.py
from .ast_nodes import *
from .prelude import inject_prelude

INDENT = "    "

class Transpiler:
    def transpile(self, program: Program) -> str:
        lines = [self._stmt(node, 0) for node in program.body]
        python_src = "\n".join(lines) + "\n"
        return inject_prelude(python_src)

    # --- Statements ---

    def _stmt(self, node: Statement, depth: int) -> str:
        pad = INDENT * depth
        match node:
            case FunctionDef():
                return self._fn(node, depth)
            case ClassDef():
                return self._cls(node, depth)
            case Assignment(target, value):
                tgt = target if isinstance(target, str) else self._expr(target)
                return f"{pad}{tgt} = {self._expr(value)}"
            case AugAssignment(target, op, value):
                tgt = target if isinstance(target, str) else self._expr(target)
                return f"{pad}{tgt} {op} {self._expr(value)}"
            case UnpackAssignment(targets, value):
                tgt = ", ".join(
                    f"*{self._expr(t.value)}" if isinstance(t, Spread) else self._expr(t)
                    for t in targets
                )
                return f"{pad}{tgt} = {self._expr(value)}"
            case AppendStatement(target, value):
                return f"{pad}{self._expr(target)}.append({self._expr(value)})"
            case IfStatement():
                return self._if(node, depth)
            case ForStatement():
                return self._for(node, depth)
            case DoStatement(condition, body, else_body):
                lines = [f"{pad}while {self._expr(condition)}:"]
                lines += [self._stmt(s, depth + 1) for s in body]
                if else_body:
                    lines.append(f"{pad}else:")
                    lines += [self._stmt(s, depth + 1) for s in else_body]
                return "\n".join(lines)
            case TryStatement():
                return self._try(node, depth)
            case RetStatement(value):
                val = f" {self._expr(value)}" if value is not None else ""
                return f"{pad}return{val}"
            case UseStatement(imports):
                return "\n".join(f"{pad}{self._use(imp)}" for imp in imports)
            case AliasStatement(name, target):
                return f"{pad}{name} = {self._expr(target)}"
            case BreakStatement():
                return f"{pad}break"
            case ContinueStatement():
                return f"{pad}continue"
            case GlobalStatement(names):
                return f"{pad}global {', '.join(names)}"
            case NonlocalStatement(names):
                return f"{pad}nonlocal {', '.join(names)}"
            case AssertStatement(test, msg):
                if msg is None:
                    return f"{pad}assert {self._expr(test)}"
                return f"{pad}assert {self._expr(test)}, {self._expr(msg)}"
            case DelStatement(targets):
                tgts = ", ".join(self._expr(t) for t in targets)
                return f"{pad}del {tgts}"
            case RaiseStatement(exc, cause):
                if exc is None:
                    return f"{pad}raise"
                elif cause is None:
                    return f"{pad}raise {self._expr(exc)}"
                else:
                    return f"{pad}raise {self._expr(exc)} from {self._expr(cause)}"
            case WithStatement(items, body):
                parts = []
                for expr, name in items:
                    parts.append(f"{self._expr(expr)} as {name}" if name else self._expr(expr))
                header = f"{pad}with {', '.join(parts)}:"
                lines = [header] + [self._stmt(s, depth + 1) for s in body]
                return "\n".join(lines)
            case ExprStatement(expr):
                return f"{pad}{self._expr(expr)}"
            case PassStatement():
                return f"{pad}pass"
            case YieldStatement(value, is_from):
                if value is None:
                    return f"{pad}yield"
                keyword = "yield from" if is_from else "yield"
                return f"{pad}{keyword} {self._expr(value)}"
            case _:
                raise NotImplementedError(f"Unknown statement: {type(node)}")

    # Python dunder names that L++ @-methods should emit as __name__
    _DUNDER_NAMES = frozenset({
        "init", "del", "repr", "str", "bytes", "format",
        "lt", "le", "eq", "ne", "gt", "ge",
        "hash", "bool", "len", "length_hint",
        "getitem", "setitem", "delitem", "missing", "iter", "reversed", "next",
        "contains", "add", "radd", "iadd", "sub", "rsub", "isub",
        "mul", "rmul", "imul", "truediv", "rtruediv", "itruediv",
        "floordiv", "rfloordiv", "ifloordiv", "mod", "rmod", "imod",
        "pow", "rpow", "ipow", "and", "rand", "iand",
        "or", "ror", "ior", "xor", "rxor", "ixor",
        "lshift", "rshift", "ilshift", "irshift",
        "neg", "pos", "abs", "invert",
        "int", "float", "complex", "index",
        "enter", "exit", "call", "new",
        "get", "set", "delete", "set_name",
        "init_subclass", "class_getitem",
    })

    def _fn(self, node: FunctionDef, depth: int) -> str:
        pad = INDENT * depth
        params = []
        if node.is_method:
            params.append("self")
        for p in node.params:
            if p.kind == "var":
                params.append(f"*{p.name}")
            elif p.kind == "kw":
                params.append(f"**{p.name}")
            elif p.default is not None:
                params.append(f"{p.name}={self._expr(p.default)}")
            else:
                params.append(p.name)
        param_str = ", ".join(params)
        name = f"__{node.name}__" if node.is_method and node.name in self._DUNDER_NAMES else node.name
        lines = []
        for dec in node.decorators:
            lines.append(f"{pad}@{self._expr(dec)}")
        lines.append(f"{pad}def {name}({param_str}):")
        if not node.body:
            lines.append(f"{INDENT * (depth + 1)}pass")
        else:
            *body, last = node.body
            for s in body:
                lines.append(self._stmt(s, depth + 1))
            # Last statement: implicit return if it's an expression
            if isinstance(last, ExprStatement):
                lines.append(f"{INDENT * (depth + 1)}return {self._expr(last.expr)}")
            else:
                lines.append(self._stmt(last, depth + 1))
        return "\n".join(lines)

    def _cls(self, node: ClassDef, depth: int) -> str:
        pad = INDENT * depth
        base = f"({', '.join(node.bases)})" if node.bases else ""
        lines = []
        for dec in node.decorators:
            lines.append(f"{pad}@{self._expr(dec)}")
        lines.append(f"{pad}class {node.name}{base}:")
        for method in node.body:
            lines.append(self._fn(method, depth + 1))
        return "\n".join(lines)

    def _if(self, node: IfStatement, depth: int) -> str:
        pad = INDENT * depth
        lines = [f"{pad}if {self._expr(node.condition)}:"]
        lines += [self._stmt(s, depth + 1) for s in node.body]
        for cond, body in node.elifs:
            if cond is None:
                lines.append(f"{pad}else:")
            else:
                lines.append(f"{pad}elif {self._expr(cond)}:")
            lines += [self._stmt(s, depth + 1) for s in body]
        return "\n".join(lines)

    def _for(self, node: ForStatement, depth: int) -> str:
        pad = INDENT * depth
        targets = ", ".join(node.targets)
        lines = [f"{pad}for {targets} in {self._expr(node.iterable)}:"]
        lines += [self._stmt(s, depth + 1) for s in node.body]
        if node.else_body is not None:
            lines.append(f"{pad}else:")
            lines += [self._stmt(s, depth + 1) for s in node.else_body]
        return "\n".join(lines)

    def _try(self, node: TryStatement, depth: int) -> str:
        pad = INDENT * depth
        lines = [f"{pad}try:"]
        lines += [self._stmt(s, depth + 1) for s in node.body]
        for h in node.handlers:
            if isinstance(h.exc_type, list):
                exc_str = f"({', '.join(h.exc_type)})"
            else:
                exc_str = h.exc_type
            if exc_str and h.name:
                lines.append(f"{pad}except {exc_str} as {h.name}:")
            elif exc_str:
                lines.append(f"{pad}except {exc_str}:")
            else:
                lines.append(f"{pad}except:")
            lines += [self._stmt(s, depth + 1) for s in h.body]
        if node.finally_body:
            lines.append(f"{pad}finally:")
            lines += [self._stmt(s, depth + 1) for s in node.finally_body]
        return "\n".join(lines)

    def _use(self, imp: UseImport) -> str:
        if imp.item:
            alias_part = f" as {imp.alias}" if imp.alias else ""
            return f"from {imp.module} import {imp.item}{alias_part}"
        elif imp.alias:
            return f"import {imp.module} as {imp.alias}"
        else:
            return f"import {imp.module}"

    # --- Expressions ---

    def _expr(self, node: Expression) -> str:
        match node:
            case NumberLiteral(value):
                return str(value)
            case StringLiteral(parts):
                return self._string(parts)
            case Name(id):
                return id
            case SelfAttr(attr):
                return f"self.{attr}"
            case Attribute(obj, attr):
                return f"{self._expr(obj)}.{attr}"
            case Subscript(obj, key):
                return f"{self._expr(obj)}[{self._expr(key)}]"
            case Slice(start, stop, step):
                s = self._expr(start) if start is not None else ""
                e = self._expr(stop) if stop is not None else ""
                if step is not None:
                    return f"{s}:{e}:{self._expr(step)}"
                return f"{s}:{e}"
            case ChainedComparison(operands, ops):
                parts = [self._expr(operands[0])]
                for op, operand in zip(ops, operands[1:]):
                    parts += [op, self._expr(operand)]
                return " ".join(parts)
            case BinOp(left, op, right):
                return f"{self._expr(left)} {op} {self._expr(right)}"
            case UnaryOp(op, operand):
                py_op = "not " if op == "not" else op
                return f"{py_op}{self._expr(operand)}"
            case Call(func, args, kwargs):
                return self._call(func, args, kwargs)
            case ZeroArgCall(func):
                return f"{self._expr(func)}()"
            case Pipeline(steps):
                return self._pipeline(steps)
            case Lambda(params, body):
                return f"lambda {', '.join(params)}: {self._expr(body)}"
            case Compose(left, right):
                return f"(lambda *a, **kw: {self._expr(left)}({self._expr(right)}(*a, **kw)))"
            case TernaryOp(value, condition, else_value):
                return f"{self._expr(value)} if {self._expr(condition)} else {self._expr(else_value)}"
            case ListLiteral(elements):
                return f"[{', '.join(self._expr(e) for e in elements)}]"
            case DictLiteral(pairs):
                items = ", ".join(f"{self._expr(k)}: {self._expr(v)}" for k, v in pairs)
                return "{" + items + "}"
            case SetLiteral(elements):
                return "{" + ", ".join(self._expr(e) for e in elements) + "}"
            case Tuple(elements):
                return ", ".join(self._expr(e) for e in elements)
            case ListComp(elt, targets, iter, condition):
                target_str = ", ".join(targets)
                cond = f" if {self._expr(condition)}" if condition else ""
                return f"[{self._expr(elt)} for {target_str} in {self._expr(iter)}{cond}]"
            case DictComp(key, value, targets, iter, condition):
                target_str = ", ".join(targets)
                cond = f" if {self._expr(condition)}" if condition else ""
                return "{" + f"{self._expr(key)}: {self._expr(value)} for {target_str} in {self._expr(iter)}{cond}" + "}"
            case SetComp(elt, targets, iter, condition):
                target_str = ", ".join(targets)
                cond = f" if {self._expr(condition)}" if condition else ""
                return "{" + f"{self._expr(elt)} for {target_str} in {self._expr(iter)}{cond}" + "}"
            case Spread(value):
                return f"*{self._expr(value)}"
            case _:
                raise NotImplementedError(f"Unknown expression: {type(node)}")

    def _string(self, parts: list) -> str:
        if all(isinstance(p, str) for p in parts):
            inner = self._escape_str_content("".join(parts))
            return f'"{inner}"'
        inner = ""
        for part in parts:
            if isinstance(part, str):
                escaped = self._escape_str_content(part)
                inner += escaped.replace("{", "{{").replace("}", "}}")
            else:
                inner += "{" + self._expr(part) + "}"
        return f'f"{inner}"'

    @staticmethod
    def _escape_str_content(s: str) -> str:
        """Re-encode decoded string content for Python string literal output.

        Input is decoded Unicode (real newline, tab, backslash characters) as
        produced by the lexer — not raw source escape sequences. The \\r branch
        is included defensively; the lexer normalises \\r\\n to \\n at scan time
        so a carriage-return character cannot currently arrive here.
        Backslash is replaced first so later replacements don't double-escape
        the newly-added backslashes.
        """
        return (s
            .replace("\\", "\\\\")
            .replace('"',  '\\"')
            .replace("\n", "\\n")
            .replace("\t", "\\t")
            .replace("\r", "\\r")
        )

    def _call(self, func: Expression, args: list, kwargs: dict) -> str:
        all_args = [self._expr(a) for a in args]
        all_args += [f"{k}={self._expr(v)}" for k, v in kwargs.items()]
        return f"{self._expr(func)}({', '.join(all_args)})"

    def _pipeline(self, steps: list[Expression]) -> str:
        # r(10)|ma(x->x*2)|li!  →  li(ma(lambda x: x*2, r(10)))
        # Step 0 is the source; each subsequent step wraps the accumulated result
        result = self._expr(steps[0])
        for step in steps[1:]:
            if isinstance(step, ZeroArgCall):
                fn = self._expr(step.func)
                result = f"{fn}({result})"
            elif isinstance(step, Call):
                # Insert accumulated result after positional args, before kwargs
                # ma(x->x*2) → ma(lambda x: x*2, acc)
                # so(reverse=1) → so(acc, reverse=1)
                inner_args = [self._expr(a) for a in step.args]
                kw_args = [f"{k}={self._expr(v)}" for k, v in step.kwargs.items()]
                all_args = ", ".join(inner_args + [result] + kw_args)
                result = f"{self._expr(step.func)}({all_args})"
            else:
                result = f"{self._expr(step)}({result})"
        return result
