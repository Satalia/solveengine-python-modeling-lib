from .helper import StrEnum
from enum import Enum
import os

# Solve Engine API key
SE_URL_GRPC = 'solve.satalia.com:443'
SE_URL_HTTP = 'https://solve.satalia.com/api/v2/jobs/'
EXAMPLE_SAT_PATH = 'examples/usage_sat.py'
EXAMPLE_MIP_PATH = 'examples/usage_mip.py'
WORKING_DIR = os.path.dirname(os.path.realpath(__file__))


def help_sat():
    """returns the str value for the content
    of the example usage for SAT modelling
    """
    with open(os.path.join(WORKING_DIR, EXAMPLE_SAT_PATH), 'r') as f:
        res = f.read()
        f.close()
    return res


def help_mip():
    """returns the str value for the content
        of the example usage for MIP modelling
    """
    with open(os.path.join(WORKING_DIR, EXAMPLE_MIP_PATH), 'r') as f:
        res = f.read()
        f.close()
    return res


class SEUrls(StrEnum):
    """part of URL to add to the origin one for http requests"""
    RESULTS_URL= "results"
    STATUS_URL = "status"
    SCHEDULE_URL = "schedule"


class SolverStatusCode(StrEnum):
    """Enum for the status codes returned by the solvers"""
    INTERRUPTED = "interrupted"
    NOTSTARTED = "notstarted"
    OPTIMAL = "optimal"
    INFEASIBLE = "infeasible"
    UNBOUNDED = "unbounded"
    SATISFIABLE = "satisfiable"
    UNSATISFIABLE = "unsatisfiable"


class SEStatusCode(StrEnum):
    """Enums for the status codes returned by SE"""
    NOTSTARTED = "notstarted"
    QUEUED = "queued"
    STARTED = "started"
    STARTING = "starting"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    TIMEOUT = "timeout"

