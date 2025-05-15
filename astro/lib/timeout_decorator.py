import signal
import timeout_decorator
import time

TIMEOUT = 10
_timeout_dict = {}

def set_timeout_contract(timeout_contract):
    _timeout_dict["TIMEOUT_CONTRACT"] = timeout_contract
    
def get_timeout_contract():
    try:
        return _timeout_dict["TIMEOUT_CONTRACT"]
    except:
        return ""

def set_timeout_dirpath(dirpath):
    _timeout_dict["TIMEOUT_DIRPATH"] = dirpath

def get_timeout_dirpath():
    try:
        return _timeout_dict["TIMEOUT_DIRPATH"]
    except:
        return ""


class TimeoutException(Exception):
    pass

def signal_handler(signum, frame):
    raise TimeoutException("TimeOut Error")

def timeout(seconds=5):
    def decorator(func):
        def wrapper(*args, **kwargs):
            def _handle_timeout(signum, frame):
                error_message = get_timeout_contract()
                error_message = error_message + get_timeout_dirpath()
                raise TimeoutError(error_message)

            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                raise e
            finally:
                signal.alarm(0)
            return result

        return wrapper
    return decorator


def my_function():
    # ...
    my_function2("hahah")

@timeout()
def my_function2(test):
    time.sleep(600)


if __name__ == "__main__":
    pass