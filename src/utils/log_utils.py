import logging
import inspect

from src.core.env import IS_LOCAL_ENV

def _get_caller_logger():
    # stack()[1] = safe_x
    # stack()[2] = the module that called safe_x
    caller_frame = inspect.stack()[2]
    module = inspect.getmodule(caller_frame[0])
    module_name = module.__name__ if module else "unknown"
    # use __name__ to get a logger named after the module we're calling safe_x in.
    # This will tell us the name of the file that produced messages in logs. We can enable or
    # disable them per module, filter logs by module name, and have more control over our
    # log information.
    return logging.getLogger(module_name)


def safe_debug(message: str):
    """
        Debug logs that should only appear in development (locally).
        Prevents leaking sensitive data in production.
    """
    if IS_LOCAL_ENV:
        logger = _get_caller_logger()
        logger.debug(message)


def safe_info(message: str):
    """
        Info logs that are safe for all environments.
    """
    logger = _get_caller_logger()
    logger.info(message)


def safe_warning(message: str):
    """
        Warning logs that are safe for all environments.
    """
    logger = _get_caller_logger()
    logger.warning(message)


def safe_error(message: str):
    logger = _get_caller_logger()
    logger.error(message)


def safe_exception(message: str, exc_info = None):
    logger = _get_caller_logger()
    logger.exception(message, exc_info = exc_info)
