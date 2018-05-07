# -*- coding: utf-8 -*-
"""
Module for testing the Solver-Engine interface
"""

# pylint: disable=R0201, C0103, W0612, C0111, protected-access

import pytest
from pysolveengine.mipmodel import MIPModel, Expr, Operator, Var, Constraint, VarType, INF


def var(name="x", lb=0, ub=1, vartype=VarType.CONTINIOUS):
    return Var(name, lb=lb, ub=ub, vartype=vartype)


class TestMIPModel:
    # @httpretty.activate
    # def test_start_solver(self):
    #     httpretty.register_uri(httpretty.POST, MIPModel.BASEURL + "/123/start", body="")
    #     m = MIPModel(token="abc", filename="a.lp")
    #     m._id = "123"
    #     m._start_solver()
    #     assert httpretty.last_request().headers["authorization"] == "Bearer abc"

    def test_add_var(self):
        v = MIPModel(token="a").add_var("v", lb=12, ub=34, vartype=VarType.CONTINIOUS)
        assert v.lb == 12
        assert v.ub == 34
        assert v.name == "v"
        assert v.vartype == VarType.CONTINIOUS

    def test_add_continuous_var(self):
        v = MIPModel(token="a").add_continuous_var("v", lb=12, ub=34)
        assert v.lb == 12
        assert v.ub == 34
        assert v.name == "v"
        assert v.vartype == VarType.CONTINIOUS

    def test_unique_var_names(self):
        m = MIPModel("a")
        v1 = m.add_continuous_var("v")
        with pytest.raises(ValueError):
            v2 = m.add_var("v")

    def test_integer_var(self):
        v = MIPModel(token="a").add_integer_var("v", lb=12, ub=34)
        assert v.lb == 12
        assert v.ub == 34
        assert v.name == "v"
        assert v.vartype == VarType.INTEGER

    def test_binary_var(self):
        v = MIPModel(token="a").add_binary_var("v")
        assert v.lb == 0
        assert v.ub == 1
        assert v.name == "v"
        assert v.vartype == VarType.INTEGER

    def test_add_constriant(self):
        with pytest.raises(ValueError):
            MIPModel("a").add_constraint(constr=Expr())
        with pytest.raises(ValueError):
            MIPModel("a").add_constraint(constr=12)

    def test_obj(self):
        with pytest.raises(ValueError):
            x = MIPModel("a").obj
        m = MIPModel("a")
        m._obj = m._obj._replace(value=12)
        assert m.obj == 12

    def test_set_obj(self):
        m = MIPModel("a")
        m.set_obj(Expr(12))
        assert m._obj.expr.lpstr() == "12"

    def test_get_file_str(self):
        m = MIPModel("a")
        x = m.add_integer_var('x', lb=0, ub=1)
        y = m.add_integer_var('y')
        m.add_constraint(x >= 2)
        m.set_obj(x)
        m.set_to_minimize()
        result = "Minimize\nx\nSubject To\nx >= 2\nBounds\n0 <= x <= 1\n-inf <= y <= inf\nGeneral\nx y\nEnd"
        result2 = "Minimize\nx\nSubject To\nx >= 2\nBounds\n-inf <= y <= inf\n0 <= x <= 1\nGeneral\ny x\nEnd"
        # print(m._get_file_str())
        # print(result)
        assert m._get_file_str() == result or m._get_file_str() == result2


class TestConstraint:
    def test_format_str(self):
        assert Constraint(var(), Operator.GEQ, 0)._format_str("x", 2) == "x >= 2"
        assert Constraint(var(), "<=", 0)._format_str("x", 2) == "x <= 2"
        assert Constraint(var(), "<=", 0)._format_str(Expr(4), var()) == "4 <= x"
        assert str(Constraint(var(), "<=", 2)) == "x <= 2"
        assert str(Constraint(var(), "<=", Expr(2))) == "x <= 2"
        with pytest.raises(ValueError):
            Constraint("x", "<=", 2)
        with pytest.raises(ValueError):
            Constraint(3, "<=", 2)

    def test_lpstr(self):
        assert Constraint(var(), "<=", 2).lpstr() == "x <= 2"

        c = Constraint(var(), "<=", var("y")).lpstr()
        assert c == "x - y <= 0" or c == "- y + x <= 0"

        d = Constraint(var()+12, "<=", var("y")).lpstr()
        assert d == "x - y <= -12" or d == "- y + x <= -12"

        e = Constraint(var()+12, "<=", var("y")-12).lpstr()
        assert e == "x - y <= -24" or e == "- y + x <= -24"

        with pytest.raises(ValueError):
            Constraint(2, "<=", 1).lpstr()

        with pytest.raises(ValueError):
            Constraint(Expr(2), "<=", Expr(1)).lpstr()

class TestExpr:
    def test_add_term(self):
        x = var()
        assert Expr(2).add_term(x, 3).variables[x] == 3

    def test_lpstr(self):
        e = Expr(2).add_term(var(), 3).add_term(var("y"), -4)
        assert e.lpstr() == "- 4 y + 3 x + 2" or e.lpstr() == "3 x - 4 y + 2"
        f = Expr(0).add_term(var(), 3).add_term(var("y"), -4)
        assert f.lpstr() == "- 4 y + 3 x" or f.lpstr() == "3 x - 4 y"

    def test_is_constant(self):
        assert Expr(2).is_constant
        assert not var().is_constant

    def test_equals(self):
        e = Expr(2)
        assert not e.equals(2)
        assert not e.equals(Expr())
        assert e.equals(Expr(2))

        e = Expr(0)
        e.variables[1] = 2
        f = Expr(0)
        f.variables[1] = 2
        assert e.equals(f)
        g = Expr(0)
        g.variables[1] = 3
        assert not e.equals(g)

    def var_is_unchanged(self, variable):
        assert variable.variables == {variable:1}
        assert variable.constant == 0
        assert isinstance(variable, Var)

    def test_add(self):
        x, y = var(), var("y")
        e = x + y
        assert e.variables == {x: 1, y: 1}
        assert e.constant == 0
        assert e.equals(y + x)

        e = x + 5
        assert e.variables == {x: 1}
        assert e.constant == 5
        assert e.equals(5 + x)

        e = (x+y+1) + (x+2)
        assert e.variables == {x: 2, y: 1}
        assert e.constant == 3

        self.var_is_unchanged(x)
        self.var_is_unchanged(y)

    def test_sub(self):
        x, y = var(), var("y")
        e = x - y
        assert e.variables == {x: 1, y: -1}
        assert e.constant == 0
        assert e.equals(-(y-x))

        e = x - 5
        assert e.variables == {x: 1}
        assert e.constant == -5
        assert e.equals(-(5-x))

        self.var_is_unchanged(x)
        self.var_is_unchanged(y)

    def test_mul(self):
        x = var()
        e = 5*x
        assert e.variables == {x: 5}
        assert e.constant == 0
        assert e.equals(x*5)

        self.var_is_unchanged(x)

    def test_iadd(self):
        x, y, z, t = var(), var("y"), var("z"), var("t")

        t += 0
        assert not isinstance(t, Var)
        assert isinstance(t, Expr)
        assert t.constant == 0

        e = Expr(5)
        e += y
        assert e.equals(y + 5)

        e = Expr(2)
        e += 3
        assert e.equals(Expr(5))

        e = 2*y + 2
        e += 3*z
        assert e.equals(2*y + 2 + 3*z)

        self.var_is_unchanged(x)
        self.var_is_unchanged(y)
        self.var_is_unchanged(z)

    def test_imul(self):
        e = Expr(2)
        e *= 4
        assert e.equals(Expr(8))

        x = var()
        e = Expr(2)
        with pytest.raises(ValueError):
            e *= x

        y = var("y")
        y *= 5
        assert not isinstance(y, Var)

        self.var_is_unchanged(x)

    def test_neg(self):
        x = var()
        e = -x
        assert e.variables == {x: -1}
        assert e.constant == 0
        self.var_is_unchanged(x)

    def test_le(self):
        e1 = Expr(1)
        e2 = Expr(2)
        c = e1 <= e2
        assert isinstance(c, Constraint)
        assert c._lhs == e1
        assert c._rhs == e2
        assert c._operator == "<="

        d = e1 <= 1
        assert isinstance(d, Constraint)
        assert d._lhs == e1
        assert d._rhs == 1
        assert d._operator == "<="

        e = 1 <= e1
        assert isinstance(e, Constraint)
        assert e._lhs == e1
        assert e._rhs == 1
        assert e._operator == ">="

    def test_ge(self):
        e1 = Expr(1)
        e2 = Expr(2)
        c = e1 >= e2
        assert isinstance(c, Constraint)
        assert c._lhs == e1
        assert c._rhs == e2
        assert c._operator == ">="

    def test_eq(self):
        e1 = Expr(1)
        e2 = Expr(2)
        c = e1 == e2
        assert isinstance(c, Constraint)
        assert c._lhs == e1
        assert c._rhs == e2
        assert c._operator == "="


class TestVar:
    def test_value(self):
        with pytest.raises(ValueError):
            v = var("v").value
        v = var("v")
        v.set_value(10)
        assert v.value == 10

    def test_name(self):
        assert var("v123").name == "v123"
        with pytest.raises(AttributeError):
            var("v").name = 'a'

    def test_lpstr_bounds(self):
        assert var("v", lb=-12, ub=34).lpstr_bounds() == "-12 <= v <= 34"
        assert var("v", lb=-INF, ub=INF).lpstr_bounds() == "-inf <= v <= inf"
        assert var("v", lb=INF, ub=-INF).lpstr_bounds() == "inf <= v <= -inf"
        assert var("v", lb=1, ub=INF).lpstr_bounds() == "1 <= v <= inf"
        assert var("v", lb=-INF, ub=1).lpstr_bounds() == "-inf <= v <= 1"

    def test_lpstr_type(self):
        assert var("x", vartype=VarType.CONTINIOUS).lpstr_type() == ""
        assert var("x", vartype=VarType.INTEGER).lpstr_type() == "x"

    def test_type(self):
        assert var("y", vartype=VarType.INTEGER).vartype == VarType.INTEGER
        assert var("y", vartype=VarType.CONTINIOUS).vartype == VarType.CONTINIOUS
        assert var("y").vartype == VarType.CONTINIOUS

    def test_expr(self):
        assert isinstance(var("y"), Expr)
