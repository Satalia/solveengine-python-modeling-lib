# -*- coding: utf-8 -*-
"""Module for testing the Solver-Engine base class
"""

# pylint: disable=R0201, C0103, W0612, C0111, protected-access


import json
import pytest
import httpretty
from pysolveengine.basemodel import SEStatusCode, BaseModel, SolverStatusCode


class TestBaseModel:
    @httpretty.activate
    def test_get_job_id(self):
        httpretty.register_uri(httpretty.POST, BaseModel.BASEURL,
                               body='{"job_id": "123"}', content_type='text/json')
        assert BaseModel(token="abc", filename="a", file_ending=".lp")._get_job_id() == "123"
        assert httpretty.last_request().headers["authorization"] == "Bearer abc"
        x = json.loads(httpretty.last_request().body.decode())
        assert x == {"options": {}, "files": [{"name": "a.lp"}]}

    @httpretty.activate
    def test_bearer(self):
        httpretty.register_uri(httpretty.GET, BaseModel.BASEURL, body="abc")
        BaseModel(token="123")._send("get", with_jobid=False)
        assert httpretty.last_request().headers["authorization"] == "Bearer 123"

    def test_status(self):
        m = BaseModel("a")
        assert m.se_status == SEStatusCode.NOTSTARTED
        assert m.solver_status == SolverStatusCode.NOTSTARTED


    def test_filename(self):
        with pytest.raises(ValueError):
            BaseModel(token="", filename="abc", file_ending=".tt")

        with pytest.raises(ValueError):
            BaseModel(token="", filename="abc", file_ending="lp")

        model = BaseModel(token="", filename="test", file_ending=".lp")
        assert model._filename == "test.lp"
        model = BaseModel(token="", filename="test", file_ending=".cnf")
        assert model._filename == "test.cnf"
