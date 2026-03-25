"""
High-level semantic groups of AST node types.

This module defines reusable "kinds" (domains) that group multiple AST node
types under a single conceptual category, such as loops, assignments or scopes.

The goal is to allow matcher rules to operate on semantic concepts instead of
low-level node names.

Examples:
    match("For|While")
    match(K.loop)

    match("Assign|AnnAssign")
    match(K.assignment)

Kinds improve readability, reduce duplication, and make rules more robust
against changes in underlying AST structures.

Each kind resolves to a set of astroid node classes via ``Domain.resolve()``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Iterable, Type

from astroid import nodes


NodeCls = Type[nodes.NodeNG]


@dataclass
class Domain:
    """Represents a semantic group of AST node types.

    A Domain encapsulates a set of related astroid node classes and provides
    a ``resolve()`` method returning those classes.

    Domains are used by the matcher DSL to express patterns at a higher level
    than individual node types.

    Example:
        K.loop resolves to {For, While}

    Notes:
        Domains are composable and may internally reference multiple AST types.
    """
    name: str
    _all: FrozenSet[NodeCls]

    def resolve(self) -> FrozenSet[NodeCls]:
        return self._all

    def __iter__(self):
        return iter(self._all)


def _domain(name: str, all_types: Iterable[NodeCls], **members: NodeCls) -> Domain:
    d = Domain(name=name, _all=frozenset(all_types))
    for k, v in members.items():
        setattr(d, k, v)
    return d


class K:
    """Namespace of predefined AST domains (kinds).

    Provides commonly used semantic groupings such as:

        K.loop          -> For, While
        K.assignment    -> Assign, AnnAssign
        K.scope         -> FunctionDef, ClassDef, Module
        K.import_       -> Import, ImportFrom

    Intended to be used with the matcher DSL:

        match(K.loop)
        match(K.assignment)

    This allows writing rules that are independent of specific AST node names.
    """

    # --- definitions / scope ---
    scope = _domain(
        "scope",
        all_types={nodes.Module, nodes.FunctionDef, nodes.AsyncFunctionDef, nodes.ClassDef, nodes.Lambda},
        module=nodes.Module,
        function=nodes.FunctionDef,
        async_function=nodes.AsyncFunctionDef,
        class_=nodes.ClassDef,
        lambda_=nodes.Lambda,
    )

    # --- loops ---
    loop = _domain(
        "loop",
        all_types={nodes.For, nodes.AsyncFor, nodes.While},
        for_=nodes.For,
        async_for=nodes.AsyncFor,
        while_=nodes.While,
    )

    # --- assignment family ---
    assignment = _domain(
        "assignment",
        all_types={nodes.Assign, nodes.AnnAssign, nodes.AugAssign, nodes.NamedExpr},
        assign=nodes.Assign,
        ann=nodes.AnnAssign,
        aug=nodes.AugAssign,
        named=nodes.NamedExpr,
    )

    # --- imports ---
    import_ = _domain(
        "import",
        all_types={nodes.Import, nodes.ImportFrom},
        import_stmt=nodes.Import,
        from_=nodes.ImportFrom,
    )

    # --- termination / jump ---
    terminator = _domain(
        "terminator",
        all_types={nodes.Return, nodes.Raise, nodes.Break, nodes.Continue, nodes.Pass, nodes.Yield, nodes.YieldFrom},
        return_=nodes.Return,
        raise_=nodes.Raise,
        break_=nodes.Break,
        continue_=nodes.Continue,
        pass_=nodes.Pass,
        yield_=nodes.Yield,
        yield_from=nodes.YieldFrom,
    )

    # --- expressions (core) ---
    expr = _domain(
        "expr",
        all_types={
            nodes.Call, nodes.Attribute, nodes.Name, nodes.Const,
            nodes.BinOp, nodes.BoolOp, nodes.UnaryOp, nodes.Compare,
            nodes.Subscript, nodes.Slice, nodes.Starred
        },
        call=nodes.Call,
        attr=nodes.Attribute,
        name_=nodes.Name,
        const=nodes.Const,
        binop=nodes.BinOp,
        boolop=nodes.BoolOp,
        unary=nodes.UnaryOp,
        compare=nodes.Compare,
        subscript=nodes.Subscript,
        slice_=nodes.Slice,
        starred=nodes.Starred,
    )

    # --- collections ---
    collection = _domain(
        "collection",
        all_types={nodes.List, nodes.Tuple, nodes.Set, nodes.Dict},
        list_=nodes.List,
        tuple_=nodes.Tuple,
        set_=nodes.Set,
        dict_=nodes.Dict,
    )

    # --- comprehensions ---
    comprehension = _domain(
        "comprehension",
        all_types={nodes.ListComp, nodes.SetComp, nodes.DictComp, nodes.GeneratorExp, nodes.Comprehension},
        list_comp=nodes.ListComp,
        set_comp=nodes.SetComp,
        dict_comp=nodes.DictComp,
        gen_exp=nodes.GeneratorExp,
        comp=nodes.Comprehension,
    )

    # --- control flow (broader) ---
    control_flow = _domain(
        "control_flow",
        all_types={nodes.If, nodes.For, nodes.AsyncFor, nodes.While, nodes.Try, nodes.TryStar, nodes.With, nodes.AsyncWith, nodes.Match},
        if_=nodes.If,
        for_=nodes.For,
        async_for=nodes.AsyncFor,
        while_=nodes.While,
        try_=nodes.Try,
        try_star=nodes.TryStar,
        with_=nodes.With,
        async_with=nodes.AsyncWith,
        match_=nodes.Match,
    )

    # --- pattern matching (Python 3.10+) ---
    pattern = _domain(
        "pattern",
        all_types={
            nodes.Match, nodes.MatchCase, nodes.MatchAs, nodes.MatchClass, nodes.MatchMapping,
            nodes.MatchOr, nodes.MatchSequence, nodes.MatchSingleton, nodes.MatchStar, nodes.MatchValue
        },
        match=nodes.Match,
        case=nodes.MatchCase,
        as_=nodes.MatchAs,
        class_=nodes.MatchClass,
        mapping=nodes.MatchMapping,
        or_=nodes.MatchOr,
        seq=nodes.MatchSequence,
        singleton=nodes.MatchSingleton,
        star=nodes.MatchStar,
        value=nodes.MatchValue,
    )

  
    func = _domain(
        "func",
        all_types={nodes.FunctionDef, nodes.AsyncFunctionDef, nodes.Lambda},
        def_=nodes.FunctionDef,
        async_def=nodes.AsyncFunctionDef,
        lambda_=nodes.Lambda,
    )