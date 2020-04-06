"""A parallel version of the mars script

Original mars script available at
https://confluence.ecmwf.int//download/attachments/56664858/mars
"""

import argparse
import os
from time import sleep
from . import api


def print_status(future):
    print("Request for target '{}' changed status to {}".format(future.target, future.status))


parser = argparse.ArgumentParser(prog="python -m ecmwfapi_futures", description="""
    Submit multiple MARS requests concurrently.
""")
parser.add_argument("--no-logs", action="store_true", help="disable writing of log files")
parser.add_argument("--service", default="mars", help="which service to use (default 'mars')")
parser.add_argument("--workers", default=3, type=int, help="how many workers that submit requests (default 3)")
parser.add_argument("infiles", nargs="+", help="input files, each containing one MARS request")


if __name__ == "__main__":

    args = parser.parse_args()

    service = args.service.strip()
    write_logs = not args.no_logs
    max_workers = args.max_workers

    requests = []
    for infile in args.infiles:
        assert os.path.exists(infile), "file '{}' does not exist".format(infile)
        with open(infile, "r") as f:
            requests.append(f.read())

    server = api.ECMWFDataServer(max_workers=max_workers, write_logs=write_logs)

    def submit(request):
        sleep(1) # Wait a second between requests
        return server.mars(service, request, status_callback=print_status)

    wait_all([submit(request) for request in requests])

