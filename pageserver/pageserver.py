"""
  A trivial web server in Python.

  Based largely on https://docs.python.org/3.4/howto/sockets.html
  This trivial implementation is not robust:  We have omitted decent
  error handling and many other things to keep the illustration as simple
  as possible.

  FIXME:
  Currently this program always serves an ascii graphic of a cat.
  Change it to serve files if they end with .html or .css, and are
  located in ./pages  (where '.' is the directory from which this
  program is run).
"""

import config    # Configure from .ini files and command line
import logging   # Better than print statements
logging.basicConfig(format='%(levelname)s:%(message)s',
                    level=logging.INFO)
log = logging.getLogger(__name__)
# Logging level may be overridden by configuration 

import os        # Building and checking file paths
import socket    # Basic TCP/IP communication on the internet
import _thread   # Response computation runs concurrently with main program
DOCROOT = "./pages" #overridden by configuration in main()

def listen(portnum):
    """
    Create and listen to a server socket.
    Args:
       portnum: Integer in range 1024-65535; temporary use ports
           should be in range 49152-65535.
    Returns:
       A server socket, unless connection fails (e.g., because
       the port is already in use).
    """
    # Internet, streaming socket
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Bind to port and make accessible from anywhere that has our IP address
    serversocket.bind(('', portnum))
    serversocket.listen(1)    # A real server would have multiple listeners
    return serversocket


def serve(sock, func):
    """
    Respond to connections on sock.
    Args:
       sock:  A server socket, already listening on some port.
       func:  a function that takes a client socket and does something with it
    Returns: nothing
    Effects:
        For each connection, func is called on a client socket connected
        to the connected client, running concurrently in its own thread.
    """
    while True:
        log.info("Attempting to accept a connection on {}".format(sock))
        (clientsocket, address) = sock.accept()
        _thread.start_new_thread(func, (clientsocket,))


##
# Starter version only serves cat pictures. In fact, only a
# particular cat picture.  This one.
##
CAT = """
     ^ ^
   =(   )=
"""

# HTTP response codes, as the strings we will actually send.
# See:  https://en.wikipedia.org/wiki/List_of_HTTP_status_codes
# or    http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html
##
STATUS_OK = "HTTP/1.0 200 OK\n"
STATUS_FORBIDDEN = "HTTP/1.0 403 Forbidden\n\n"
STATUS_NOT_FOUND = "HTTP/1.0 404 Not Found\n\n"
STATUS_NOT_IMPLEMENTED = "HTTP/1.0 401 Not Implemented\n\n"
STATUS_SERVER_ERROR = "HTTP/1.0 500 Internal Server Error\n\n"

#content types for the files we serve
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
}


def respond(sock):
    """
    This server responds only to GET requests (not PUT, POST, or UPDATE).
    Any valid GET request is answered with an ascii graphic of a cat.
    """
    request = sock.recv(1024)  # We accept only short requests
    request = str(request, encoding='utf-8', errors='strict')
    log.info("--- Received request ----")
    log.info("Request was {}\n***\n".format(request))

    parts = request.split()
    try:
        if len(parts) > 1 and parts[0] == "GET":
            serve_path(parts[1], sock)
        else:
            log.info("Unhandled request: {}".format(request))
            transmit(STATUS_NOT_IMPLEMENTED, sock)
            transmit("\nI don't handle this request: {}\n".format(request), sock)
    except Exception:
        #if theres a but this will log it, and tell the client instead of hanging
        log.exception("Error while handling request")
        transmit(STATUS_SERVER_ERROR, sock)
    finally:
        #always close the connection, even after an error
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()

def serve_path(path, sock):
    #sends the file named by path or a 403 / 404 error status if we can't or won't
    
    #ignores any query string
    path = path.split("?")[0]
    log.info("Requested path: {}".format(path))
 
    #responds to forbidden symbols with 403
    if "~" in path or "//" in path or ".." in path:
        transmit(STATUS_FORBIDDEN, sock)
        transmit("403 Forbidden: {}\n".format(path), sock)
        return
 
    #only serves .html and .css files, otherwise 403
    extension = os.path.splitext(path)[1]
    if extension not in CONTENT_TYPES:
        transmit(STATUS_FORBIDDEN, sock)
        transmit("403 Forbidden: only .html and .css files are served\n", sock)
        return
 
    #if the file doesn't exist under DOCROOT, respond with 404
    file_path = os.path.join(DOCROOT, path.lstrip("/"))
    if not os.path.isfile(file_path):
        transmit(STATUS_NOT_FOUND, sock)
        transmit("404 Not Found: {}\n".format(path), sock)
        return
 
    #otherwise send the file
    with open(file_path, "r", encoding="utf-8") as source:
        content = source.read()
    transmit(STATUS_OK, sock)
    transmit("Content-Type: {}\n\n".format(CONTENT_TYPES[extension]), sock)
    transmit(content, sock)

def transmit(msg, sock):
    """It might take several sends to get the whole message out"""
    buff = bytes(msg, encoding="utf-8")
    sent = 0
    while sent < len(buff):
        sent += sock.send(buff[sent:])

###
#
# Run from command line
#
###


def get_options():
    """
    Options from command line or configuration file.
    Returns namespace object with option value for port
    """
    # Defaults from configuration files;
    #   on conflict, the last value read has precedence
    options = config.configuration()
    # We want: PORT, DOCROOT, possibly LOGGING

    if options.PORT <= 1000:
        log.warning(("Port {} selected. " +
                         " Ports 0..1000 are reserved \n" +
                         "by the operating system").format(options.port))

    return options


def main():
    global DOCROOT
    options = get_options()
    port = options.PORT
    if options.DEBUG:
        log.setLevel(logging.DEBUG)
    DOCROOT = options.DOCROOT
    log.info("Serving files from DOCROOT {}".format(DOCROOT))
    sock = listen(port)
    log.info("Listening on port {}".format(port))
    log.info("Socket is {}".format(sock))
    serve(sock, respond)


if __name__ == "__main__":
    main()
