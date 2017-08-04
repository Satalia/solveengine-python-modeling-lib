# -*- coding: utf-8 -*-
"""Base Class for communication with the Solve Engine Solver
"""

from collections import namedtuple
import logging
from sys import stdout

from .connection import GrpcConnection, HttpConnection
from .helper import _get_logger
from .config import SolverStatusCode, SEStatusCode

LOGGER = _get_logger()

class BaseModel(object):
    """BaseModel class

    Base Class for communication with the SolveEngine Solver

    Attributes:
    token: the SolveEngine token provided by the website, also called "api_key"
    this is necessary to connect to the solver

    filename: the filename that the uploaded file should have,
    default is model.lp, must end with .lp

    id: job id provided by Solve Engine when sending a new problem
    
    sleeptime: the time we should sleep between checks if the SolveEngine
    is finished solving the problem

    debug(boolean): active the debug output
    """
    OPTIONS = namedtuple("Options", 'sleeptime debug')

    def __init__(self, token, filename="model", sleeptime=2, debug=False, 
                 file_ending=".lp", interactive_mode=False, http_mode=False):
        if debug:
            LOGGER.setLevel(logging.DEBUG)
        if file_ending not in [".lp", ".cnf"]:
            raise ValueError("Filetype {} not supported".format(file_ending))
        self._file_ending = file_ending
        self._filename = filename + file_ending
        self._token = token
        self._id = None
        self._options = BaseModel.OPTIONS(sleeptime, debug)
        self._solver_status = str(SolverStatusCode.NOTSTARTED)
        self._se_status = str(SEStatusCode.NOTSTARTED)
        
        self.interactive = interactive_mode
        self.use_http = http_mode
        
        if self.use_http:
            self.connection = HttpConnection()
        else:
            self.connection = GrpcConnection(self._token)
            
        LOGGER.debug("creating model with filename= " + self._filename)

    def _get_file_str(self):
        raise NotImplementedError()

    def _process_solution(self, result):
        raise NotImplementedError()

    def solve(self):
        """solve the model
        
        Encode the problem
        Upload it to Solve engine, getting a job id back
        schedule the created job,
        ask for the job status until it is finished,
        ask for and interprete the results
        
        Raises:
        Error: if there is a connection problem
        """

        self._id, self._se_status, result = self.connection.manage_solving(self)
        self._process_solution(result)
        LOGGER.debug("Results obtained : {}".format(self._solver_status))    

        self.print_if_interactive("Solving done : {}".format(self._solver_status))

    @property
    def solver_status(self):
        """get the status the solver reported of the result"""
        return self._solver_status
    
    @property
    def job_id(self):
        """ get the ID of the job sent to Solve Engine"""
        return self._id
    
    @property
    def se_status(self):
        """get the job status the solver reported while solving"""
        return self._se_status
    
    @property
    def filename(self):
        """get the name chosen for the file"""
        return self._filename
    
    def update_filename(self, name):
        """update the name of the file that will be sent to solveengine
        after adding the file ending in case
        """
        if not name.endswith(self._file_ending):
            name = "".join([name, self._file_ending])
        self._filename = name
    
    def print_problem(self):
        """ print the entire problem in the asked format"""
        print(self.get_file_str())

    def print_if_interactive(self, msg):
        """print a line replacing the current one only if mode interactive asked"""
        if self.interactive:
            stdout.write("".join(["\r", msg, " " * 20]))