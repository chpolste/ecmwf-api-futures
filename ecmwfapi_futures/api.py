import warnings
import datetime as dt
from concurrent import futures

from ecmwfapi import api



_MAX_REQUEST_WARNING = (
            "No more than 3 (20) requests per user can be active (queued) at a time. "
            "See: https://confluence.ecmwf.int/display/UDOC/Total+number+of+requests+a+user+can+submit+-+Web+API+FAQ"
            )


class ECMWFDataServer:
    """A future-based replacement for `ecmwfapi.ECMWFDataServer`
    
    A wrapper around `concurrent.futures.ThreadPoolExecutor` that implements
    the `retrieve` method of `ecmwfapi.ECMWFDataServer`.

    Can be used as a context manager that cleans up threads without having to
    call `ECMWFDataServer.shutdown()` explicitly.
    """

    def __init__(self, url=None, key=None, email=None, max_workers=1, defaults=None):
        """Start a thread pool for request submission to the ECMWF server
        
        `max_workers` specifies how many requests can be executed concurrently.
        
        `defaults` can be set to a request template that provides non-changing
        fields for every request submitted with `ECMWFDataServer.retrieve()`.

        If `url`, `key` and `email` are not specified the API authentication
        information is read from the environment.
        """
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
        """Submit a request to the ECMWF server and return a future that tracks its progess"""
        request_dct = self.defaults.copy()
        if request is not None:
            request_dct.update(request)
        # Unify handling of service argument for ECMWFDataServer and
        # ECMWFService by allowing a service field in requests analogous to the
        # dataset field.
        service = None
        assert not ("dataset" in request_dct and "service" in request_dct)
        if "dataset" in request_dct:
            service = "datasets/{}".format(request_dct["dataset"])
        if "service" in request_dct:
            service = "services/{}".format(request_dct["service"])
        if service is None:
            raise ValueError("dataset or service must be specified in the request")
        # Submit request, return associated future
        return APIRequestFuture(self, service, request_dct, status_callback=status_callback)



class ECMWFService(ECMWFDataServer):
    """A future-based replacement for `ecmwfapi.ECMWFService`

    Implements the `execute` method of `ecmwfapi.ECMWFService` in terms of
    `ECMWFDataServer.request`. See `ECMWFDataServer` for more information.
    """

    def __init__(self, service, url=None, key=None, email=None, max_workers=1, defaults=None):
        """See `ECMWFDataServer.__init__`"""
        super().__init__(url, key, email, max_workers, defaults)
        self.defaults["service"] = service

    def execute(self, request=None, target=None, status_callback=None):
        """Submit a request to the ECMWF server and return a future that tracks its progess"""
        request = dict() if request is None else request.copy()
        if target is not None:
            request["target"] = target
        return self.retrieve(request=request, status_callback=status_callback)



class APIRequestFuture:
    """Combines `concurrent.futures.Future` and `ecmwfapi.APIRequest`
    
    APIRequestFuture instances are created by `ECMWFDataServer.retrieve()` and
    should not be created directly.
    """
    
    def __init__(self, pool, service, request, status_callback=None):
        self.messages = []
        self.request = request
        self._status = "waiting"
        self.id = None
        # Pop target from the request dict, the server should not care about
        # local path issues
        self.target = request.pop("target")
        # ecmwfapi.APIRequest result fields
        self.href = None
        self.size = None
        self.type = None
        # Keep track of elapsed time
        self.start_time = dt.datetime.utcnow()
        self.end_time = None
        # Status change callbacks
        self._status_callbacks = []
        if status_callback is not None:
            self.add_status_callback(status_callback)
        # Instanciate and execute ecmwfapi.APIRequest object in separate
        # thread. Both communicate with the ECMWF server and are blocking.
        def execute():
            # Suppress any calls to print in ecmwfapi by setting quiet=True and
            # verbose=False. Other messages are passed to self._recv.
            apireq = api.APIRequest(url=pool.url, service=service, email=pool.email, key=pool.key,
                    log=self._recv, quiet=True, verbose=False, news=True)
            try:
                return apireq.execute(request, self.target)
            # HTTP Errors are communicated as APIExeceptions. The actual HTTP
            # error message must be recovered from the request's connection.
            except api.APIException as e:
                conn = apireq.connection
                if hasattr(conn, "last") and "error" in conn.last and "messages" in conn.last:
                    e.value += "\n".join(conn.last["messages"])
                raise
        self._future = pool._submit(execute)
        # Add a callback that processes the results of the API request
        self._future.add_done_callback(self._callback)

    def __repr__(self):
        elapsed_min = self.elapsed / dt.timedelta(minutes=1)
        return "<APIRequestFuture id={} status={} elapsed={:.2f}min target={}>".format(self.id, self.status, elapsed_min, self.target)

    @property
    def elapsed(self):
        """Time elapsed since instantiation of the future"""
        end = dt.datetime.utcnow() if self.end_time is None else self.end_time
        return end - self.start_time

    @property
    def status(self):
        """Current status of the request

        Status          Meaning
        ---------------------------------------------------------------
        "waiting"       The future has not yet been scheduled by the
                        ECMWFDataServer thread pool.
        "submitted"     The request has been submitted to the server.
        "queued"        The request has been queued by the server.
        "active"        The request is active on the server.
        "complete"      Data has been downloaded, the request is finished.
        "cancelled"     The future was cancelled.
        "error"         An error occurred while running the future.
        """
        return self._status

    @status.setter
    def status(self, status):
        self._status = status
        for callback in self._status_callbacks:
            callback(self)

    def add_status_callback(self, fn):
        """Attach the callable `fn` as a status change event handler.
        
        `fn` will be called with the future as its only argument when the
        status of the future changes. Attached callbacks are called in the
        order that they were attached.
        """
        if not callable(fn):
            raise TypeError("Argument is not callable")
        self._status_callbacks.append(fn)

    def _recv(self, msg):
        """Process log messages from the `ecmwfapi.RequestAPI` object"""
        # Synchronize the status with that of the request on the server
        if msg.startswith("Request is "):
            self.status = msg[11:].strip()
        # Obtain the request id assigned by the server
        if msg.startswith("Request id: "):
            self.id = msg[12:].strip()
        # Log all messages
        self.messages.append(msg)

    def _callback(self, future):
        """Update fields when the wrapped future completes"""
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

    def cancel(self):
        """See `concurrent.futures.Future.cancel`
        
        Cancels the local future, not the request on the ECMWF server.
        """
        return self._future.cancel()

    def cancelled(self):
        """See `concurrent.futures.Future.cancelled`"""
        return self._future.cancelled()

    def running(self):
        """See `concurrent.futures.Future.running`"""
        return self._future._running()

    def done(self):
        """See `concurrent.futures.Future.done`"""
        return self._future.done()

    def result(self, timeout=None):
        """See `concurrent.futures.Future.result`"""
        return self._future.result(timeout=timeout)

    def exception(self, timeout=None):
        """See `concurrent.futures.Future.exception`"""
        return self._future.exception(timeout=timeout)



def wait(fs, *args, **kwargs):
    """Like `concurrent.futures.wait` but for `APIRequestFuture`"""
    fs_map = { f._future: f for f in fs }
    done, not_done = futures.wait(fs_map.keys(), *args, **kwargs)
    return { fs_map[f] for f in done }, { fs_map[f] for f in not_done }


def as_completed(fs, *args, **kwargs):
    """Like `concurrent.futures.as_completed` but for `APIRequestFuture`"""
    fs_map = { f._future: f for f in fs }
    for f in futures.as_completed(fs_map.keys()):
        yield fs_map[f]

