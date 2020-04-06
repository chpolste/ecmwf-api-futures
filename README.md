# ecmwf-api-futures

A future-based interface to [ecmwf-api-client](https://github.com/ecmwf/ecmwf-api-client).

Provides replacements for `ECMWFDataServer` and `ECMWFService` that execute requests in separate threads without blocking and less printing to stdout.
A future is returned for every request that tracks its status on the server.
This allows better error handling and concurrent submission of requests (but be aware of [request limits](https://confluence.ecmwf.int/display/UDOC/Total+number+of+requests+a+user+can+submit+-+Web+API+FAQ)).

This is not official software from the ECMWF and the author of this software is not affiliated with the ECMWF.


## Features

The methods `ECMWFServerData.retrieve` and `ECMWFService.execute` are replacements for the corresponding methods of [ecmwf-api-client](https://github.com/ecmwf/ecmwf-api-client). Features that are specific to ecmwf-api-futures:

- Every request immediately returns a future, which tracks the progress of the request.
- Multiple requests can be submitted.
  The `ECMWFDataServer` will send at most `max_workers` requests to the server at once.
  If more requests are submitted locally, they will wait until a worker has finished with a previous request.
- A default set of parameters can be specified that forms the basis of all subsequent requests (see example below).
- By default log files are written for every request submitted (this can be disabled).

Both `ECMWFServerData` and `ECMWFService` implement the `Executor` interface of [concurrent.futures](https://docs.python.org/3/library/concurrent.futures.html#executor-objects).
Compatible replacements for the functions `wait` and `as_completed` of that module are available too.

If the module is run as

    python -m ecmwfapi_futures ...

it acts as a parallel implementation of the [mars](https://confluence.ecmwf.int//download/attachments/56664858/mars) script, accepting multiple input files containing one MARS request each.

Please consult the docstrings and source code to obtain more information.


## Example

Adapted from the test script of [ecmwf-api-client](https://github.com/ecmwf/ecmwf-api-client#test).

```python
import ecmwfapi_futures as api

# Specify default parameters that are reused for all requests
server = api.ECMWFDataServer(max_workers=2, defaults={
    'origin'    : "ecmf",
    'levtype'   : "sfc",
    'number'    : "1",
    'expver'    : "prod",
    'dataset'   : "tigge",
    'step'      : "0/6/12/18",
    'area'      : "70/-130/30/-60",
    'grid'      : "2/2",
    'param'     : "167",
    'time'      : "00/12",
    'type'      : "pf",
    'class'     : "ti"
})

# Retrieve two days of forecasts
req1 = server.retrieve({
    'date'      : "2014-11-01",
    'target'    : "tigge_2014-11-01_0012.grib"
})
req2 = server.retrieve({
    'date'      : "2014-11-02",
    'target'    : "tigge_2014-11-02_0012.grib"
})

api.wait([req1, req2])
```


## Dependencies

- `ecmwf-api-client`, set up according to [its documentation](https://github.com/ecmwf/ecmwf-api-client#configure)
- `concurrent.futures`, i.e. Python 3.2 or newer


## Installation

To install as a package, run

    pip install .

from the root of the repository.


## License

Copyright 2019-2020 Christopher Polster

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

