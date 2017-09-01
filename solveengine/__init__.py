# -*- coding: utf-8 -*-
"""__init__ for the SolveEngine
"""

def _create_logger():
    import logging
    from .helper import LOGGER_NAME
    logger = logging.getLogger(LOGGER_NAME)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)s = %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
_create_logger()

from .mipmodel import MIPModel, INF, Direction
from .satmodel import SATModel
from .config import SEStatusCode, SolverStatusCode, help_sat, help_mip

