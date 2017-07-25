# -*- coding: utf-8 -*-
"""Module for the Solver-Engine

This module contains code to build and solve MIP
models via the Solve-Engine.

"""

from enum import Enum
from collections import namedtuple

from helper import StrEnum, _get_logger, check_complete_list
from basemodel import BaseModel, SolverStatusCode

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
    CONTINIOUS = 0
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

    def __init__(self, token, filename="model", sleeptime=2,
                 debug=False, interactive_mode=False, http_mode=False):
        super(MIPModel, self).__init__(token=token,
                                       filename=filename,
                                       sleeptime=sleeptime,
                                       debug=debug,
                                       file_ending=".lp",
                                       interactive_mode=interactive_mode,
                                       http_mode=http_mode)
        self._variables = dict()
        self._constraints = []
        self._obj = MIPModel.OBJECTIVE(Expr(), Direction.MINIMIZE, None)

    def add_var(self, name, lb=-INF, ub=INF, vartype=VarType.CONTINIOUS):
        """add Variable to model"""
        if name in self._variables:
            raise ValueError("Variable {} does exists".format(name))
        var = Var(name, lb, ub, vartype)
        self._variables[name] = var
        return var

    def add_continious_var(self, name, lb=-INF, ub=INF):
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
        return self.add_var(
            name=name, lb=lb, ub=ub, vartype=VarType.CONTINIOUS)

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
        return self.add_var(name, lb=lb, ub=ub, vartype=VarType.INTEGER)

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
        if not isinstance(constr, Constraint):
            raise ValueError("wrong Type for constraint")
        constr.name = name or constr.name
        self._constraints.append(constr)

    def set_obj(self, expr):
        """set Objective function

        Set the objective Function

        Args:
        expr: the objective function,
        has to be either a linear expression build from variables
        or an object which returns a number by calling the __str__ method
        """
        self._obj = self._obj._replace(expr=expr)

    def set_direction(self, direction):
        """set Objective Direction"""
        self._obj = self._obj._replace(direction=direction)

    def set_to_minimize(self):
        """minimize the objective"""
        self.set_direction(Direction.MINIMIZE)

    def set_to_maximize(self):
        """maximize the objective"""
        self.set_direction(Direction.MAXIMIZE)
    
    def build_with_matrices(self, f, A, b, 
                            Aeq = None, beq = [], 
                            lb=[], ub=[], 
                            int_list=[], bin_list=[]):
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

        self._check_matrices(f, A, b, Aeq, beq, lb, ub, int_list, bin_list)
        self._build_variables_matrices(len(f), lb, ub, int_list, bin_list)
        self._build_objective_matrices(f)
        self._build_constraints_matrices(A, b, Aeq, beq)
        
    def _check_matrices(self, f, A, b, Aeq, beq, lb, ub, int_list, bin_list):
        """Check that the dimensions of the matrices match with each other
        
        Complete the vectors lb, ub, int_list, bin_list 
        with values by default if they are shorter than the number of variables
        """        
        nb_vars = len(f)
        try:
            tem = A.shape[1]
        except:
            raise ValueError("Input error : A is not a 2-dimension matrix")
        
        if A.shape[0] != len(b):
            raise ValueError("Input error : A and b are differently sized")
        if A.shape[1] != nb_vars:
            raise ValueError("Input error : A and b are differently sized")
        if Aeq != None:
            try:
                tem = Aeq.shape[1]
            except:
                raise ValueError("Input error : Aeq is not a 2-dimension matrix")

            if Aeq.shape[0] not in [len(beq),1]:
                raise ValueError("Input error : Aeq and beq are differently sized")
            if Aeq.shape[1] not in [nb_vars, 0]:
                raise ValueError("Input error : Aeq and f are differently sized")
        

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

    def _build_variables_matrices(self, nb_vars, lb, ub, int_list, bin_list):
        """reinitiate variables
        build variables like x0, .., xnbVars using matlab-style vectors
        add them to the model's dictionary
        """
        self._variables = dict()
        lst_tuples = self._build_name_index_tuples("x", nb_vars)
        for var_name, index in lst_tuples:
            if bin_list[index]:
                self.add_binary_var(var_name)
            elif int_list[index]:
                self.add_integer_var(var_name, lb=lb[index], ub = ub[index])
            else:
                self.add_continious_var(var_name, lb=lb[index], ub = ub[index])

    def _build_objective_matrices(self, f):
        """set the objective function using the list f"""
        expr = self._build_expr_coeff_vars(f, self._variables.values())
        self.set_obj(expr)
        self.set_to_minimize()

    def _build_constraints_matrices(self, A, b, Aeq, beq):
        """build the model's constraints using matlab-style matrices"""
        self._constraints = []
        self._add_constraints_matrices(A,b, booEqu=False)
        if Aeq != None:
            self._add_constraints_matrices(Aeq,beq, booEqu=True)

    def _add_constraints_matrices(self, A, b, booEqu):
        """add all the constraints deduced from the matrices A and b"""
        lst_tuples = self._build_name_index_tuples("cEq" if booEqu else "cIneq", len(b))
        for cstrName, index in lst_tuples:
            expr = self._build_expr_coeff_vars(A[index, :], self._variables.values())
            if booEqu:
                self.add_constraint(expr == b[index], cstrName)
            else:
                self.add_constraint(expr <= b[index], cstrName)            

    def _build_name_index_tuples(self, name, indexMax):
        """return list of tuples [('nameN', N)] of the size indexMax"""
        def tuple_name_index(n): return tuple(["".join([name, str(n)]), n])
        return list(map(tuple_name_index, range(0, indexMax))) 

    def _build_expr_coeff_vars(self, lst_coeffs, lst_vars):
        """return the expression given the lists of coefficient and variables"""
        return sum(coeff * var for coeff, var in zip(lst_coeffs, lst_vars))

    @property
    def obj(self):
        """get objective value

        Raises:
        ValueError: if no objective value is stored
        """
        if self._obj.value is None:
            raise ValueError("no objective value is stored")
        return self._obj.value
    
    @property
    def variables(self):
        """get the results for the variables
        
        Raises:
        ValueError: if one variable has no value stored
        """
        def get_value(var): return var.value
        lst_values = list(map(get_value, self._variables.values()))
        return dict(zip(self._variables.keys(), lst_values))
    
    @property
    def solver_status(self):
        """get the status"""
        return self._solver_status

    def _process_solution(self, result_obj):
        """process the results of the solver"""
        self._obj = self._obj._replace(value=result_obj.objective_value)
        self._solver_status= result_obj.status
        if self._solver_status not in SolverStatusCode.get_values():
            raise ValueError("solver status unknown:", self._solver_status)

        for var in result_obj.variables:
            self._variables[var.name].set_value(var.value)

    def print_results(self):
        lst_lines = ["".join(["Status : ", self.solver_status])]
        lst_lines.append("".join(["Objective value : ", str(self.obj)]))
        lst_lines.extend(list(map(str, self._variables.values())))
        print("\n".join(lst_lines))

    def get_file_str(self):
        listLines = []
        listLines.append(str(self._obj.direction.value))
        listLines.append(str(self._obj.expr.lpstr()))
        listLines.append("Subject To")
        listLines.extend(c.lpstr() for c in self._constraints)
        listLines.append("Bounds")
        
        bound_lst = [v.lpstr_bounds() for v in self._variables.values()]
        listLines.extend(b for b in bound_lst if b)
        
        listLines.append("General")
        listLines.extend(v.lpstr_type() for v in self._variables.values())
        listLines.append("End")
        return "\n".join(listLines)


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
        self._operator = operator
        self._lhs = lhs
        self._rhs = rhs
        self.name = name

    def _format_str(self, lhs, rhs):
        namestr = "{}: ".format(self.name) if self.name else ""
        return "{}{} {} {}".format(namestr, lhs, self._operator, rhs)

    def lpstr(self):
        """get LP string for constraint"""
        lhs = self._lhs - self._rhs
        if not isinstance(lhs, Expr) or lhs.is_constant:
            raise ValueError("a constraint must have a least one variable")
        rhs = -lhs.constant
        lhs.constant = 0
        return self._format_str(lhs, rhs)

    def __str__(self):
        return self._format_str(self._lhs, self._rhs)


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

    def __init__(self, name, lb, ub, vartype):
        super(Var, self).__init__()
        self._name = name
        self.vartype = vartype
        self.lb = lb
        self.ub = ub
        self._value = None
        self.variables = {self: 1}

    def __hash__(self):
        return hash(str(self.name))

    @property
    def value(self):
        """get the value of the variable after solving

        Raises:
        ValueError: if no value has been computed yet
        """
        if self._value is None:
            raise ValueError("no solution computed")
        return self._value

    def set_value(self, val):
        """internal method to set value of variable"""
        self._value = val

    @property
    def name(self):
        """get the name of the variable"""
        return self._name

    def lpstr_bounds(self):
        """build the lp string"""
        return "{} <= {} <= {}".format(self.lb, self.name, self.ub)

    def lpstr_type(self):
        """return the var name if var is discrete"""
        if self.vartype == VarType.CONTINIOUS:
            return ""
        if self.vartype == VarType.INTEGER:
            return self.name
        raise ValueError("not a valid variable type {}".format(self.vartype))

    def __iadd__(self, other):
        expr = self.get_copy()
        expr += other
        return expr

    def __imul__(self, other):
        expr = self.get_copy()
        expr *= other
        return expr
    
    def __str__(self):
        return "".join([self._name, " : ", str(self._value)])
