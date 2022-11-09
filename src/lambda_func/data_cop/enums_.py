"""
Module that contains a record of enums for
the entire project.
"""
from enum import Enum


class DataCopEnum(Enum):
    """
    Contains a list of enums that are related to DataCop.
    These enums will be used by the event parser to determine
    the type of state machine that the event must be passed to.
    """

    DEFAULT = 0
    FSS = 1
    MACIE = 2
