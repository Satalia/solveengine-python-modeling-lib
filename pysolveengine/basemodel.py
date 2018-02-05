# -*- coding: utf-8 -*-
"""Base Class for communication with the Solve Engine Solver
"""

from collections import namedtuple
import logging
from sys import stdout

from .client import GrpcClient, HttpClient
from .helper import _get_logger, check_instance
from .config import SolverStatusCode, SEStatusCode

LOGGER = _get_logger()


class BaseModel(object):
    """BaseModel class

    Base Class for communication with the SolveEngine Solver

    Attributes:
    token: the SolveEngine token provided by the website, also called "api_key"
    this is necessary to connect to the solver

    file_name: the file_name that the uploaded file should have,
    default is model.lp, must end with .lp

    id: job id provided by Solve Engine when sending a new problem
    
    options : contain :
        sleep_time: the time we should sleep between checks if the SolveEngine
                    is finished solving the problem
        debug(boolean): active the debug output

    __solver_status: status of the solution returned by SE
    __se_status: current status of the solving processus
    """
    OPTIONS = namedtuple("Options", 'sleep_time debug')

    def __init__(self, token, file_name, sleep_time=2, debug=False,
                 file_ending=".lp", interactive_mode=False, http_mode=False):
        if debug:
            LOGGER.setLevel(logging.DEBUG)
        if file_ending not in [".lp", ".cnf"]:
            raise ValueError("File type {} not supported".format(file_ending))

        _check_init(token, sleep_time,
                    debug, interactive_mode,
                    http_mode)

        self.__file_name = file_name
        self.__token = token
        self.__id = None
        self.__options = BaseModel.OPTIONS(sleep_time, debug)
        self.__solver_status = str(SolverStatusCode.NOTSTARTED)
        self.__se_status = str(SEStatusCode.NOTSTARTED)

        self.interactive = interactive_mode
        self.use_http = http_mode
        
        if self.use_http:
            self.client = HttpClient(self, self.__token,
                                             self.__options.sleep_time)
        else:
            self.client = GrpcClient(self, self.__token,
                                             self.__options.sleep_time)

        LOGGER.debug("creating model with file_name= " + self.__file_name)

    def reinit(self):
        """
        Reinitialise the model/job characteristics that are not init parameters
        :return: Nothing
        """
        self.__id = None
        self.__solver_status = str(SolverStatusCode.NOTSTARTED)
        self.__se_status = str(SEStatusCode.NOTSTARTED)

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

        self.__id, self.__se_status, result = self.client.manage_solving()
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
    def file_name(self):
        """get the name chosen for the file"""
        return self.__file_name

    def print_if_interactive(self, msg):
        """print a line replacing the current one only if mode interactive asked"""
        if self.interactive:
            stdout.write("".join(["\r", msg, " " * 20]))


def _check_init(token, sleep_time,
                debug, interactive_mode,
                http_mode):
    """
    Check that all the initialising input suit the model

    :param token: string value of the id needed
            from SolveEngine to identify the user
    :param sleep_time: double value of the time
            requested by the user between two
            status requests of the job
    :param debug: boolean value, True if the
            user doesn't want debug messages to be displayed
    :param interactive_mode: boolean, True if the
            user wants solving status messages to be displayed
    :param http_mode: boolean, True if the user
            wants the requests to follow http methods,
            instead it will use GRPC
    :return:
    """
    check_instance(fct_name="init model", value=token,
                   name="token", type_=str)
    check_instance(fct_name="init model", value=sleep_time,
                   name="sleep_time", type_=(int, float))
    check_instance(fct_name="init model", value=debug,
                   name="debug", type_=bool)
    check_instance(fct_name="init model", value=interactive_mode,
                   name="interactive_mode", type_=bool)
    check_instance(fct_name="init model", value=http_mode,
                   name="http_mode", type_=bool)
