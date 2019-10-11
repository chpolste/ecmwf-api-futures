# ecmwf-api-futures

A future-based interface to [ecmwf-api-client](https://github.com/ecmwf/ecmwf-api-client).

Provides a drop-in replacement for `ECMWFDataServer` that executes requests in separate threads without blocking and less printing to stdout.
A future is returned for every request that tracks its status on the server.
This allows better error handling and concurrent submission of requests (but be aware of [request limits](https://confluence.ecmwf.int/display/UDOC/Total+number+of+requests+a+user+can+submit+-+Web+API+FAQ)).


## Dependencies

- `ecmwf-api-client`, set up according to [its documentation](https://github.com/ecmwf/ecmwf-api-client#configure)
- `concurrent.futures`, i.e. Python 3.2 or newer

