# -*- coding: utf-8 -*-
"""
Module for testing the Solver-Engine interface
"""

# pylint: disable=R0201, C0103, W0612, C0111, protected-access

import pytest
from pysolveengine.helper import StrEnum

class ETest(StrEnum):
    A="a"
    B="b"

class TestStrEnum:
    def test_getValues(self):
        assert set(ETest.get_values()) == set(["a", "b"])

