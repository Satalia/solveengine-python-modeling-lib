# -*- coding: utf-8 -*-
"""Module for the Solver-Engine

This module contains code to build and solve MIP
models via the Solve-Engine.

"""

from enum import Enum
from collections import namedtuple
from numpy import ndarray

from .helper import StrEnum, _get_logger, check_instance

from .basemodel import BaseModel, SolverStatusCode

LOGGER = _get_logger()


class Infinity:
    """class to represent infinity

    >>> str(Infinity())
    'inf'
    >>> str(-Infinity())
    '-inf'
    """

    def __neg__(self):
        return NegInfinity()

    def __str__(self):
        return "inf"
    
    def __repr__(self):
        return "INF"

class NegInfinity:
    """class to represent -infinity

    >>> str(-NegInfinity())
    'inf'
    >>> str(NegInfinity())
    '-inf'
    """

    def __neg__(self):
        return Infinity()

    def __str__(self):
        return "-inf"
    
    def __repr__(self):
        return "-INF"

INF = Infinity()


class VarType(Enum):
    """Enum for the types of variables"""
    CONTINUOUS = 0
    INTEGER = 1


class Operator(StrEnum):
    """Constraint Operators"""
    LEQ = "<="
    EEQ = "="
    GEQ = ">="


class Direction(StrEnum):
    """Optimization Directions"""
    MAXIMIZE = "Maximize"
    MINIMIZE = "Minimize"


class MIPModel(BaseModel):
    """MIPModel class

    Creates A MIPModel class to create MIP/LP model
    The default objective is 0 and
    the default objective direction is minimize.
    The default variable lower bound is -infinity.
    The default variable upper bound is infinity.

    Attributes:
    token: the SolveEngine token provided by the website,
    this is necessary to connect to the solver

    filename: the filename that the uploaded file should have,
    default is model

    sleeptime: the time we should sleep between checks if the SolveEngine
    is finished solving the problem

    debug(boolean): active the debug output
    """
    OBJECTIVE = namedtuple('Objective', 'expr direction value')
    DEFAULT_VAR_NAME = "x"
    DEFAULT_EQ_NAME = "cEq"
    DEFAULT_INEQ_NAME = "cIneq"

    def __init__(self, token, filename="model", sleep_time=2,
                 debug=False,
                 interactive_mode=False, http_mode=False):
        """initialise the model

        INPUTS :
            token : api-key to solve with solve engine
            filename : problem name that will figure on SolveEngine
            sleeptime : amount of seconds waited between two status requests
            debug : to initiate, or not, Logger()
            interactive_mode : to print the advances of the solving while solving
            http_mode : use http requests if True, GRPC if False

        ATTRIBUTES :
            __variables : dictionary of problem variables, var_name : var_instance
            __lst_variables : list of variables, to keep the order
                              of the vars they have been added with
            __constraints : list of constraints
            __obj : objective function defined with namedtuple,
                    attributes : expression, direction (min/max),
                    and the value updated when solved
        """
        super(MIPModel, self).__init__(token=token,
                                       filename=filename,
                                       sleep_time=sleep_time,
                                       debug=debug,
                                       file_ending=".lp",
                                       interactive_mode=interactive_mode,
                                       http_mode=http_mode)
        self.__variables = dict()
        self.__lst_variables = list()
        self.__constraints = []
        self.__obj = MIPModel.OBJECTIVE(Expr(), Direction.MINIMIZE, None)

    def _add_var(self, name, lb=-INF, ub=INF, var_type=VarType.CONTINUOUS):
        """add Variable to model"""
        check_instance(fct_name='add_var', value=name,
                       name='name', type_=str)

        if name in self.__variables:
            raise ValueError("".join(["Variable ", name,
                                      " does exists already"]))
        var = Var(name, lb, ub, var_type)
        self.__variables[name] = var
        self.__lst_variables.append(var)
        return var

    def add_continuous_var(self, name, lb=-INF, ub=INF):
        """add and return continuous variable.

        Adds a continuous variable to the model.

        Args:
        name: name of the variable

        lb: the lower bound of the variable,
        this can be any object which returns a valid number by calling its __str__ method

        ub: the upper bound of the variable,
        this can be any object which returns a valid number by calling its __str__ method

        Returns:
        instance of Var class

        Raises:
        ValueError: Whenever their already exists a variable with that name
        """
        return self._add_var(
            name=name, lb=lb, ub=ub, var_type=VarType.CONTINUOUS)

    def add_integer_var(self, name, lb=-INF, ub=INF):
        """add Integer Variable

        Adds an integer variable to the model.

        Args:
        name: name of the variable

        lb: the lower bound of the variable,
        this can be any object which returns a valid number by calling its __str__ method

        ub: the upper bound of the variable,
        this can be any object which returns a valid number by calling its __str__ method

        Returns:
        instance of Var class

        Raises:
        ValueError: Whenever their already exists a variable with that name
        """
        return self._add_var(name, lb=lb, ub=ub, var_type=VarType.INTEGER)

    def add_binary_var(self, name):
        """add Binary Variable

        Adds a binary variable to the model.

        Args:
        name: name of the variable

        Returns:
        instance of Var class

        Raises:
        ValueError: Whenever their already exists a variable with that name
        """
        return self.add_integer_var(name=name, lb=0, ub=1)

    def add_constraint(self, constr, name=None):
        """add Constraint

        Adds a constraint to the model

        Args:
        constr: the constraint
        name (optional): a name for the constraint

        Raises:
        ValueError: is constr is not of type Constraint
        """
        check_instance(fct_name="add_constraint", value=constr,
                       name='constr', type_=Constraint)
        if name is not None:
            check_instance(fct_name="add_constraint", value=name,
                           name='name', type_=str)
        constr.name = name or constr.name
        self.__constraints.append(constr)

    def set_obj(self, expr):
        """set Objective function

        Set the objective Function

        Args:
        expr: the objective function,
        has to be either a linear expression build from variables
        or an object which returns a number by calling the __str__ method
        """
        self.__obj = self.__obj._replace(expr=expr)

    def set_direction(self, direction):
        """set Objective Direction"""
        self.__obj = self.__obj._replace(direction=direction)

    def set_to_minimize(self):
        """minimize the objective"""
        self.set_direction(Direction.MINIMIZE)

    def set_to_maximize(self):
        """maximize the objective"""
        self.set_direction(Direction.MAXIMIZE)
    
    def build_with_matrices(self, f, A, b, 
                            Aeq=None, beq=None,
                            lb=None, ub=None,
                            int_list=None, bin_list=None):
        """Function to build the model using the Matlab way
        
        Args: 
            f, b, beq, lb, ub : lists of real numbers
            A, Aeq: matrices of real numbers
            int_list, bin_list: lists of binary numbers
            
            such that it matches with this model
            
                             {   A * x <= b
            min fx such that { Aeq * x  = beq
             x               {    lb <= x <= ub
                             { x[i] integer if int_list[i] = 1
                             { x[i] binary if bin_list[i] = 1
        
        Returns:
            errMsg if the Args are not coherent
            None if all is ok
        """
        Aeq = list() if Aeq is None else Aeq
        beq = list() if beq is None else beq
        lb = list() if lb is None else lb
        ub = list() if ub is None else ub
        int_list = list() if int_list is None else int_list
        bin_list = list() if bin_list is None else bin_list

        _check_matrices(f, A, b, Aeq, beq, lb, ub, int_list, bin_list)
        self._build_variables_matrices(len(f), lb, ub, int_list, bin_list)
        self._build_objective_matrices(f)
        self._build_constraints_matrices(A, b, Aeq, beq)

    def _build_variables_matrices(self, nb_vars, lb, ub, int_list, bin_list):
        """reinitiate variables
        build variables like x0, .., xnbVars using matlab-style vectors
        add them to the model's dictionary
        """
        self.__variables = dict()
        lst_tuples = _build_name_index_tuples(self.DEFAULT_VAR_NAME, nb_vars)
        for var_name, index in lst_tuples:
            if bin_list[index]:
                self.add_binary_var(var_name)
            elif int_list[index]:
                self.add_integer_var(var_name, lb=lb[index], ub=ub[index])
            else:
                self.add_continuous_var(var_name, lb=lb[index], ub=ub[index])

    def _build_objective_matrices(self, f):
        """set the objective function using the list f"""
        expr = _build_expr_coeff_vars(f, self.__lst_variables)
        self.set_obj(expr)
        self.set_to_minimize()

    def _build_constraints_matrices(self, A, b, Aeq, beq):
        """build the model's constraints using matlab-style matrices"""
        self.__constraints = []
        self._add_constraints_matrices(A, b, boo_equ=False)
        if Aeq is not None:
            self._add_constraints_matrices(Aeq, beq, boo_equ=True)

    def _add_constraints_matrices(self, A, b, boo_equ):
        """add all the constraints deduced from the matrices A and b"""
        lst_tuples = _build_name_index_tuples(self.DEFAULT_EQ_NAME if boo_equ
                                              else self.DEFAULT_INEQ_NAME, len(b))
        for cstr_name, index in lst_tuples:
            expr = _build_expr_coeff_vars(A[index], self.__lst_variables)
            if boo_equ:
                self.add_constraint(expr == b[index], cstr_name)
            else:
                self.add_constraint(expr <= b[index], cstr_name)

    def get_variable(self, name):
        """return the variable with the str name of the variable"""
        check_instance(fct_name='get_variable_with_name', value=name,
                       name='name', type_=str)
        return self.__variables[name]

    def remove_constraint_with_index(self, index):
        """remove one constraint with the index"""
        check_instance(fct_name="remove_constraint_with_index",
                       value=index, name='index', type_=int)
        try:
            self.__constraints.pop(index)
        except:
            raise ValueError("".join(["The index specified, ", str(index),
                                      ", is out of range. There are ",
                                      str(len(self.__constraints)),
                                      " constraints."]))

    def print_constraints(self):
        """prints the constraints with the index to remove them in case"""
        rg = range(0, len(self.__constraints))
        str_cstrs = list(map(str, self.__constraints))
        print("\n".join(map(str, zip(rg, str_cstrs))))

    @property
    def obj(self):
        """get objective value

        Raises:
        ValueError: if no objective value is stored
        """
        if self.__obj.value is None:
            return "not computed"
        return self.__obj.value

    @property
    def var_results(self):
        """return a dictionary of the variables {'var_id': value}"""
        def make_tuple(var): return tuple([var.name, var.value])

        iter_tuples = map(make_tuple, self.__lst_variables)
        return dict(iter_tuples)

    def _process_solution(self, result_obj):
        """process the results of the solver"""
        self.__obj = self.__obj._replace(value=result_obj.objective_value)
        s_status = result_obj.status
        if s_status not in SolverStatusCode.get_values():
            raise ValueError("solver status unknown:", self.solver_status)

        for var in result_obj.variables:
            self.__variables[var.name].set_value(var.value)
        return s_status

    def print_results(self):
        """prints a sum up of the results returned from solve engine"""
        lst_lines = list()
        lst_lines.append("".join(["Status : ", self.solver_status]))
        lst_lines.append("".join(["Objective value : ", str(self.obj)]))
        lst_lines.append("Variables :")
        lst_lines.extend(list(map(str, self.__lst_variables)))
        print("\n".join(lst_lines))

    def build_str_model(self):
        """returns the str file of the problem, written in the mlip format"""
        list_lines = list()
        list_lines.append(str(self.__obj.direction.value))
        list_lines.append(str(self.__obj.expr.lpstr()))
        list_lines.append("Subject To")
        list_lines.extend(c.lpstr() for c in self.__constraints)
        list_lines.append("Bounds")
        
        bound_lst = [v.lpstr_bounds() for v in self.__lst_variables]
        list_lines.extend(b for b in bound_lst if b)

        list_lines.append("General")
        list_lines.extend(v.name for v in self.__lst_variables if v.is_integer)
        list_lines.append("End")
        return "\n".join(list_lines)


class Constraint(object):
    """class to represent a constraint

    Attributes:
    lhs: an expression or number, the left-hand-side of the constraint
    operator: either <=, = or >=
    rhs: an expression or number, the right-hand-side of the constraint
    optional name: the name of the constraint
    """

    def __init__(self, lhs, operator, rhs, name=None):
        if not isinstance(lhs, Expr) and not isinstance(rhs, Expr):
            raise ValueError(
                "a constraint must have at least one expression, not {} and {}".
                format(lhs, rhs))
        self.__operator = operator
        self.__lhs = lhs
        self.__rhs = rhs
        self.name = name

    def _format_str(self, lhs, rhs):
        name_str = "{}: ".format(self.name) if self.name else ""
        return "{}{} {} {}".format(name_str, lhs, self.__operator, rhs)

    def lpstr(self):
        """get LP string for constraint"""
        lhs = self.__lhs - self.__rhs
        if not isinstance(lhs, Expr) or lhs.is_constant:
            raise ValueError("a constraint must have a least one variable")
        rhs = -lhs.constant
        lhs.constant = 0
        return self._format_str(lhs, rhs)

    def __str__(self):
        return self._format_str(self.__lhs, self.__rhs)


class Expr(object):
    """class for linear expression

    This class represents an affine linear expression.

    Attributes:
    constant: the constant part of the expression, default=0
    """

    def __init__(self, constant=0):
        self.variables = dict()
        self.constant = constant

    def add_term(self, var, value):
        """add term to expression

        Args:
        var: variable
        value: any object which returns a number by calling its __str__ method

        Raises:
        ValueError: if var is not a variable obtained by the add_var method
        of the model class
        """
        if not isinstance(var, Var):
            raise ValueError("no a variable")
        self.variables[var] = value
        return self

    def lpstr(self):
        """return the lp string of the expression"""
        if not self.variables:
            return str(self.constant)

        res = []
        for var, value in self.variables.items():
            res.append("+" if value >= 0 else "-")
            if abs(value) != 1:
                res.append(str(abs(value)))
            res.append(var.name)
        if res[0] == "+":
            res = res[1:]
        lpstr = " ".join(res)
        if self.constant:
            lpstr += " + {}".format(self.constant)
        return lpstr

    @property
    def is_constant(self):
        """is the expr just a number

        Returns:
        True if the expression does not contain any variables, otherwise False
        """
        return not any(self.variables)

    def __str__(self):
        return self.lpstr()

    def __repr__(self):
        return "Expr[{}]".format(self)

    def get_copy(self):
        """return shallow copy"""
        expr = Expr(self.constant)
        expr.variables = self.variables.copy()
        return expr

    def __iadd__(self, other):
        if not isinstance(other, Expr):
            other = Expr(other)
        self.constant += other.constant
        for var, value in other.variables.items():
            self.variables[var] = self.variables.get(var, 0) + value
        return self

    def __imul__(self, other):
        if isinstance(other, Expr):
            raise ValueError("cannot multiply Expr with Expr")
        self.constant *= other
        for var in self.variables:
            self.variables[var] *= other
        return self

    def __add__(self, other):
        expr = self.get_copy()
        expr += other
        return expr

    def __neg__(self):
        expr = self.get_copy()
        expr *= -1
        return expr

    def __mul__(self, other):
        expr = self.get_copy()
        expr *= other
        return expr

    def __div__(self, other):
        return self * (1 / other)

    def __truediv__(self, other):
        return self.__div__(other)

    def __sub__(self, other):
        return self + (-other)

    def __rsub__(self, other):
        return -self + other

    def __rmul__(self, other):
        return self * other

    def __radd__(self, other):
        return self + other

    def __isub__(self, other):
        self += -other
        return self

    def __idiv__(self, other):
        self *= (1 / other)
        return self

    def __itruediv__(self, other):
        self.__idiv__(other)
        return self

    def __le__(self, other):
        return Constraint(self, Operator.LEQ, other)

    def __ge__(self, other):
        return Constraint(self, Operator.GEQ, other)

    def __eq__(self, other):
        return Constraint(self, Operator.EEQ, other)

    def equals(self, other):
        """method for comparison"""
        if not isinstance(other, Expr):
            return False
        return self.variables == other.variables and self.constant == other.constant


class Var(Expr):
    """variable class

    Class that represents a Variable.
    This class should not be used directed, only via the model.add_var method.

    Attributes:
    name: the name of the variable
    lb: the lower bound of the variable
    ub: the upper bound of the variable
    vartype: the type of the variable, either continuous or integer
    """

    def __init__(self, name, lb, ub, var_type):
        super(Var, self).__init__()

        check_instance(fct_name='create new Var()', value=name,
                       name='name', type_=str)
        check_instance(fct_name='create new Var()', value=lb,
                       name='lb', type_=(float, int, Infinity,
                                         NegInfinity))
        check_instance(fct_name='create new Var()', value=ub,
                       name='ub', type_=(float, int, Infinity,
                                         NegInfinity))
        check_instance(fct_name='create new Var()', value=var_type,
                       name='var_type', type_=VarType)

        self.__name = name
        self.var_type = var_type
        self.lb = lb
        self.ub = ub
        self.__value = None
        self.variables = {self: 1}

    def __hash__(self):
        return hash(str(self.name))

    @property
    def value(self):
        """get the value of the variable after solving

        Raises:
        ValueError: if no value has been computed yet
        """
        if self.__value is None:
            return "not computed"
        return self.__value

    def set_value(self, val):
        """internal method to set value of variable"""
        self.__value = val

    @property
    def name(self):
        """get the name of the variable"""
        return self.__name

    def lpstr_bounds(self):
        """build the lp string"""
        return "{} <= {} <= {}".format(self.lb, self.name, self.ub)

    @property
    def is_integer(self):
        return self.var_type == VarType.INTEGER

    def __iadd__(self, other):
        expr = self.get_copy()
        expr += other
        return expr

    def __imul__(self, other):
        expr = self.get_copy()
        expr *= other
        return expr
    
    def __str__(self):
        return "".join([self.__name, " : ", str(self.__value)])


def _build_name_index_tuples(name, index_max):
    """return list of tuples [('nameN', N)] of the size indexMax"""
    def tuple_name_index(n):
        return tuple(["".join([name, str(n)]), n])

    return list(map(tuple_name_index, range(0, index_max)))


def _build_expr_coeff_vars(lst_coeffs, lst_vars):
    """return the expression given the lists of coefficient and variables"""
    return sum(coeff * var for coeff, var in zip(lst_coeffs, lst_vars) if coeff != 0)


def _check_matrices(f, A, b, Aeq, beq, lb, ub, int_list, bin_list):
    """Check that the dimensions of the matrices match with each other

    Complete the vectors lb, ub, int_list, bin_list
    with values by default if they are shorter than the number of variables
    """
    _check_vector_attr(l=f, l_name='f')
    _check_matrix_attr(m=A, m_name='A')
    _check_vector_attr(l=b, l_name='b')

    nb_vars = len(f)

    if len(A) != len(b):
        raise ValueError("Input error : A and b are differently sized")
    if len(A[0]) != nb_vars:
        raise ValueError("Input error : A and b are differently sized")
    if Aeq is not None:
        _check_matrix_attr(m=Aeq, m_name='Aeq')
        _check_vector_attr(l=beq, l_name='beq')

        if len(Aeq) not in [len(beq), 1]:
            raise ValueError("Input error : Aeq and beq are differently sized")
        if len(Aeq[0]) not in [nb_vars, 0]:
            raise ValueError("Input error : Aeq and f are differently sized")

    _check_vector_attr(l=lb, l_name='lb')
    _check_vector_attr(l=ub, l_name='ub')
    _check_vector_attr(l=int_list, l_name='int_list')
    _check_vector_attr(l=bin_list, l_name='bin_list')

    if not check_complete_list(lb, nb_vars, -INF):
        raise ValueError("Input error : the vector lb has too many values")
    if not check_complete_list(ub, nb_vars, INF):
        raise ValueError("Input error : the vector ub has too many values")
    if not check_complete_list(int_list, nb_vars, 0):
        raise ValueError("Input error : the vector int_list has too many values")
    if not check_complete_list(bin_list, nb_vars, 0):
        raise ValueError("Input error : the vector bin_list has too many values")

    if 1 in [i for i, j in zip(int_list, bin_list) if i == j]:
        raise ValueError("Input error : some variables are both integer and binary")


def _check_vector_attr(l, l_name):
    def raise_input_error(msg):
        msg_frst_rw = "".join(["Given input, ", l_name, " is incorrect."])
        raise ValueError("\n".join([msg_frst_rw,
                                    msg,
                                    "Here is the input given :",
                                    str(l)]))
    try:
        nb_rws = len(l)
    except:
        raise_input_error("len() of it should return the nb of rows")

    for rw_cnt in range(0, nb_rws):
        try:
            val = l[rw_cnt]
        except:
            raise raise_input_error("\n".join(["Should be possible to call input[index]",
                                               "".join(["The cell involved is the cell ",
                                                        "[", str(rw_cnt), "]"])]))
        try:
            if not isinstance(val, (Infinity, NegInfinity)):
                float(val)
        except:
            raise raise_input_error("\n".join(["All the values should be numeric or INF",
                                               "".join(["The cell involved is the cell ",
                                                        "[", str(rw_cnt), "]"])]))


def _check_matrix_attr(m, m_name):
    def raise_input_error(msg):
        msg_frst_rw = "".join(["Given input, ", m_name, " is incorrect."])
        raise ValueError("\n".join([msg_frst_rw,
                                   msg,
                                    "Here is the input given :",
                                    str(m)]))

    try:
        nb_rws = len(m)
    except:
        raise_input_error("len() of it should return the nb of rows")

    try:
        frst_rw_ln = len(m[0])
    except:
        raise raise_input_error("Should be possible to call input[0]")
    for rw_cnt in range(0, nb_rws):
        try:
            rw_ln = len(m[rw_cnt])
        except:
            raise raise_input_error("\n".join(["Should be possible to call len(input[i])",
                                              "".join(["Row involved is the row ", str(rw_cnt)])]))

        if rw_ln != frst_rw_ln:
            raise raise_input_error("\n".join(["All the rows should be the same size",
                                               "".join(["The first row's size was : ",
                                                        str(frst_rw_ln)]),
                                               "".join(["The row ", str(rw_cnt),
                                                        "'s size is : ", str(rw_ln)])]))

        for col_cnt in range(0, frst_rw_ln):
            try:
                val = m[rw_cnt][col_cnt]
            except:
                raise raise_input_error("\n".join(["Should be possible to call row_value[index]",
                                                  "".join(["The row involved is the row ",
                                                           "[", str(rw_cnt), "]"])]))
            try:
                float(val)
            except:
                raise raise_input_error("\n".join(["All the values should be numeric",
                                                  "".join(["The cell involved is the cell ",
                                                           "[", str(rw_cnt), str(col_cnt), "]"])]))


def check_complete_list(list_, nb_max, def_value):
    """make sure the list is long enough

    complete with default value if not

    return False if the list is too long
    """

    if len(list_) <= nb_max:
        list_.extend([def_value] * (nb_max - len(list_)))
        return True
    else:
        return False
