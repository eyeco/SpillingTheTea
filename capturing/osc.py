# osc.py

import utils

from pythonosc import osc_server

startCommand = "/start"
stopCommand = "/stop"
markerCommand = "/marker"

port = 6669

import sys
import traceback
class SafeThreadingOSCServer(osc_server.ThreadingOSCUDPServer):
    def handle_error(self, request, client_address):
        exc_type, exc_value, exc_traceback = sys.exc_info()

        utils.error(f"error while processing OSC data:\n\t{exc_type.__name__ if exc_type else 'Unknown'}\n\tError Message: {exc_value}")

        # utils.error(f"OSC: Caught an issue from {client_address}:\nError Type:    {exc_type.__name__ if exc_type else 'Unknown'}\nError Message: {exc_value}")

        # # 2. OPTIONAL: If it's a completely unexpected error (not the regular expression TypeError),
        # # print the mini stack trace so you can debug your handler functions!
        # if exc_type is not TypeError:
        #     utils.warn("OSC: Unexpected error detected! Printing shorthand stack trace:")
        #     # Prints just the last 2 frames of the track so your console stays tidy
        #     traceback.print_exception(exc_type, exc_value, exc_traceback, limit=2)
        # else:
        #     utils.warn("suppressed expected trailing-byte Type-Mismatch error.")

        pass