# -*- coding: utf-8 -*-
"""Module for the Solver-Engine

This module contains code to build and solve MIP
models via the Solve-Engine.

"""

import itertools
from functools import reduce

from .basemodel import BaseModel, SolverStatusCode


class SATModel(BaseModel):
    """SATModel class

    allows to model SAT problems

    Attributes:
    token: the SolveEngine token provided by the website,
    this is necessary to connect to the solver

    filename: the filename that the uploaded file should have,
    default is model

    sleeptime: the time we should sleep between checks if the SolveEngine
    is finished solving the problem

    debug(boolean): active the debug output
    """

    def __init__(self, token, filename="model", sleeptime=2,
                 debug=False, interactive_mode=False, http_mode=False):
        super(SATModel, self).__init__(token, filename,
                                       sleeptime, debug, ".cnf",
                                       interactive_mode=interactive_mode,
                                       http_mode=http_mode)
        self._variables = dict()
        self._constraints = []

    def _process_solution(self, result_obj):
        """process the results of the solver"""
        self._solver_status = result_obj.status
        if self._solver_status not in SolverStatusCode.get_values():
            raise ValueError("solver status unknown:", self._solver_status)
        
        for var in result_obj.variables:
                self._variables[int(var.name)].set_value(True if var.value == 1 else False)

    def add_variable(self, name, id_=0):
        """add SAT variable to model
        
        if a specific id is wanted : 
        """
        new_id = self._get_new_id(id_)                
        var = Var(name, new_id)
        self._variables[var.id] = var
        return var

    def add_constraint_expr(self, expr):
        """add constraint to model,
        all constraint are implicitly connected via AND operator"""
        self._constraints.append(expr)
    
    def add_list_constraints(self, lst_constraints):
        """add a list of constraint
        constraint can be vectors or Expr
        """
        for constraint in lst_constraints:
            if type(constraint) == list:
                self.add_constraint_vector(constraint)
            elif type(constraint) == type(Expr()):
                self.add_constraint_expr(constraint)
            else:
                raise ValueError("One constraint of the list is not recognised")

    def add_constraint_vector(self, lst):
        """add a constraint using a vector format [1,-2,3]"""
        if set(map(type, lst)) != {int} and 0 not in lst:
            raise ValueError("The values in the list must be integers and != 0")
            
        for id_ in lst:
            self._add_id(id_)
        iter_vars = map(self._get_var, lst)
        self.add_constraint_expr(reduce(OR, iter_vars))
    
    def _get_var(self, id_):
        """return the right variable even if the id is negative
        set it negative if wanted
        """
        if id_ < 0:
            return - self._variables[abs(id_)]
        else:
            return self._variables[id_]
    
    def _add_id(self, id_):
        """manage negative IDs
        add new variable only if not already used
        """
        a_id = abs(id_)
        if a_id not in self._variables.keys():
            return self.add_variable("x" + str(a_id), a_id)

    def _get_new_id(self, id_=0):
        """if specific id not requested, will take the smallest one not taken
        Does not rely on te number of variables anymore
        """
        if id_ == 0:
            new_id = 1
            while new_id in self._variables.keys():
                new_id += 1
        else:
            new_id = id_
        return new_id

    @property
    def constraints(self):
        """returns the field: constraints of the model"""
        return self._constraints

    @property
    def variables(self):
        """return a dictionary of the variables {'var_name':value}"""
        def make_tuple(var): return tuple([var.name, var.value])
        iter_tuples = map(make_tuple, self._variables.values()) 
        return dict(iter_tuples)

    @property
    def solver_status(self):
        """returns the status returned by the solver"""
        return self._solver_status

    def print_results(self):
        """prints a sum up of the results returned from solve engine"""
        lst_lines = ["".join(["Status : ", self.solver_status])]
        lst_lines.extend([var.result 
                          for var in self._variables.values()])
        print("\n".join(lst_lines))

    def get_file_str(self):
        clauses = (constr.convert_to_cnf().content for constr in self._constraints)
        clauses = [clause for x in clauses for clause in x]
        filestr = "p cnf {} {}\n".format(len(self._variables), len(clauses))
        filestr += "\n".join(clause.get_cnf_str() for clause in clauses)
        return filestr

class Expr(object):
    """Expr class"""
    OPERATOR = "ERROR"

    def __str__(self):
        raise NotImplementedError()

    def convert_to_cnf(self):
        """convert the expr to conjuction normal form"""
        raise NotImplementedError()

    def __repr__(self):
        return str(self)

    def __or__(self, other):
        return OR(self, other)

    def __and__(self, other):
        return AND(self, other)

    def __xor__(self, other):
        return XOR(self, other)

    def __le__(self, other):
        return IMP(self, other)

    def __eq__(self, other):
        return EQ(self, other)

    def __ne__(self, other):
        return NE(self, other)

    def __neg__(self):
        return NEG(self)


class NEG(Expr):
    """negation expression"""
    OPERATOR = "!"

    def __init__(self, inner):
        assert not isinstance(inner, NEG)
        self._inner = inner

    def __str__(self):
        return "{}{}".format(self.OPERATOR, self.inner)

    def __neg__(self):
        return self.inner

    def get_cnf_str(self):
        """get the id of the variable or negation of a variable"""
        assert isinstance(self.inner, Var)
        return "-{}".format(self.inner.id)

    @property
    def inner(self):
        """return the inner expr of the negation"""
        return self._inner

    def convert_to_cnf(self):
        expr = self.inner

        if isinstance(expr, Var):
            return AND(OR(self))

        if isinstance(expr, (XOR, IMP, EQ, NE)):
            expr = expr.get_equivalent_expr()

        if isinstance(expr, AND):
            return OR(*[NEG(x) for x in expr.content]).convert_to_cnf()

        if isinstance(expr, OR):
            return AND(*[NEG(x) for x in expr.content]).convert_to_cnf()

        raise ValueError("found not supported inner type {}".format(self.inner))

class ListExpr(Expr):
    """a dummy expr class for expression which can contain multiple expressions"""
    def __init__(self, *content):
        self._content = []
        self._add_other(*content)

    def _add_other(self, *content):
        for expr in content:
            if isinstance(expr, self.__class__):
                self._content += expr.content
            else:
                self._content.append(expr)

    def convert_to_cnf(self):
        raise NotImplementedError()

    @property
    def content(self):
        """get the content of the and operator"""
        return self._content

    def __str__(self):
        result = " {} ".format(self.OPERATOR)
        result = result.join(str(x) for x in self.content)
        return "({})".format(result)

class AND(ListExpr):
    """and expression"""
    OPERATOR = "&"

    def convert_to_cnf(self):
        return AND(*[x for elem in self.content for x in elem.convert_to_cnf().content])

class OR(ListExpr):
    """or expression"""
    OPERATOR = "|"

    def convert_to_cnf(self):
        cnfs = (x.convert_to_cnf().content for x in self.content)
        return AND(*[OR(*x) for x in itertools.product(*cnfs)])

    def get_cnf_str(self):
        """get the cnf string"""
        return " ".join(x.get_cnf_str() for x in self.content) + " 0"

class BinaryExpr(Expr):
    """dummy class for binary expression"""
    def __init__(self, lhs, rhs):
        self._lhs = lhs
        self._rhs = rhs

    @property
    def lhs(self):
        """get left-hand-side of expression"""
        return self._lhs

    @property
    def rhs(self):
        """get right-hand-side of expression"""
        return self._rhs

    def __str__(self):
        return "({} {} {})".format(self.lhs, self.OPERATOR, self.rhs)

    def get_equivalent_expr(self):
        """get expression which only uses AND, OR and NEG and is equivalent"""
        raise NotImplementedError()

class XOR(BinaryExpr):
    """xor expression"""
    OPERATOR = "^"

    def convert_to_cnf(self):
        return self.get_equivalent_expr().convert_to_cnf()

    def get_equivalent_expr(self):
        return (self.lhs & -self.rhs) | (-self.lhs & self.rhs)


class EQ(BinaryExpr):
    """equivalence expression"""
    OPERATOR = "=="

    def convert_to_cnf(self):
        return self.get_equivalent_expr().convert_to_cnf()

    def get_equivalent_expr(self):
        return (self.lhs & self.rhs) | (-self.lhs & -self.rhs)

class NE(BinaryExpr):
    """non equivalence expression"""
    OPERATOR = "!="

    def convert_to_cnf(self):
        return self.get_equivalent_expr().convert_to_cnf()

    def get_equivalent_expr(self):
        return (-self.lhs | -self.rhs) & (self.lhs | self.rhs)

class IMP(BinaryExpr):
    """implication expression"""
    OPERATOR = "<="

    def convert_to_cnf(self):
        return self.get_equivalent_expr().convert_to_cnf()

    def get_equivalent_expr(self):
        return -self.rhs | self.lhs

class Var(Expr):
    """Variable class for SAT models"""

    def __init__(self, name, idd):
        self._name = name
        self._value = None
        self._id = idd

    def convert_to_cnf(self):
        return AND(OR(self))

    def __str__(self):
        return "{}".format(self.name)

    @property
    def name(self):
        """the name of the variable"""
        return self._name

    @property
    def id(self):
        """get the id of the variable"""
        return self._id

    def get_cnf_str(self):
        """get the id of the variable"""
        return str(self._id)

    @property
    def value(self):
        """get the solution value of the variable"""
        if self._value is None:
            raise ValueError("no value assigned yet")
        return self._value

    @property
    def result(self):
        if self._value is None:
            return "".join([self.name, " : ", "not computed"])
        else:
            return "".join([self.name, " : ", str(self.value)])

    def set_value(self, value):
        """set the solution value of the variable"""
        if not isinstance(value, bool):
            raise ValueError("wrong type for variable value")
        self._value = value
