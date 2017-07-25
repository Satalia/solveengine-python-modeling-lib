"""
This file presents how to create a SATModel, add variables, add constraints and solve the model using the SolveEngine python interface
"""
from solveengine import SATModel, VarType, SEStatusCode, SolverStatusCode

######################################
# create SAT model
#
# the token
token = "2prMEegqCAFB5eqmfuXmGufyJ+PcMzJbZaQcvqrhtx4="
staticmethod
# the name of the file being used when uploading the problem file
# (to be able to find the file in the webinterface of the SolveEngine easier)
# default: model
filename = "special_model"

# the time (in seconds) the model class waits before checking the server if the result is ready
# the smaller the number the shorter the intervals
sleeptime = 3

# with/without debug printout
# this does not print debug information for the solvers
debug = True

#if True, messages will be printed to keep updated on the status of the solving
interactive_mode = True

#web connection works by default with grpc, which is faster
#if http connections desired set it to True
http_mode = False

model = SATModel(token, filename=filename, sleeptime=sleeptime, 
                 debug=debug, interactive_mode=interactive_mode,
                 http_mode=http_mode)

######################################
######################################
#BUILDING STEP BY STEP
######################################
# Creating Variables
#
#an integer id is automatically given to each variable
#the id is the smallest available integer
x1 = model.add_variable("x1")
x2 = model.add_variable("x2")

#you can define an id yourself, but it is not advised
x3 = model.add_variable("x3", id_=3)

# Building expressions
#
# !x1 means negative(x1)
expr = !x1

# | is used for 'OR'; & is used for 'AND'
expr = (x1 | x2) & x3

# ^ is used for 'XOR'  (equivalent to (x1 | x2) & !(x1 & x2)
expr = x1 ^ x2

# (==, !=, <=) are used to express equivalence, non equivalence and implication
expr = (x1 == x2) <= (x1 != x3)

# Add constraint
model.add_constraint_expr(expr)

######################################
######################################
#BUILDING WITH A LIST
######################################
# This way uses only the integer ids
# You cannot use the id 0
# no need to build the variables first
#they will be automatically added to the model with a generated name

#Add a constraint (only linked by 'OR')  (equivalent to : x1 | !x5 | x2)
model.add_constraint_vector([1, -5, 2])

#You can also add several constraints in once
#there can be expression as well as vectors
lst_constraints = []
lst_constraints.append([1,-2,5])
lst_constraints.append(expr)
model.add_list_constraints(lst_constraints=lst_constraints)

######################################
######################################
# check the model
#
print(model.get_file_str())

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
if model.solver_status == SEStatusCode.COMPLETED:

    # print solver status
    print("solver status:", model.solver_status)

    # status codes with solution
    if model.solver_status in [SolverStatusCode.SATISFIABLE]:

        # print variable values : 1 if True, -1 if False
        print("x1=", x1.value)
        print("x2=", x2.value)
        
        #print variables values
        for key, value in model.variables:
            print(key, "=", value)
        
        #print summary
        model.print_result()

    # status codes without solution
    elif model.solver_status in [SolverStatusCode.UNSATISFIABLE]:
        print("the solver returned that the problem is unsatisfiable")

# status codes for an unsuccessful run
if model.se_status in [SEStatusCode.FAILED, SEStatusCode.STOPPED, SolverStatusCode.INTERRUPTED]:
    print("something went wrong")
if model.se_status in [SEStatusCode.TIMEOUT]:
    print("time limit has been reached")
