#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug  4 13:04:57 2017

@author: w848
"""
import grpc
import time
import base64 as b64
import requests

from .config import SE_URL_HTTP, SE_URL_GRPC, SEStatusCode, SEUrls
from .svc_jobs_pb2_grpc import JobStub
from .svc_jobs_pb2 import Problem, JobRequest, CreateJobRequest
from .helper import _get_logger, unusual_answer, SERequests, build_err_msg, ObjResponse

LOGGER = _get_logger()


class BaseConnection():
    def __init__(self, model, sleep_time):
        self.model = model
        self.sleep_time = sleep_time

    def manage_solving(self):
        self._create_job()
        self._schedule_job()
        se_status = self._wait_results()
        result = self._get_solution()

        return self._id, se_status, result


class GrpcConnection(BaseConnection):
    def __init__(self, model, token, sleep_time):
        """initiate the connection class for grpc"""
        super(GrpcConnection, self).__init__(model=model,
                                             sleep_time=sleep_time)
        self._prepare_grpc()
        self.__grpc_metadata = [("authorization", "".join(["api-key ", token]))]

    def _prepare_grpc(self):
        """prepare objects needed for grpc"""
        creds = grpc.ssl_channel_credentials()
        channel = grpc.secure_channel(SE_URL_GRPC, creds)
        self._solve_engine = JobStub(channel)

    def _create_job(self):
        """create a job by sending the problem to Solveengine
        return the id of the 'job' created in the solve engine network
        """
        LOGGER.debug("Creating Solve Engine job...")
        pb_data = self.model.build_str_model().encode('ascii')
            
        pb = Problem(name=self.model.filename, data=pb_data)

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
        """launch the resolution of the job just created"""
        LOGGER.debug("Scheduling Solve Engine job...")

        try:
            self._solve_engine.Schedule(JobRequest(id=self._id),
                                    metadata=self.__grpc_metadata)
        except grpc.RpcError as err:
            raise grpc.RpcError(err.details())

        LOGGER.debug("Job scheduled")

    def _wait_results(self):
        """asks for the status of the solving until it finishes"""
        sec_cnt = 0
        while True:
            try:
                resp_obj = self._solve_engine.Status(JobRequest(id=self._id),
                                                 metadata=self.__grpc_metadata)
            except grpc.RpcError as err:
                raise grpc.RpcError(err.details())

            if unusual_answer(resp_obj, SERequests.GET_STATUS):
                raise ValueError(build_err_msg(resp_obj))

            se_status = resp_obj.status
            
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
        """asks Solveengine the results of the problem"""
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


class HttpConnection(BaseConnection):
    def __init__(self, model, token, sleep_time):
        super(HttpConnection, self).__init__(model=model,
                                             sleep_time=sleep_time)
        self.__headers = {"Authorization": "api-key {}".format(token)}
    
    def _create_job(self):
        """create a job by sending the problem to Solveengine
        return the id of the 'job' created in the solve engine network
        """
        LOGGER.debug("Creating Solve Engine job...")
        pb_data = self.model.build_str_model().encode('ascii')

        pb_data = b64.b64encode(pb_data).decode('utf-8')

        dict_data = dict(problems=[dict(name=self.model.filename, data=pb_data)])
        resp = self._send("post", with_job_id=False, json=dict_data)

        solution = ObjResponse(resp, SERequests.CREATE_JOB)
        if solution.unusual_answer:
            raise ValueError(solution.build_err_msg)
        self._id = solution.job_id
       
        LOGGER.debug("Job created {}".format(self._id))

    def _schedule_job(self):
        """launch the resolution of the job just created"""
        LOGGER.debug("Scheduling Solve Engine job...")

        resp = self._send("post", SEUrls.SCHEDULE_URL)
        
        solution = ObjResponse(resp, SERequests.SCHEDULE_JOB)
        if solution.unusual_answer:
            raise ValueError(solution.build_err_msg)

        LOGGER.debug("Job scheduled")

    def _wait_results(self):
        """asks for the status of the solving untill it finishes"""
        sec_cnt = 0
        while True:
            resp = self._send("get", SEUrls.STATUS_URL)

            solution = ObjResponse(resp, SERequests.GET_STATUS)
            if solution.unusual_answer:
                raise ValueError(solution.build_err_msg)
            se_status = solution.job_status
            
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
        """asks Solveengine the results of the problem"""
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
        """send an http request to solveengine"""
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
