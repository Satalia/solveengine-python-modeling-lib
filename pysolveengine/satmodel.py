# -*- coding: utf-8 -*-
"""Module for the Solver-Engine

This module contains code to build and solve MIP
models via the Solve-Engine.

"""

import itertools
from functools import reduce
from os.path import isfile

from .basemodel import BaseModel, SolverStatusCode
from .helper import check_instance


class SATModel(BaseModel):
    """SATModel class

    allows to model SAT problems

    Attributes:
    model_name: the name that the uploaded file should have,
    without extension, default is model

    sleep_time: the time we should sleep between checks if the SolveEngine
    is finished solving the problem

    debug(boolean): active the debug output

    interactive_mode(boolean): active information printing while solving

    http_mode(boolean): active http requests instead of grpc

    __variables/__variables_name(dict):used to store the variables
    indexing them by id or by name

    __lst_variables: list of variables, in the order of added
    used to get the variables in a logical order

    __constraints: list of the added constraints
    """

    def __init__(self, token, model_name="model", sleep_time=2,
                 debug=False,
                 interactive_mode=False, http_mode=False):
        """initialise the model

            INPUTS :
                token : api-key to solve with solve engine
                model_name : problem name that will figure on SolveEngine
                sleept_ime : amount of seconds waited between two status requests
                debug : to initiate, or not, Logger()
                interactive_mode : to print the advances of the solving while solving
                http_mode : use http requests if True, GRPC if False

            ATTRIBUTES :
                __variables : dictionary of problem variables, var_id : var_instance
                __variables_name : dictionary of problem variables, var_name : var_instance
                __lst_variables : list of variables, to keep the order
                              of the vars they have been added with
                __constraints : list of constraints
        """
        check_instance(fct_name='init SATModel', value=model_name,
                       name='model_name', type_=str)
        if not model_name.endswith(".cnf"):
            file_name = "".join([model_name, ".cnf"])
        else:
            file_name = model_name
        super(SATModel, self).__init__(token=token,
                                       file_name=file_name,
                                       sleep_time=sleep_time,
                                       debug=debug,
                                       interactive_mode=interactive_mode,
                                       http_mode=http_mode)

        self.__variables = dict()
        self.__variables_name = dict()
        self.__lst_variables = list()
        self.__constraints = list()

    def reinit(self):
        """
        Reinitialise the model characteristics that are not init parameters
        :return: Nothing
        """
        self.__variables = dict()
        self.__variables_name = dict()
        self.__lst_variables = list()
        self.__constraints = list()
        super(SATModel, self).reinit()

    def _process_solution(self, result_obj):
        """
        process the results of the solver

        :param result_obj: the object given as a response
            from Solveengine after solving the problem
        :return: s_status: the status of the job of solving
        """
        s_status = str(result_obj.status)
        if s_status not in SolverStatusCode.get_values():
            raise ValueError("solver status unknown:", self.solver_status)
        
        for var in result_obj.variables:
            var_id = int(var.name)
            if var_id in self.__variables.keys():
                self.__variables[var_id].set_value(True if int(var.value) == 1 else False)

        return s_status

    def add_variable(self, name, id_=0):
        """
        Add SAT variable to model
        return existing variable if already added

        if a specific id is wanted : will give this id to the variable

        :param name: string value for the name of the variable
        :param id_: integer value for the id that will
                    be used for the variable
        :return: the variable instance just created
        """
        check_instance(fct_name='add_variable', value=name,
                       name='name', type_=str)
        check_instance(fct_name='add_variable', value=id_,
                       name='id_', type_=int)
        new_id = self.__get_new_id(id_)
        if new_id in self.__variables:
            raise ValueError("".join(["Could not add_variable, the id ",
                                     str(new_id), " is already used."]))
        if name in self.__variables_name:
            raise ValueError("".join(["Could not add_variable, the name ",
                                      name, " is already used."]))

        new_var = Var(name, new_id)
        self.__variables_name[name] = new_var
        self.__variables[new_id] = new_var
        self.__lst_variables.append(new_var)
        return new_var

    def add_constraint_expr(self, expr):
        """
        add constraint to model,
        all constraint are implicitly connected via AND operator

        :param expr: expression to add (type Expr())
        """
        check_instance(fct_name='add_constraint_expr',
                       value=expr, name='expr', type_=Expr)

        self.__constraints.append(expr)

    def add_constraint_vector(self, lst):
        """
        add a constraint using a vector format [1,-2,3]
        do nothing if lst is empty (not lst   return False if empty)

        :param lst: a list of integers as a constraint
                integers must be different from 0
        """
        if not lst:
            return

        if set(map(type, lst)) != {int} and 0 not in lst:
            raise ValueError("".join(["Could not add a constraint.",
                                      "The values in the list must be integers and != 0",
                                      "The constraint given : ", str(lst)]))

        for id_ in lst:
            self.__add_id(id_)
        iter_vars = map(self.__get_var, lst)
        self.add_constraint_expr(reduce(OR, iter_vars))

    def add_list_constraints(self, lst_constraints):
        """
        add a list of constraint
        using either add_constraint_expr or
                    add_constraint_vector

        :param lst_constraints: a list of Expr() or lists
        """
        check_instance(fct_name="add_list_constraints", value=lst_constraints,
                       name="lst_constraints", type_=list)
        for constraint in lst_constraints:
            if isinstance(constraint, list):
                self.add_constraint_vector(constraint)
            elif isinstance(constraint, Expr):
                self.add_constraint_expr(constraint)
            else:
                check_instance(fct_name="add_constraint for one value of the list",
                               value=constraint, name="constraint",
                               type_=(list, Expr))

    def build_from_file(self, file_path):
        """
        Builds the model using an existing SAT problem
        written in the cnf format

        :param file_path: string value of the path to the file
        """
        check_instance(fct_name="build_from_file", value=file_path,
                       name="file_path", type_=str)
        if not file_path.endswith(".cnf"):
            raise ValueError("\n".join(["Could not build_from_file, the apth must end with '.cnf'.",
                                        "".join(["Here is the path given : ", file_path])]))
        if not isfile(file_path):
            raise ValueError("\n".join(["Could not build_from_file, file does not exist.",
                                       "".join(["Here is the path given : ", file_path])]))
        self.reinit()

        with open(file_path, 'r') as f:
            pb_txt = f.read()
            f.close()

        lst_rws = pb_txt.split('\n')

        first_rw = _get_first_rw(lst_rws, file_path)
        lst_lst = [_from_line_to_rw(line, file_path)
                   for line in lst_rws[first_rw:]
                   if len(line.replace(" ", "")) > 0]

        self.add_list_constraints(lst_lst)

    def get_variable_with_id(self, id_):
        """
        return the variable with the integer id of the variable

        :param id_: the integer id of the variable
                (having been set while creating the variable)
        :return: Var() instance of the asked variable
        """
        check_instance(fct_name='get_variable_with_id', value=id_,
                       name='id_', type_=int)
        return self.__variables[abs(id_)]

    def get_variable_with_name(self, name):
        """
        return the variable with the string name of the variable

        :param name: the string name of the variable
                (having been set while creating the variable)
        :return: Var() instance of the asked variable
        """
        check_instance(fct_name='get_variable_with_name', value=name,
                       name='name', type_=str)
        return self.__variables_name[name]

    def remove_constraint_with_index(self, index):
        """
        remove one constraint with the index

        :param index: integer value of the index of
                the constraint in the list
        """
        check_instance(fct_name="remove_constraint_with_index",
                       value=index, name='index', type_=int)
        try:
            self.__constraints.pop(index)
        except:
            raise ValueError("".join(["The index specified, ", str(index),
                                      ", is out of range. There are ",
                                      str(len(self.__constraints)),
                                      " constraints."]))

    def __get_var(self, id_):
        """
        return the right variable even if the id is negative
        set it negative if wanted

        :param id_: the integer id of the variable
                (having been set while creating the variable)
        :return: plus or minus the Var() instance
                of the asked variable
        """
        if id_ < 0:
            return - self.__variables[abs(id_)]
        else:
            return self.__variables[id_]
    
    def __add_id(self, id_):
        """
        manage negative IDs
        add new variable only if not already used

        :param id_: the integer id of the variable
                (having been set while creating the variable)
        :return: the variable instance just created
        """
        a_id = abs(id_)
        if a_id not in self.__variables.keys():
            return self.add_variable("x" + str(a_id), a_id)

    def __get_new_id(self, id_=0):
        """
        if specific id not requested, will take the smallest one not taken
        Does not rely on te number of variables anymore

        :param id_: requested integer for the id of the new variable
        :return:
        """
        if id_ == 0:
            new_id = 1
            while new_id in self.__variables.keys():
                new_id += 1
        else:
            new_id = abs(int(id_))
        return new_id

    def print_constraints(self):
        """prints the constraints with the index to remove them in case"""
        rg = range(0, len(self.__constraints))
        str_cstrs = list(map(str, self.__constraints))
        print("\n".join(map(str, zip(rg, str_cstrs))))

    @property
    def var_results(self):
        """
        :return: dictionary of the variables {'var_id':value}
        """
        def make_tuple(var): return tuple([var.id, var.value])

        iter_tuples = map(make_tuple, self.__lst_variables)
        return dict(iter_tuples)

    @property
    def var_name_results(self):
        """
        :return: dictionary of the variables {'var_name':value}
        """

        def make_tuple(var): return tuple([var.name, var.value])

        iter_tuples = map(make_tuple, self.__lst_variables)
        return dict(iter_tuples)

    def print_results(self):
        """prints a summary of the results returned from solve engine"""
        lst_lines = ["".join(["Status : ", self.solver_status])]
        lst_lines.extend([var.result 
                          for var in self.__lst_variables])
        print("\n".join(lst_lines))

    def build_str_model(self):
        """
        Builds the str file of the problem, written in the cnf format
        :return: returns the str value of the text
        """
        clauses = (constr.convert_to_cnf().content for constr in self.__constraints)
        clauses = [clause for x in clauses for clause in x]
        filestr = "p cnf {} {}\n".format(len(self.__variables), len(clauses))
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
    OPERATOR = "-"

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
            return OR(*[ - x for x in expr.content]).convert_to_cnf()

        if isinstance(expr, OR):
            return AND(*[ - x for x in expr.content]).convert_to_cnf()

        raise ValueError("found not supported inner type {}".format(self.inner))


class ListExpr(Expr):
    """a dummy expr class for expression which can contain multiple expressions"""
    def __init__(self, *content):
        self._content = []
        self.__add_other(*content)

    def __add_other(self, *content):
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

    def __init__(self, name, id_):
        self.__name = name
        self.__value = None
        self.__id = id_

    def convert_to_cnf(self):
        return AND(OR(self))

    def __str__(self):
        return "{}".format(self.name)

    @property
    def name(self):
        """the name of the variable"""
        return self.__name

    @property
    def id(self):
        """get the id of the variable"""
        return self.__id

    def get_cnf_str(self):
        """get the id of the variable"""
        return str(self.__id)

    @property
    def value(self):
        """get the solution value of the variable"""
        if self.__value is None:
            return "not computed"
        return self.__value

    @property
    def result(self):
        if self.__value is None:
            return "".join([self.name, " : ", "not computed"])
        else:
            return "".join([self.name, " : ", str(self.value)])

    def set_value(self, value):
        """set the solution value of the variable"""
        if not isinstance(value, bool):
            raise ValueError("wrong type for variable value")
        self.__value = value


def _get_first_rw(lst_rws, path):
    rw_cnt, max_lst = (0, len(lst_rws))
    while not lst_rws[rw_cnt].startswith("p cnf "):
        rw_cnt += 1
        if rw_cnt == max_lst:
            raise ValueError("\n".join(["".join(["Could not build_from_path, ",
                                                 "the file is odd, no line starting"
                                                 " with 'p cnf ' found"]),
                                       "".join(["Here is the path sent : ", path])]))
    return rw_cnt + 1


def _from_line_to_rw(line, path):
    l = []
    for i in line.split(" ")[:-1]:
        try:
            l.append(int(i))
        except:
            raise ValueError("\n".join(["".join(["Could not build_from_path, ",
                                                 "the file is odd, one line contains ",
                                                 "something else than integers."]),
                                        "".join(["Here is the path of the file sent : ",
                                                 path]),
                                        "".join(["Here is the odd line : ", line])]))

    return l
