#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import grpc
import time
import base64 as b64
import requests

from .config import SE_URL_HTTP, SE_URL_GRPC, SEStatusCode, SEUrls
from .svc_jobs_pb2_grpc import JobStub
from .svc_jobs_pb2 import Problem, JobRequest, CreateJobRequest
from .helper import _get_logger, unusual_answer, SERequests, build_err_msg, ObjResponse

LOGGER = _get_logger()


class BaseClient(object):
    """
    MIPModel class

        Create an instance to help connection with SE

        Attributes:
        model(BaseModel): the model where all the problem attributes are
        sleep_time: he time we should sleep between checks if the SolveEngine
                    is finished solving the problem
    """
    def __init__(self, model, sleep_time):
        """
        Initialises a base instance of client
        :param model: the model instance of the problem to solve
        :param sleep_time: the double value to indicate the time
                    to wait between 2 status requests
        """
        self.model = model
        self.sleep_time = sleep_time
        self.job_id = ""
        self._job_created = False
        self._job_scheduled = False
        self._job_done = False

    def manage_solving(self):
        """
        Go Through all the steps for solving a problem

        :return:
            job_id: the id of the solved job,
                returned because must be updated into the job class
            se_status: the status of the job (interupted/completed/failed/ etc.

        """
        if not self._job_created:
            self._create_job()
            self._job_created = True

        if not self._job_scheduled:
            self._schedule_job()
            self._job_scheduled = True

        if not self._job_done:
            se_status = self._wait_results()
            self._job_done = True

        result = self._get_solution()

        return self._id, se_status, result


class GrpcClient(BaseClient):
    def __init__(self, model, token, sleep_time):
        """
        Init the http kind of client

        :param model: the instance of the problem
        :param token: the string file of the api-key needed to
                    recognize the user
        :param sleep_time: the double value to indicate the time
                    to wait between 2 status requests
        :update _grpc_metadata, _solve_engine
        """
        super(GrpcClient, self).__init__(model=model,
                                         sleep_time=sleep_time)
        self._prepare_grpc()
        self.__grpc_metadata = [("authorization", "".join(["api-key ", token]))]

    def _prepare_grpc(self):
        """prepare objects needed for grpc"""
        creds = grpc.ssl_channel_credentials()
        channel = grpc.secure_channel(SE_URL_GRPC, creds)
        self._solve_engine = JobStub(channel)

    def _create_job(self):
        """
        create a job by sending the problem to Solveengine
        return the id of the 'job' created in the solve engine network

        :updates:
            updates client._id
        """
        LOGGER.debug("Creating Solve Engine job...")
        pb_data = self.model.build_str_model().encode('ascii')
            
        pb = Problem(name=self.model.file_name, data=pb_data)

        req = CreateJobRequest(problems=[pb], options={})
        try:
            resp_obj = self._solve_engine.Create(req, metadata=self.__grpc_metadata)
        except grpc.RpcError as err:
            raise grpc.RpcError(err.details())

        if unusual_answer(resp_obj, SERequests.CREATE_JOB):
            raise ValueError(build_err_msg(resp_obj))
        self._id = resp_obj.id
       
        LOGGER.debug("Job created {}".format(self._id))

    def _schedule_job(self):
        """
        launches the resolution of the job just created
        """
        LOGGER.debug("Scheduling Solve Engine job...")

        try:
            self._solve_engine.Schedule(JobRequest(id=self._id),
                                        metadata=self.__grpc_metadata)
        except grpc.RpcError as err:
            raise grpc.RpcError(err.details())

        LOGGER.debug("Job scheduled")

    def _get_status(self):
        """
        asks for the status of the job
        :return: the string value for the job status
        """
        try:
            resp_obj = self._solve_engine.Status(JobRequest(id=self._id),
                                                 metadata=self.__grpc_metadata)
        except grpc.RpcError as err:
            raise grpc.RpcError(err.details())

        if unusual_answer(resp_obj, SERequests.GET_STATUS):
            raise ValueError(build_err_msg(resp_obj))

        return str(resp_obj.status)

    def _wait_results(self):
        """
        asks for the status of the solving until it finishes

        :return:
            status: string file describing the status of the job
        """
        sec_cnt = 0
        while True:

            se_status = self._get_status()

            msg = "".join(["Solving the problem, status : ", se_status,
                           " - waiting time : ", str(sec_cnt), "s"])
            LOGGER.debug(msg)
            self.model.print_if_interactive(msg)
            
            if se_status == SEStatusCode.COMPLETED:
                break
            elif se_status == SEStatusCode.FAILED:
                raise ValueError("Error with Solve engine : problem solving failed")
            elif se_status == SEStatusCode.TIMEOUT:
                raise ValueError("".join(["Error with Solve engine :",
                                          " the time limit (10min by default)",
                                          " has been reached before solving the problem"]))
            elif se_status == SEStatusCode.STOPPED:
                raise ValueError("Error with Solve engine : the job has been manually cancelled")

            time.sleep(self.sleep_time)
            sec_cnt += 1
        return se_status

    def _get_solution(self):
        """
        asks Solveengine the results of the problem

        :return:
        result: an instance containing the solution of the problem
            (objective value, variables, status)
        """
        LOGGER.debug("Getting results...")
        
        try:
            resp_obj = self._solve_engine.GetResults(JobRequest(id=self._id),
                                                     metadata=self.__grpc_metadata)
        except grpc.RpcError as err:
            raise grpc.RpcError(err.details())

        if unusual_answer(resp_obj, SERequests.GET_RESULT):
            raise ValueError(build_err_msg(resp_obj))
        result = resp_obj.result
        current_id = resp_obj.job_id

        if current_id != self._id:
            raise ValueError("Wrong Job_ID, Server Error")
        
        return result


class HttpClient(BaseClient):
    def __init__(self, model, token, sleep_time):
        """
        Init the http kind of client

        :param model: the instance of the problem
        :param token: the string file of the api-key needed to
                    recognize the user
        :param sleep_time: the double value to indicate the time
                    to wait between 2 status requests
        """
        super(HttpClient, self).__init__(model=model,
                                         sleep_time=sleep_time)
        self.__headers = {"Authorization": "api-key {}".format(token)}
    
    def _create_job(self):
        """
        create a job by sending the problem to Solveengine
        return the id of the 'job' created in the solve engine network

        :updates:
            updates client._id
        """
        LOGGER.debug("Creating Solve Engine job...")
        pb_data = self.model.build_str_model().encode('ascii')

        pb_data = b64.b64encode(pb_data).decode('utf-8')

        dict_data = dict(problems=[dict(name=self.model.file_name, data=pb_data)])
        resp = self._send("post", with_job_id=False, json=dict_data)

        solution = ObjResponse(resp, SERequests.CREATE_JOB)
        if solution.unusual_answer:
            raise ValueError(solution.build_err_msg)
        self._id = solution.job_id
       
        LOGGER.debug("Job created {}".format(self._id))

    def _schedule_job(self):
        """
        launches the resolution of the job just created
        """
        LOGGER.debug("Scheduling Solve Engine job...")

        resp = self._send("post", SEUrls.SCHEDULE_URL)
        
        solution = ObjResponse(resp, SERequests.SCHEDULE_JOB)
        if solution.unusual_answer:
            raise ValueError(solution.build_err_msg)

        LOGGER.debug("Job scheduled")

    def _get_status(self):
        """
        asks for the status of the job
        :return: the string value for the job status
        """
        resp = self._send("get", SEUrls.STATUS_URL)

        solution = ObjResponse(resp, SERequests.GET_STATUS)
        if solution.unusual_answer:
            raise ValueError(solution.build_err_msg)
        return str(solution.job_status)

    def _wait_results(self):
        """
        asks for the status of the solving until it finishes

        :return:
            status: string file describing the status of the job
        """
        sec_cnt = 0
        while True:
            se_status = self._get_status()
            
            msg = "".join(["Solving the problem, status : ", se_status,
                           " - waiting time : ", str(sec_cnt), "s"])
            LOGGER.debug(msg)
            self.model.print_if_interactive(msg)
            
            if se_status == SEStatusCode.COMPLETED:
                break
            elif se_status == SEStatusCode.FAILED:
                raise ValueError("Error with Solve engine : problem solving failed")
            elif se_status == SEStatusCode.TIMEOUT:
                raise ValueError("".join(["Error with Solve engine :",
                                          " the time limit (10min by default)",
                                          " has been reached before solving the problem"]))
            elif se_status == SEStatusCode.STOPPED:
                raise ValueError("Error with Solve engine : the job has been manually cancelled")

            time.sleep(self.sleep_time)
            sec_cnt += 1
        return se_status

    def _get_solution(self):
        """
        asks Solveengine the results of the problem

        :return:
        result: an instance containing the solution of the problem
            (objective value, variables, status)
        """
        LOGGER.debug("Getting results...")
        
        resp = self._send("get", SEUrls.RESULTS_URL)
        result = ObjResponse(resp, SERequests.GET_RESULT)
        if result.unusual_answer:
            raise ValueError(result.build_err_msg)
        current_id = result.job_id

        if current_id != self._id:
            raise ValueError("Wrong Job_ID, Server Error")

        return result
    
    def _send(self, msgtype="post", path=None, with_job_id=True, **kwargs):
        """
        send an http request to solveengine

        :param msgtype: string type, post/get/etc.
        :param path: what must complete the base url
        :param with_job_id: true if we should add the job_id in the url
        :param kwargs: args for the requests function.
            Here must a json additional string file
        :return:
            return the instance returned from the request
            built from a json format
        """
        url = "".join([SE_URL_HTTP,
                       "".join([self._id, "/"]) if with_job_id else "",
                       str(path) if path else ""])
        try:
            result = getattr(requests, msgtype)(url, headers=self.__headers, **kwargs)
        except requests.RequestException as err:
            raise requests.RequestException(err.response)

        LOGGER.debug("request result: " + result.text)
        result.raise_for_status()
        return result.json()
