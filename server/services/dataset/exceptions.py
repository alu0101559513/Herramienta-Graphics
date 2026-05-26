from __future__ import annotations


class DatasetFormatError(Exception):
    """
    Description:
        Raised when the uploaded dataset does not match a supported CSV format.
    """

    pass


class DatasetValidationError(Exception):
    """
    Description:
        Raised when a parsed dataset fails validation rules.
    """

    pass
