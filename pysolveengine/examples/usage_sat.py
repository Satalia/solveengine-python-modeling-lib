"""
This file presents how to create a SATModel, add variables, add constraints and solve the model using the SolveEngine python interface
"""
from pysolveengine import SATModel, SEStatusCode, SolverStatusCode

######################################
# create SAT model
#
# the token
token = "#2prMEegqCAFB5eqmfuXmGufyJ+PcMzJbZaQcvqrhtx4="

# the name of the file being used when uploading the problem file
# (to be able to find the file in the webinterface of the SolveEngine easier)
# default: model
file_name = "special_model"

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

model = SATModel(token, model_name=file_name, sleep_time=sleep_time,
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

# if a variable is lost, you can use get_variable
x3 = model.get_variable_with_id(id_=3)
# or
x3 = model.get_variable_with_name(name="x3")

# Building expressions
#
# -x1 means negative(x1)
# when expression displayed, will show !x1
expr = -x1

# | is used for 'OR'; & is used for 'AND'
expr = (x1 | x2) & x3

# ^ is used for 'XOR'  (equivalent to (x1 | x2) & -(x1 & x2)
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

#Add a constraint (only linked by 'OR')  (equivalent to : x1 | -x5 | x2)
model.add_constraint_vector([1, -5, 2])

#You can also add several constraints in once
#there can be expression as well as vectors
lst_constraints = []
lst_constraints.append([1,-2,5])
lst_constraints.append(expr)
model.add_list_constraints(lst_constraints=lst_constraints)

######################################
######################################
#BUILDING WITH A FILE
######################################
# You can also easily build the model 
# using a file
# The file must contained a problem written
# in a cnf format, starting with p cnf

file_path = '/.../filename.cnf'
model.build_from_file(file_path=file_path)

######################################
######################################
# check the model
#
print(model.build_str_model())
model.print_constraints()
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
    if model.solver_status in [SolverStatusCode.SATISFIABLE]:

        # print variable values : 1 if True, -1 if False
        print("x1=", x1.value)
        #or
        print("x1=", model.var_results[1])
        #or
        print("x1=", model.var_name_results["x1"])        

        #or
        for key, value in model.var_name_results.items():
            print(key, "=", value)

        #or
        #print summary
        model.print_results()

    # status codes without solution
    elif model.solver_status in [SolverStatusCode.UNSATISFIABLE]:
        print("the solver returned that the problem is unsatisfiable")

# status codes for an unsuccessful run
if model.se_status in [SEStatusCode.FAILED,
                       SEStatusCode.STOPPED,
                       SEStatusCode.INTERRUPTED]:
    print("something went wrong")
if model.se_status in [SEStatusCode.TIMEOUT]:
    print("time limit has been reached")
