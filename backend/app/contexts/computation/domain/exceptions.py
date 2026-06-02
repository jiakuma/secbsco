from fastapi import HTTPException


class ComputationError(Exception):
    pass


class RuntimeNotReadyError(ComputationError):
    pass
