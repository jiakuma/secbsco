def success(data=None, message: str = "success"):
    return {
        "code": 0,
        "message": message,
        "data": data,
    }


def fail(message: str = "failed", code: int = 1, data=None):
    return {
        "code": code,
        "message": message,
        "data": data,
    }
