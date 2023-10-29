import logging, random, socket, argparse, struct, sys


def randomize_text(text):
    """
    Randomize text by repeating characters and discarding some of them.

    :param text: The input text to be randomized.
    :return: A randomized version of the input text.
    """

    def discard():
        return random.choices([True, False], weights=[1, 5])[0]

    def repeat(char):
        should_repeat = random.choices([True, False], weights=[1, 5])[0]
        return char * (int(random.paretovariate(1)) if should_repeat else 1)

    transformed_text = [repeat(c) for c in text if not discard()]
    return "".join(transformed_text) if transformed_text else text[0]


def parse_header(header):
    """
    Parse the binary header to extract action and message length.

    :param header: The binary header to be parsed.
    :return: A tuple containing the action and message length.
    """
    # Variables for decoding header
    binary_header = format(header, "032b")
    action_code = int(binary_header[:5], 2)
    message_length = int(binary_header[5:], 2)

    # Log
    logging.debug(
        f"Header: {header}, Binary Header: {binary_header}, actionCode: {action_code}, Message Length: {message_length}"
    )

    # Define and return actions and info
    actions = {1: "uppercase", 2: "lowercase", 4: "reverse", 8: "shuffle", 16: "random"}
    return actions.get(action_code, "error"), message_length


def process_data(action, data):
    """
    Process the data based on the given action.

    :param action: The action to be applied to the data.
    :param data: The input data to be processed.
    :return: The processed data based on the specified action.
    """
    if action == "uppercase":
        return data.upper()
    elif action == "lowercase":
        return data.lower()
    elif action == "reverse":
        return data[::-1]
    elif action == "shuffle":
        return "".join(random.sample(data, len(data)))
    elif action == "random":
        return randomize_text(data)
    else:
        return "error"


def run(port):
    """
    Run the server.

    :param port: The port number on which the server listens.
    :return: None
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

            data_buffer = bytearray()
            while True:
                chunk = conn.recv(1024)
                if not chunk:
                    break
                data_buffer.extend(chunk)

                while len(data_buffer) >= 4:
                    header = struct.unpack("!I", data_buffer[:4])[0]
                    action, msg_len = parse_header(header)

                    if len(data_buffer) < 4 + msg_len:
                        break

                    message = data_buffer[4 : 4 + msg_len].decode("utf-8", "ignore")
                    logging.info(f"Received: {message}")
                    response = process_data(action, message)
                    conn.send(struct.pack("!I", len(response)) + response.encode())

                    data_buffer = data_buffer[4 + msg_len :]

            conn.close()
            logging.info(f"Connection closed")
    except KeyboardInterrupt:  # Ctrl-C
        print("Shutting down server")
        sys.exit(0)


def setup_logging(verbose):
    """
    Set up logging based on verbosity.

    :param verbose: A boolean indicating whether to enable verbose logging.
    :return: None
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(format="%(levelname)s:%(message)s", level=level)


if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p", "--port", required=False, type=int, default=8083, help="port to bind to"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        required=False,
        action="store_true",
        help="turn on debugging output",
    )
    args = parser.parse_args()

    # Log and setup logging
    setup_logging(args.verbose)
    logging.debug(args)

    # Run the code
    run(args.port)
