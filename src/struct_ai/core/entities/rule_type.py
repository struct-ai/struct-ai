from enum import Enum


class RuleType(str, Enum):
    """
    Define the principal of clean architecture tracking by  Struct AI.
    """

    DEPENDENCY_INVERSION = "dependency_inversion"
    SINGLE_RESPONSIBILITY = "srp"
    IMMUTABILITY = "immutability"
    LAYER_VIOLATION = "layer_violation"
    MODULARITY = "modularity"
