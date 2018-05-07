"""
This file presents how to create a MIPModel, add variables, add constraints and solve the model using the SolveEngine python interface
"""
from pysolveengine import MIPModel, INF, Direction, SEStatusCode, SolverStatusCode

######################################
# create MIP model
#
# the token
token = "2prMEegqCAFB5eqmfuXmGufyJ+PcMzJbZaQcvqrhtxg="

# the name of the file being used when uploading the problem file
# (to be able to find the file in the webinterface of the SolveEngine easier)
# default: model
model_name = "special_model"

# the time (in seconds) the model class waits before checking the server if the result is ready
# the smaller the number the shorter the intervals
sleep_time = 3

# with/without debug printout
# this does not print debug information for the solvers
debug = True

#if True, messages will be printed to keep updated on the status of the solving
interactive_mode = True

#web connection works by default with grpc, which is faster
#if http connections desired set it to True
http_mode = False

model = MIPModel(token, model_name=model_name, sleep_time=sleep_time,
                 debug=debug, interactive_mode=interactive_mode,
                 http_mode=http_mode)

# two ways to set the objective direction of the model
model.set_to_minimize()
# or
model.set_direction(Direction.MINIMIZE)

######################################
######################################
#BUILDING STEP BY STEP
######################################
# Creating Variables
#
# for all methods we have the default bounds:
# lb=-INF
# ub=INF

# binary variable
x1 = model.add_binary_var(name="x1")
x2 = model.add_binary_var("x2")

# integer variable
# note that for y1, ub=INF is set by default
y1 = model.add_integer_var(name="y1", lb=-13)
y2 = model.add_integer_var(name="y2", lb=-13, ub=INF)

# continuous variable
# note that for z2, lb=-INF is set by default
z2 = model.add_continuous_var("z2", ub=23)
z3 = model.add_continuous_var("z3", lb=-INF, ub=23)

# example of a continuous variable with lb=-INF, ub=INF
z1 = model.add_continuous_var("z1")

# if a variable you added is lost, you can get it back with get_variable()
z1 = model.get_variable("z1")

# change / print bounds
z1.lb = 12
z1.ub = 34
print("z1 lb=", z1.lb)
print("z1 ub=", z1.ub)

# print name
print("z1 name=", z1.name)

######################################
# creating expressions
#
# building linear expression
expr = 2*x1 + 3*y1 + z1 + 4

# print expression
print("expr=", expr)
print("expr=", str(expr))

# check if expr is constant
print("expr is constant?", expr.is_constant) # False

# check if two expr are equal on a semantic level
expr2 = 2*x1 + z1 + 4 + 2*y1 + y1
print("expr equals expr2?", expr.equals(expr2)) # True

# modify expression
expr -= x1
expr += x2
expr *= 3

######################################
# create constraint using <=, == or >=
#
constr1 = expr <= x2 + 4*z3 - 5

# add constraints to model, the name is optional
model.add_constraint(constr1, name="some constraint")
model.add_constraint(y1 >= -12 + y2)
model.add_constraint(x1 == z2 + 4)

######################################
# setting objective
#
# the objective is an expression
model.set_obj(expr + 12*y2)

######################################
######################################
#BUILDING MODEL WITH MATRICES (LIKE MATLAB)
######################################
#This way will reset the model and build it using matrices following this syntax :
#f, b, beq, lb, ub : lists of real numbers
#A, Aeq: matrices of real numbers
#int_list, bin_list: lists of 0 or 1

#such that it matches with this model

#                 {   A * x <= b
#min fx such that { Aeq * x  = beq
# x               {    lb <= x <= ub
#                 { x[i] integer if int_list[i] = 1
#                 { x[i] binary if bin_list[i] = 1
######################################

import numpy as np

######################################
#Set the matrices
#
#objective function
f = [-2,1,3]
#or
f = np.array([-2, 1, 3])

#inequality constraints coefficients : left and right sides
A = np.array([[2, 3, 1], [-1, 0, 4]])
#or
A = [[2, 3, 1], [-1, 0, 4]]

b = [1, 0]

#[equality constraints coefficients : left and right sides]
Aeq = np.array([[1, 5, 0]])
#or
Aeq = [[1, 5, 0]]
beq = [-2.5]

#[lower and upper bounds]
lb = [-INF, 1, -1]
ub = [5, 10, INF]

#[list of integer/binary variables, 1 for integer/binary]
#In case of conflict with bounds, binary has priority
int_list = [0, 0, 1]
bin_list = [1, 0, 0]

# these inputs can as well be classes that return something with respectively [i][j] and [i]
# all the values inside must be called in float()

######################################
#Reset the model and set it using these matrices
model.build_with_matrices(f, A, b,
                          Aeq=Aeq, beq=beq, lb=lb, ub=ub, #optional
                          int_list=int_list, bin_list=bin_list) #optional

######################################
# check the model
#
print(model.build_str_model())
print(model.file_name)

# You can know the index for each constraint by printing them
model.print_constraints()
# You can remove constraint knowing its index
model.remove_constraint_with_index(index=-1)

# At all time you can reinitialise the model's status/cosntraints/variables
#
model.reinit()

# solving the model
#
model.solve()
######################################
# checking the result status and getting the result
#
# there are two different status values
# print SolveEngine status
print("status=", model.se_status)

# if solve was successful
if model.se_status == SEStatusCode.COMPLETED:

    # print solver status
    print("solver status:", model.solver_status)

    # status codes with solution
    if model.solver_status in [SolverStatusCode.OPTIMAL]:

        # print obj value
        print("obj=", model.obj)

        # print variable values
        print("x1=", x1.value)
        print("x2=", x2.value)
        print("y1=", y1.value)
        print("y2=", y2.value)
        print("z1=", z1.value)
        print("z2=", z2.value)
        print("z3=", z3.value)
        
        #or
        for key, value in model.var_results:
            print(key, "=", value)
            
        #print summary
        model.print_results()

    # status codes without solution
    if model.solver_status in [SolverStatusCode.INFEASIBLE,
                               SolverStatusCode.UNBOUNDED]:
        print("the solver did not return a solution")

# status codes for an unsuccessful run
if model.se_status in [SEStatusCode.FAILED,
                       SEStatusCode.STOPPED,
                       SEStatusCode.INTERRUPTED]:
    print("something went wrong")
if model.se_status in [SEStatusCode.TIMEOUT]:
    print("time limit has been reached")
