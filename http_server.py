import argparse, logging, socket, sys, time, os


def send_response(connecting_socket, file_path, header, root_folder):
    """
    Sends server response to the client.

    @param connecting_socket: The client connection socket.
    @param file_path: The path to the file to be sent.
    @param header: The HTTP header for the response.
    @param root_folder: The root folder for server files.

    @return: None
    """

    # Try to get file size; if file not found, default to 404.html
    try:
        full_path = root_folder + file_path
        file_size = os.path.getsize(full_path)
    except FileNotFoundError:
        full_path = root_folder + "/404.html"
        file_size = os.path.getsize(full_path)

    # Build and send the response header
    response_header = header + f"Content-Length: {file_size}\r\n\r\n"
    connecting_socket.sendall(response_header.encode())

    # Send the content of the requested file in chunks
    with open(full_path, "rb") as f:
        send_num = 0
        file_content = f.read(1024)
        while file_content:
            connecting_socket.sendall(file_content)
            send_num += 1
            logging.info(f"Send {send_num}")
            file_content = f.read(1024)


def handle_post_request(connecting_socket, request, root_folder):
    """
    Handles the client PUSH request by writing the content to a file.

    @param connecting_socket: The client connection socket.
    @param request: The client HTTP request as a string.
    @param root_folder: The root folder for server files.

    @return: None
    """
    # Extract the file path and content from the request
    headers, content = request.split("\r\n\r\n", 1)
    file_path = headers.split(" ")[1]

    # Write the content to the file
    full_path = root_folder + file_path
    with open(full_path, "wb") as f:
        f.write(content.encode())

    # Send a 201 Created response to the client
    response_header = "HTTP/1.1 201 Created\r\n\r\n"
    connecting_socket.sendall(response_header.encode())


def process_request(connecting_socket, request, root_folder):
    """
    Processes the client request and sends the appropriate response.

    @param connecting_socket: The client connection socket.
    @param request: The client HTTP request as a string.
    @param root_folder: The root folder for server files.

    @return: None
    """

    # Extract the HTTP method and the requested file from the client's request
    line_beginning = request.split("\r\n")[0]
    info = line_beginning.split(" ")
    method, request_file = info[:2]

    # Handle POST request
    if method == "POST":
        handle_post_request(connecting_socket, request, root_folder)
        return

    # Determine the response code and file path based on the request
    code, file_path = (
        (405, None)
        if method != "GET"
        else (200, "/page.html")
        if request_file == "/"
        else (404, "/404.html")
        if not os.path.isfile(root_folder + request_file)
        else (200, request_file)
    )

    # Determine the appropriate response header based on the code
    header = (
        "HTTP/1.1 200 OK\r\n"
        if code == 200
        else "HTTP/1.1 404 Not Found\r\n"
        if code == 404
        else "HTTP/1.1 405 Method Not Allowed \r\n"
    )

    # Send the response to the client
    send_response(connecting_socket, file_path, header, root_folder)


def setup_server_socket(port):
    """
    Set up the HTTP server socket.

    @param port: The port number to listen on.

    @return: The server socket
    """

    # Set up the server socket and return it
    server_socket = socket.socket()
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("", port))
    server_socket.listen()

    logging.info(f"Listening on port {port}")

    return server_socket


def handle_client_request(conn, root_folder):
    """
    Handles the client request by reading incoming data and processing it.

    @param conn: The client connection socket.
    @param root_folder: The root folder for server files.

    @return: None
    """

    # Read and accumulate incoming data from the client
    try:
        data_buffer = bytearray()
        while True:
            chunk = conn.recv(1024)
            if not chunk:
                break
            data_buffer.extend(chunk)
            data_str = data_buffer.decode()

            if "\r\n\r\n" in data_str:
                process_request(conn, data_str, root_folder)
                # Clear the buffer for the next request
                data_buffer = bytearray()
    except Exception as e:
        logging.error(f"Error handling client request: {e}")


def run(port, root_folder, delay):
    """
    Runs the HTTP server and listens for incoming client requests.

    @param port: The port number to listen on.
    @param root_folder: The root folder for server files.
    @param delay: Whether to introduce a delay before processing requests (for debugging).

    @return: None
    """

    # Initialize the server socket
    server_socket = setup_server_socket(port)

    # Continuously listen for incoming requests
    try:
        while True:
            conn, address = server_socket.accept()
            logging.info(f"Connection from: {address}")

            # Introduce delay if the delay flag is set
            if delay:
                time.sleep(5)

            # Read and accumulate incoming data from the client
            handle_client_request(conn, root_folder)

            # Close the client connection after handling the request
            conn.close()
            logging.info(f"Connection closed")

    # Allow graceful shutdown on KeyboardInterrupt
    except KeyboardInterrupt:  # Ctrl-C
        print("Shutting down server")
        sys.exit(0)


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Simple HTTP Server")
    parser.add_argument(
        "-p", "--port", required=False, type=int, default=8084, help="port to bind to"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        required=False,
        action="store_true",
        help="turn on debugging output",
    )
    parser.add_argument(
        "-d",
        "--delay",
        required=False,
        action="store_true",
        help="add a delay for debugging purposes",
    )
    parser.add_argument(
        "-f",
        "--folder",
        required=False,
        default="www",
        help="folder from where to serve from",
    )
    args = parser.parse_args()

    # Setup logging based on verbosity
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(format="%(levelname)s:%(message)s", level=level)
    logging.debug(args)

    # Ensure root folder path is consistent
    if args.folder[-1] != "/":
        args.folder += "/"

    # Start the HTTP server
    run(args.port, args.folder, args.delay)
