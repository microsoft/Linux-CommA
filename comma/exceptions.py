# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Custom exception types
"""


class CommaError(Exception):
    """Comma parent exception class"""


class CommaDatabaseError(CommaError):
    """Errors establishing database connections"""


class CommaDataError(CommaError):
    """Errors with input or stored data"""


class CommaSpreadsheetError(CommaError):
    """Errors with spreadsheet operations"""


class CommaPluginError(CommaError):
    """Errors due to plugins"""
