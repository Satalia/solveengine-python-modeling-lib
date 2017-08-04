# -*- coding: utf-8 -*-
"""Solve Engine Helpers
"""
from enum import Enum
import logging

LOGGER_NAME = "satalia_solve_engine_logger"

class SERequests(Enum):
    """enum to determinate the kind of request that has been sent,
    used to analyse the result from a request
    """
    GET_JOBS = 1
    CREATE_JOB = 2
    SCHEDULE_JOB = 3
    GET_STATUS = 4
    GET_RESULT = 5

def _get_logger():
    return logging.getLogger(LOGGER_NAME)

class StrEnum(Enum):
    """An enum which allows for comparison with a string"""
    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        return self.value == other.value

    def __str__(self):
        return self.value

    @classmethod
    def get_values(cls):
        """returns a list of all enum elements as strings"""
        values = []
        for var_name in dir(cls):
            if var_name[0] != "_":
                values.append(str(getattr(cls, var_name)))
        return values

class ResponseJob():
    """class representing the data returned from a request
    concerning a job
    """
    def __init__(self, json_obj):
        self.status = json_obj['status']
        self.userId = json_obj['user_id']
        self.jobId= json_obj['id']
        self.algorithm = json_obj['algorithm']
        self.submitted = json_obj['submitted']
        self.started = json_obj.get('started', 'did not start')
        self.finish = json_obj['finished']
        self.fileName = json_obj['filenames']
        self.usedTime = json_obj['used_time']

class Variable():
    """ class representing a variable 
    in the sens of what is returned from a request
    """
    def __init__(self, name, value):
        self.name = name
        self.value = value

class ObjResponse():
    """class created to test and gether the data returned by the http request
    depending on the type of request sent
    """
    def __init__(self, json_obj, resp_type):
        try:
            if resp_type == SERequests.GET_JOBS:
                self.jobs = []
                for dct_job in json_obj['jobs']:
                    new_job = ResponseJob(dct_job)
                    self.jobs.append(new_job)

                self.total_jobs = json_obj['total']

            elif resp_type == SERequests.CREATE_JOB:
                self.job_id = json_obj['id']

            elif resp_type == SERequests.SCHEDULE_JOB:
                if len(json_obj.keys()) == 0:
                    pass

            elif resp_type == SERequests.GET_STATUS:
                self.job_status = json_obj['status']

            elif resp_type == SERequests.GET_RESULT:
                self.variables = []
                self.job_id = json_obj['job_id'] 
                dct_result = json_obj['result']

                self.status = dct_result['status']
                self.objective_value = dct_result.get('objective_value', 'no objective value')
                lst_dct_vars = dct_result.get('variables', [])

                for dct_var in lst_dct_vars:
                    self.variables.append(Variable(dct_var['name'], dct_var['value']))
                    
            self.unusual_answer = False
            
        except:
            self.unusual_answer = True
            self.code = json_obj['code']
            self.message = json_obj['message']

    def build_err_msg(self):
        return "Error type : " + str(self.code) + "\nMessage returned by the server : " + self.message

def unusual_answer(resp_obj, resp_type):
    """tests the values the object from grpc requests should return
    
    returns True if one field is missing
    """
    try:
        if resp_type == SERequests.GET_JOBS:
            temp = resp_obj.jobs                
            temp = resp_obj.total

        elif resp_type == SERequests.CREATE_JOB:
            temp = resp_obj.id

        elif resp_type == SERequests.GET_STATUS:
            temp = resp_obj.status

        elif resp_type == SERequests.GET_RESULT:
            temp = resp_obj.job_id
            temp = resp_obj.result.status

        return False     
    except:
        return True

def build_err_msg(resp_obj):
    """returns an error message with what is written in 
    the error message returned by solve engine
    """
    return "Error type : " + str(resp_obj.code) + "\nMessage returned by the server : " + resp_obj.message
    
def check_complete_list(list_, nbMax, defValue):
    """make sure the list is long enough
    
    complete with default value if not
    
    return False if the list is too long
    """
    
    if len(list_) <= nbMax: 
        list_.extend([defValue] * (nbMax - len(list_)))
        return True
    else:
        return False