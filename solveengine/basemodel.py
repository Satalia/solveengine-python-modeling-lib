# -*- coding: utf-8 -*-
"""Base Class for communication with the Solve Engine Solver
"""

from collections import namedtuple
import logging
from sys import stdout

from .connection import GrpcConnection, HttpConnection
from .helper import _get_logger, check_instance
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
    OPTIONS = namedtuple("Options", 'sleep_time debug')

    def __init__(self, token, filename="model", sleep_time=2, debug=False,
                 file_ending=".lp", interactive_mode=False, http_mode=False):
        if debug:
            LOGGER.setLevel(logging.DEBUG)
        if file_ending not in [".lp", ".cnf"]:
            raise ValueError("File type {} not supported".format(file_ending))

        _check_init(token, filename, sleep_time,
                   debug, file_ending, interactive_mode,
                   http_mode)

        self.__file_ending = file_ending
        self.__filename = "".join([filename, self.__file_ending])
        self.__token = token
        self.__id = None
        self.__options = BaseModel.OPTIONS(sleep_time, debug)
        self.__solver_status = str(SolverStatusCode.NOTSTARTED)
        self.__se_status = str(SEStatusCode.NOTSTARTED)

        self.interactive = interactive_mode
        self.use_http = http_mode
        
        if self.use_http:
            self.connection = HttpConnection(self, self.__token,
                                             self.__options.sleep_time)
        else:
            self.connection = GrpcConnection(self, self.__token,
                                             self.__options.sleep_time)

        LOGGER.debug("creating model with filename= " + self.__filename)

    def build_str_model(self):
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

        self.__id, self.__se_status, result = self.connection.manage_solving()
        self.__solver_status = self._process_solution(result)
        LOGGER.debug("Results obtained : {}".format(self.solver_status))

        self.print_if_interactive("Solving done : {}".format(self.solver_status))
        if self.interactive:
            stdout.write("\n")

    @property
    def solver_status(self):
        """get the status the solver reported of the result"""
        return self.__solver_status
    
    @property
    def job_id(self):
        """ get the ID of the job sent to Solve Engine"""
        return self.__id
    
    @property
    def se_status(self):
        """get the job status the solver reported while solving"""
        return self.__se_status
    
    @property
    def filename(self):
        """get the name chosen for the file"""
        return self.__filename
    
    def update_filename(self, name):
        """update the name of the file that will be sent to solveengine
        after adding the file ending in case
        """
        if not name.endswith(self.__file_ending):
            name = "".join([name, self.__file_ending])
        self.__filename = name

    def print_if_interactive(self, msg):
        """print a line replacing the current one only if mode interactive asked"""
        if self.interactive:
            stdout.write("".join(["\r", msg, " " * 20]))

def _check_init(token, filename, sleep_time,
                   debug, file_ending, interactive_mode,
                   http_mode):
    check_instance(fct_name="init model", value=token,
                   name="token", type_=str)
    check_instance(fct_name="init model", value=filename,
                   name="filename", type_=str)
    check_instance(fct_name="init model", value=sleep_time,
                   name="sleep_time", type_=(int, float))
    check_instance(fct_name="init model", value=debug,
                   name="debug", type_=bool)
    check_instance(fct_name="init model", value=file_ending,
                   name="file_ending", type_=str)
    check_instance(fct_name="init model", value=token,
                   name="token", type_=str)


