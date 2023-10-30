import argparse, logging, socket, sys, time, os


def setup_logging(verbose):
    """
    Sets up the logging based on verbosity level.

    @param verbose: Whether to enable verbose logging.
    @return: None
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(format="%(levelname)s:%(message)s", level=level)


def send_response(conn, file_path, header, root_folder):
    """
    Sends server response to the client.

    @param conn: The client connection socket.
    @param file_path: The path to the file to be sent.
    @param header: The HTTP header for the response.
    @param root_folder: The root folder for server files.
    @return: None
    """
    send_num = 0
    full_path = root_folder + file_path
    try:
        file_size = os.path.getsize(full_path)
    except FileNotFoundError:
        file_size = os.path.getsize(root_folder + "/404.html")
        full_path = root_folder + "/404.html"
    response_header = header + f"Content-Length: {file_size}\r\n\r\n"
    conn.sendall(response_header.encode())

    with open(full_path, "rb") as f:
        while True:
            file_content = f.read(1024)
            if not file_content:
                break
            conn.sendall(file_content)
            send_num += 1
            logging.info(f"Send {send_num}")


def get_header(code):
    """
    Gets the response header based on HTTP response code.

    @param code: The HTTP response code.
    @return: The response header as a string.
    """
    if code == 200:
        return "HTTP/1.1 200 OK\r\n"
    elif code == 404:
        return "HTTP/1.1 404 Not Found\r\n"
    else:
        return "HTTP/1.1 405 Method Not Allowed \r\n"


def is_request_file_exist(request_file, root_folder):
    """
    Checks if a requested file exists.

    @param request_file: The path to the requested file.
    @param root_folder: The root folder for server files.
    @return: True if the file exists, False otherwise.
    """
    return os.path.isfile(root_folder + request_file)


def process_request(conn, request, root_folder):
    """
    Processes the client request and sends the appropriate response.

    @param conn: The client connection socket.
    @param request: The client HTTP request as a string.
    @param root_folder: The root folder for server files.
    @return: None
    """
    beg_line = request.split("\r\n")[0]
    info = beg_line.split(" ")
    method = info[0]
    request_file = info[1]

    if method != "GET":
        send_response(conn, None, get_header(405), root_folder)
        return

    if request_file == "/":
        send_response(conn, "/page.html", get_header(200), root_folder)
        return

    if not is_request_file_exist(request_file, root_folder):
        send_response(conn, "/404.html", get_header(404), root_folder)
        return

    send_response(conn, request_file, get_header(200), root_folder)


def run(port, root_folder, delay):
    """
    Runs the HTTP server and listens for incoming client requests.

    @param port: The port number to listen on.
    @param root_folder: The root folder for server files.
    @param delay: Whether to introduce a delay before processing requests (for debugging).
    @return: None
    """
    server_socket = socket.socket()
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("", port))
    server_socket.listen()
    logging.info(f"Listening on port {port}")

    try:
        while True:
            conn, address = server_socket.accept()
            logging.info(f"Connection from: {address}")

            if delay:
                time.sleep(5)

            data_buffer = bytearray()
            while True:
                chunk = conn.recv(1024)
                if not chunk:
                    break
                data_buffer.extend(chunk)

                data_str = data_buffer.decode()

                if "\r\n\r\n" in data_str:
                    process_request(conn, data_str, root_folder)
                    break

            conn.close()
            logging.info(f"Connection closed")
    except KeyboardInterrupt:  # Ctrl-C
        print("Shutting down server")
        sys.exit(0)


if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description="Simple HTTP Server")
    parser.add_argument(
        "-p", "--port", required=False, type=int, default=8084, help="port to bind to"
    )
    parser.add_argument(
        "-v", "--verbose", required=False, action="store_true", help="turn on debugging output"
    )
    parser.add_argument(
        "-d", "--delay", required=False, action="store_true", help="add a delay for debugging purposes"
    )
    parser.add_argument(
        "-f", "--folder", required=False, default=".", help="folder from where to serve from"
    )
    args = parser.parse_args()

    # Log and setup logging
    setup_logging(args.verbose)
    logging.debug(args)

    # Ensure the root folder ends with a '/'
    if args.folder[-1] != "/":
        args.folder += "/"

    # Run the code
    run(args.port, args.folder, args.delay)
