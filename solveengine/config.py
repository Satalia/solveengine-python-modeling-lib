from .helper import StrEnum
from enum import Enum
# Solve Engine API key
SE_URL_GRPC = 'solve.satalia.com:443'
SE_URL_HTTP = 'https://solve.satalia.com/api/v2/jobs/'
LOGGER_NAME = "satalia_solve_engine_logger"
EXAMPLE_SAT_PATH = 'examples/usage_sat.py'
EXAMPLE_MIP_PATH = 'examples/usage_mip.py'

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
    STARTING = 'starting'
    COMPLETED = 'completed'
    STOPPED = 'stopped'
    FAILED = 'failed'
    INTERRUPTED = 'interrupted'
    TIMEOUT = 'timeout'

