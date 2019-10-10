"""A future-based interface to ecmwf-api-client"""

import warnings
import datetime as dt
from ecmwfapi import api
from concurrent import futures


__all__ = ("ECMWFDataServer", "wait", "as_completed")


_MAX_REQUEST_WARNING = (
            "No more than 3 (20) requests per user can be active (queued) at a time. "
            "See: https://confluence.ecmwf.int/display/UDOC/Total+number+of+requests+a+user+can+submit+-+Web+API+FAQ"
            )


class ECMWFDataServer(futures.Executor):

    def __init__(self, defaults=None, url=None, key=None, email=None, max_workers=1):
        self.defaults = dict() if defaults is None else defaults.copy()
        # Obtain authentication information from environment if not given
        if url is None or key is None or email is None:
            key, url, email = api.get_apikey_values()
        self.key = key
        self.url = url
        self.email = email
        # Warn user about request limits
        if max_workers > 3:
            warnings.warn(_MAX_REQUEST_WARNING, stacklevel=2)
        self._executor = futures.ThreadPoolExecutor(max_workers=max_workers)

    # Executor interface

    def __enter__(self, *args, **kwargs):
        return self._executor.__enter__(*args, **kwargs)

    def __exit__(self, *args, **kwargs):
        return self._executor.__exit__(*args, **kwargs)

    def _submit(self, fn, *args, **kwargs):
        return self._executor.submit(fn, *args, **kwargs)

    def shutdown(self, wait=True):
        self._executor.shutdown(wait)

    # ECMWFDataServer interface

    def retrieve(self, request=None, status_callback=None):
        request_dct = self.defaults.copy()
        request_dct.update(request)
        return APIRequestFuture(self, request_dct, status_callback=status_callback)


class APIRequestFuture:
    
    def __init__(self, pool, request, status_callback=None):
        self.messages = []
        self.request = request
        self._status = "waiting"
        self.id = None
        # ecmwfapi.APIRequest result fields
        self.href = None
        self.size = None
        self.type = None
        # Timing
        self.start_time = dt.datetime.utcnow()
        self.end_time = None
        # Status change callbacks
        self._status_callbacks = []
        if status_callback is not None:
            self.add_status_callback(status_callback)
        # Suppress any calls to print in ecmwfapi by setting quiet=True and
        # verbose=False. Other messages are passed to self._recv.
        service = "datasets/{}".format(request["dataset"])
        apireq = api.APIRequest(url=pool.url, service=service, email=pool.email, key=pool.key,
                log=self._recv, quiet=True, verbose=False, news=True)
        self._future = pool._submit(apireq.execute, request, request["target"])
        self._future.add_done_callback(self._callback)

    def __repr__(self):
        elapsed_min = self.elapsed / dt.timedelta(minutes=1)
        return "<APIRequestFuture id={} status={} elapsed={:.2f}min>".format(self.id, self.status, elapsed_min)

    @property
    def elapsed(self):
        end = dt.datetime.utcnow() if self.end_time is None else self.end_time
        return end - self.start_time

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        self._status = status
        for callback in self._status_callbacks:
            callback(self)

    def add_status_callback(self, fn):
        if not callable(fn):
            raise TypeError("Argument is not callable")
        self._status_callbacks.append(fn)

    def _recv(self, msg):
        if msg.startswith("Request is "):
            self.status = msg[11:].strip()
        if msg.startswith("Request id: "):
            self.id = msg[12:].strip()
        self.messages.append(msg)

    def _callback(self, future):
        self.end_time = dt.datetime.utcnow()
        if future.cancelled():
            self.status = "cancelled"
        elif future.exception() is not None:
            self.status = "error"
        else:
            result = future.result()
            self.href = result["href"] if "href" in result else None
            self.size = result["size"] if "size" in result else None
            self.type = result["type"] if "type" in result else None
            if "messages" in result:
                self.messages.append("=== REQUEST OUTPUT ===")
                self.messages.extend(result["messages"])

    # Future interface

    def cancel(self):
        return self._future.cancel()

    def cancelled(self):
        return self._future.cancelled()

    def running(self):
        return self._future._running()

    def done(self):
        return self._future.done()

    def result(self, timeout=None):
        return self._future.result(timeout=timeout)

    def exception(self, timeout=None):
        return self._future.exception(timeout=timeout)


def wait(fs, *args, **kwargs):
    fs_map = { f._future: f for f in fs }
    done, not_done = futures.wait(fs_map.keys(), *args, **kwargs)
    return { fs_map[f] for f in done }, { fs_map[f] for f in not_done }

def as_completed(fs, *args, **kwargs):
    fs_map = { f._future: f for f in fs }
    for f in futures.as_completed(fs_map.keys()):
        yield fs_map[f]
