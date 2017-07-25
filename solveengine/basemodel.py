# -*- coding: utf-8 -*-
"""Base Class for communication with the Solve Engine Solver
"""

from collections import namedtuple
import logging
import time
import requests
import base64 as b64
import sys
import grpc

from svc_jobs_pb2_grpc import JobStub
from svc_jobs_pb2 import Problem, JobRequest, CreateJobRequest

from helper import _get_logger, StrEnum, unusual_answer, SERequests, build_err_msg, ObjResponse

LOGGER = _get_logger()


class SolverStatusCode(StrEnum):
    """Enum for the status codes returned by the solvers"""
    INTERUPTED = "interupted"
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

class SEUrls(StrEnum):
    """part of URL to add to the origin one for http requests"""
    RESULTS_URL= "results"
    STATUS_URL = "status"
    SCHEDULE_URL = "schedule"

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
    JOB_ID = "job_id"
    OPTIONS = namedtuple("Options", 'sleeptime debug')
    BASEURL = "https://solve.satalia.com/api/v2/jobs/"

    def __init__(self, token, filename="model", sleeptime=2, debug=False, 
                 file_ending=".lp", interactive_mode=False, http_mode=False):
        if debug:
            LOGGER.setLevel(logging.DEBUG)
        if file_ending not in [".lp", ".cnf"]:
            raise ValueError("Filetype {} not supported".format(file_ending))
        self._filename = filename + file_ending
        self._token = token
        self._id = None
        self._options = BaseModel.OPTIONS(sleeptime, debug)
        self._solver_status = str(SolverStatusCode.NOTSTARTED)
        self._se_status = str(SEStatusCode.NOTSTARTED)
        
        self.interactive = interactive_mode
        self.use_http = http_mode
        
        self._headers = {"Authorization": "api-key {}".format(self._token)}
        self._grpc_metadata = [("authorization", "".join(["api-key ", self._token]))]
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
        
        if not self.use_http:
            self._prepare_grpc()
        
        self._create_job()
        self._schedule_job()
        self._wait_results()
        self._get_solution()
        
        #todo remove if less interaction with user
        self.print_if_interactive("Solving done : {}".format(self._solver_status))

    def _prepare_grpc(self):
        creds = grpc.ssl_channel_credentials()
        channel = grpc.secure_channel("solve.satalia.com:443", creds)
        self._solve_engine = JobStub(channel)

    def _create_job(self):
        LOGGER.debug("Creating Solve Engine job...")
        pb_data = self.get_file_str().encode('ascii')
 
        if self.use_http:
            pb_data = b64.b64encode(pb_data).decode('utf-8')
        
            dict_data = dict(problems=[dict(name=self._filename, data=pb_data)])
            resp = self._send("post", with_job_id=False, json=dict_data)
        
            solution = ObjResponse(resp, SERequests.CREATE_JOB)
            if solution.unusual_answer:
                raise ValueError(solution.build_err_msg)
            self._id = solution.job_id
            
        else:
            pb = Problem(name=self._filename, data=pb_data)

            req = CreateJobRequest(problems=[pb], options={})
            resp_obj = self._solve_engine.Create(req, metadata=self._grpc_metadata)

            if unusual_answer(resp_obj, SERequests.CREATE_JOB):
                raise ValueError(build_err_msg(resp_obj))
            self._id = resp_obj.id
       
        LOGGER.debug("Job created {}".format(self._id))

    def _schedule_job(self):
        LOGGER.debug("Scheduling Solve Engine job...")

        if self.use_http:
            resp = self._send("post", SEUrls.SCHEDULE_URL)
        
            solution = ObjResponse(resp, SERequests.SCHEDULE_JOB)
            if solution.unusual_answer:
                raise ValueError(solution.build_err_msg)
        else:
            self._solve_engine.Schedule(JobRequest(id=self._id), metadata=self._grpc_metadata)

        LOGGER.debug("Job scheduled")

    def _wait_results(self):
        sec_cnt = 0
        while True:
            if self.use_http:
                resp = self._send("get", SEUrls.STATUS_URL)

                solution = ObjResponse(resp, SERequests.GET_STATUS)
                if solution.unusual_answer:
                    raise ValueError(solution.build_err_msg)
                self._se_status = solution.job_status
            else:
                resp_obj = self._solve_engine.Status(JobRequest(id=self._id), metadata=self._grpc_metadata)
            
                if unusual_answer(resp_obj, SERequests.GET_STATUS):
                    raise ValueError(build_err_msg(resp_obj))
                self._se_status = resp_obj.status
            
            msg = "".join(["Solving the problem, status : ", self._se_status,
                           " - waiting time : ", str(sec_cnt),"s"])
            LOGGER.debug(msg)
            self.print_if_interactive("".join(["\r" * (len(msg) * 2), msg, " " * 20]))
            
            if self._se_status == SEStatusCode.COMPLETED:
                break
            elif self._se_status == SEStatusCode.FAILED:
                raise ValueError("Error with Solve engine : problem solving failed")
            elif self._se_status == SEStatusCode.TIMEOUT:
                raise ValueError("Error with Solve engine : the time limit (10min by default) has been reached before solving the problem")
            elif self._se_status == SEStatusCode.STOPPED:
                raise ValueError("Error with Solve engine : the job has been manually cancelled")
            
            #todo think about adding a superficial timeout option for models
            time.sleep(1)
            sec_cnt += 1

    def _get_solution(self):
        LOGGER.debug("Getting results...")
        
        if self.use_http:
            resp = self._send("get", SEUrls.RESULTS_URL)
            result = ObjResponse(resp, SERequests.GET_RESULT)
            if result.unusual_answer:
                raise ValueError(result.build_err_msg)
            current_id = result.job_id

        else:
            resp_obj = self._solve_engine.GetResults(JobRequest(id=self._id), metadata=self._grpc_metadata)

            if unusual_answer(resp_obj, SERequests.GET_RESULT):
                raise ValueError(build_err_msg(resp_obj))
            result = resp_obj.result
            current_id = resp_obj.job_id

        if current_id != self._id:
            raise ValueError("Wrong Job_ID, Server Error")

        self._process_solution(result)
        LOGGER.debug("Results obtained : {}".format(self._solver_status))    
    
    @property
    def solver_status(self):
        """get the status the solver reported of the result"""
        return self._solver_status
    
    @property
    def se_status(self):
        """get the job status the solver reported while solving"""
        return self._se_status

    def print_problem(self):
        print(self.get_file_str())

    def _send(self, msgtype="post", path=None, with_job_id=True, **kwargs):
        url = "".join([BaseModel.BASEURL,
                       "{}/".format(self._id) if with_job_id else "",
                       str(path) if path else ""])
        result = getattr(requests, msgtype)(url, headers=self._headers, **kwargs)
        LOGGER.debug("request result: " + result.text)
        result.raise_for_status()
        return result.json()

    def print_if_interactive(self, msg):
        if self.interactive:
            sys.stdout.write("".join(["\r" * 500, msg, " " * 100]))