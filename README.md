# ecmwf-api-futures

A future-based interface to [ecmwf-api-client](https://github.com/ecmwf/ecmwf-api-client).

Provides replacements for `ECMWFDataServer` and `ECMWFService` that execute requests in separate threads without blocking and less printing to stdout.
A future is returned for every request that tracks its status on the server.
This allows better error handling and concurrent submission of requests (but be aware of [request limits](https://confluence.ecmwf.int/display/UDOC/Total+number+of+requests+a+user+can+submit+-+Web+API+FAQ)).


## Dependencies

- `ecmwf-api-client`, set up according to [its documentation](https://github.com/ecmwf/ecmwf-api-client#configure)
- `concurrent.futures`, i.e. Python 3.2 or newer


## Installation

To install as a package, run

    pip install .

from the root of the repository.


## License

Copyright 2019 Christopher Polster

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
