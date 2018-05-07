# -*- coding: utf-8 -*-
"""
Module for testing the Solver-Engine interface
"""

# pylint: disable=R0201, C0103, W0612, C0111, protected-access

import pytest
from pysolveengine.satmodel import SATModel, Var, AND, OR, XOR, IMP, EQ, NE, NEG


def do_test_expr(expr, cls, result_str):
    assert isinstance(expr, cls)
    assert str(expr) == result_str


def varx():
    return Var(name="x", idd=1)


def vary():
    return Var(name="y", idd=2)


def varz():
    return Var(name="z", idd=3)


def varsxyz():
    return varx(), vary(), varz()


def vars_are_unchanged(x, y, z):
    assert x.name == "x"
    assert x.id == 1
    assert y.name == "y"
    assert y.id == 2
    assert z.name == "z"
    assert z.id == 3


class TestSATModel:
    def test_addvar(self):
        model = SATModel(token="a")
        x = model.add_variable("x")
        y = model.add_variable("y")
        z = model.add_variable("z")
        vars_are_unchanged(x, y, z)

    def test_get_file_str(self):
        model = SATModel(token="a")
        x = model.add_variable("x")
        y = model.add_variable("y")
        z = model.add_variable("z")
        model.add_constraint((x & y) | z)
        model.add_constraint(-x & -y)
        result = model._get_file_str()
        assert result == "p cnf 3 4\n1 3 0\n2 3 0\n-1 0\n-2 0"


class TestVar:
    def test_init(self):
        x = varx()
        assert x.name == "x"
        assert x.id == 1
        assert str(x) == "x"

    def test_value(self):
        x = varx()
        with pytest.raises(ValueError):
            t = x.value
        with pytest.raises(ValueError):
            x.set_value(0)
        with pytest.raises(ValueError):
            x.set_value(1)
        with pytest.raises(ValueError):
            x.set_value("0")
        with pytest.raises(ValueError):
            x.set_value(None)
        x.set_value(True)
        assert x.value


class TestExpr:
    def test_and(self):
        x, y, z = varsxyz()
        do_test_expr(x & y, AND, "(x & y)")
        do_test_expr(x & y & z, AND, "(x & y & z)")
        do_test_expr((x & y) & z, AND, "(x & y & z)")
        do_test_expr(x & (y & z), AND, "(x & y & z)")
        vars_are_unchanged(x, y, z)

    def test_or(self):
        x, y, z = varsxyz()
        do_test_expr(x | y, OR, "(x | y)")
        do_test_expr(x | y | z, OR, "(x | y | z)")
        do_test_expr((x | y) | z, OR, "(x | y | z)")
        vars_are_unchanged(x, y, z)

    def test_xor(self):
        x, y, z = varsxyz()
        do_test_expr(x ^ y, XOR, "(x ^ y)")
        do_test_expr(x ^ y ^ z, XOR, "((x ^ y) ^ z)")
        vars_are_unchanged(x, y, z)

    def test_eq(self):
        x, y, z = varsxyz()
        do_test_expr(x == y, EQ, "(x == y)")
        do_test_expr((x == y) == z, EQ, "((x == y) == z)")
        vars_are_unchanged(x, y, z)

    def test_ne(self):
        x, y, z = varsxyz()
        do_test_expr(x != y, NE, "(x != y)")
        do_test_expr((x != y) != z, NE, "((x != y) != z)")
        vars_are_unchanged(x, y, z)

    def test_impl(self):
        x, y, z = varsxyz()
        do_test_expr(x <= y, IMP, "(x <= y)")
        do_test_expr((x <= y) <= z, IMP, "((x <= y) <= z)")
        vars_are_unchanged(x, y, z)

    def test_neg(self):
        x, y, z = varsxyz()
        do_test_expr(-x, NEG, "!x")
        do_test_expr(-(-x), Var, "x")
        vars_are_unchanged(x, y, z)


class TestConvertToCnf:
    def test_var(self):
        do_test_expr(varx().convert_to_cnf(), AND, "((x))")

    def test_neg(self):
        x, y, z = varsxyz()
        a = -x
        do_test_expr(a.convert_to_cnf(), AND, "((!x))")
        b = -(x | y | z)
        do_test_expr(b.convert_to_cnf(), AND, "((!x) & (!y) & (!z))")
        c = -(x & y & z)
        do_test_expr(c.convert_to_cnf(), AND, "((!x | !y | !z))")
        vars_are_unchanged(x, y, z)

    def test_or(self):
        x, y, z = varsxyz()
        a = x | y
        do_test_expr(a.convert_to_cnf(), AND, "((x | y))")
        b = ((x & y) | z)
        do_test_expr(b.convert_to_cnf(), AND, "((x | z) & (y | z))")
        c = ((x & y) | (x & z))
        do_test_expr(c.convert_to_cnf(), AND,
                     "((x | x) & (x | z) & (y | x) & (y | z))")
        vars_are_unchanged(x, y, z)

    def test_and(self):
        x, y, z = varsxyz()
        a = x & y
        do_test_expr(a.convert_to_cnf(), AND, "((x) & (y))")
        b = (x | y) & (x | z)
        do_test_expr(b.convert_to_cnf(), AND, "((x | y) & (x | z))")
        vars_are_unchanged(x, y, z)

    def test_xor(self):
        x, y, z = varsxyz()
        a = x ^ y
        do_test_expr(a.convert_to_cnf(), AND,
                     "((x | !x) & (x | y) & (!y | !x) & (!y | y))")
        vars_are_unchanged(x, y, z)

    def test_eq(self):
        x, y, z = varsxyz()
        a = x == y
        do_test_expr(a.convert_to_cnf(), AND,
                     "((x | !x) & (x | !y) & (y | !x) & (y | !y))")
        vars_are_unchanged(x, y, z)

    def test_implication(self):
        x, y, z = varsxyz()
        a = x <= y
        do_test_expr(a.convert_to_cnf(), AND, "((!y | x))")
        vars_are_unchanged(x, y, z)

    def test_ne(self):
        x, y, z = varsxyz()
        a = x != y
        do_test_expr(a.convert_to_cnf(), AND, "((!x | !y) & (x | y))")
        vars_are_unchanged(x, y, z)
