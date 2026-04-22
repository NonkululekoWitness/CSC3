import socket
import threading
import json
from datetime import datetime
import os

BUFFER_SIZE = 4096
MAX_HEADER_LEN = 10000


class Peer:
    def __init__(self, username: str, port: int):
        self.username = username
        self.port = port
        self.running = True
        self.msg_counter = 0
        self.peers = {}

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(("0.0.0.0", port))
        self.server.listen()

        print(f"[{self.username}] listening on port {port}")

        threading.Thread(
            target=self.listen_for_connections,
            daemon=True
        ).start()

    def create_header(self, msg_type, recipient=None, body_length=0,
                     filename=None, filesize=None):
        header = {
            "type": msg_type,
            "sender": self.username,
            "recipient": recipient,
            "timestamp": datetime.now().isoformat(),
            "seq": self.msg_counter,
            "length": body_length
        }

        if filename:
            header["filename"] = filename
        if filesize:
            header["filesize"] = filesize

        self.msg_counter += 1
        return json.dumps(header) + "\n"

    def read_header(self, conn):
        data = b""
        while True:
            chunk = conn.recv(1024)
            if not chunk:
                return None, b""

            data += chunk
            if b"\n" in data:
                line, remainder = data.split(b"\n", 1)
                return line.decode(errors="ignore").strip(), remainder

            if len(data) > MAX_HEADER_LEN:
                raise ValueError("header too long")

    def listen_for_connections(self):
        while self.running:
            try:
                conn, addr = self.server.accept()
                threading.Thread(
                    target=self.handle_client,
                    args=(conn, addr),
                    daemon=True
                ).start()
            except Exception as e:
                if self.running:
                    print(f"accept error: {e}")

    def handle_client(self, conn, addr):
        try:
            header_line, remainder = self.read_header(conn)
            if not header_line:
                return

            header = json.loads(header_line)
            msg_type = header.get("type")

            if msg_type == "MESSAGE":
                self.receive_message(conn, header, remainder)
            elif msg_type == "FILE":
                self.receive_file(conn, header, remainder)
            elif msg_type == "DISCOVERY":
                self.handle_discovery(conn, header)

        except Exception as e:
            print(f"client error: {e}")
        finally:
            conn.close()

    def receive_message(self, conn, header, remainder=b""):
        length = header.get("length", 0)
        data = remainder

        while len(data) < length:
            chunk = conn.recv(length - len(data))
            if not chunk:
                raise ValueError("Connection closed before message complete")
            data += chunk

        try:
            text = data.decode(errors="ignore")
            sender = header.get("sender")
            timestamp = header.get("timestamp")
            print(f"\n[{timestamp}] {sender}: {text}")
            print(">> ", end="", flush=True)
        except Exception:
            pass

    def receive_file(self, conn, header, remainder=b""):
        try:
            filename = header.get("filename")
            filesize = header.get("filesize", 0)
            sender = header.get("sender")

            save_path = f"received_{sender}_{filename}"

            with open(save_path, "wb") as f:
                remaining = filesize

                if remainder:
                    f.write(remainder)
                    remaining -= len(remainder)

                while remaining > 0:
                    chunk = conn.recv(min(BUFFER_SIZE, remaining))
                    if not chunk:
                        break
                    f.write(chunk)
                    remaining -= len(chunk)

            print(f"[FILE] received {filename} -> {save_path}")

        except Exception as e:
            print(f"file receive error: {e}")

    def handle_discovery(self, conn, header):
        sender = header.get("sender")
        print(f"discovery request from {sender}")

    def connect_to_peer(self, host, port, peer_username):
        self.peers[(host, port)] = peer_username
        print(f"connected to {peer_username} at {host}:{port}")

    def send_message(self, message):
        if not self.peers:
            print("No peers connected. Please connect first.")
            return

        for (host, port), username in self.peers.items():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((host, port))

                body = message.encode()
                header = self.create_header(
                    msg_type="MESSAGE",
                    recipient=username,
                    body_length=len(body)
                )

                sock.sendall(header.encode())
                sock.sendall(body)

                sock.close()
                print(f"Sent to {username}")

            except Exception as e:
                print(f"failed to send to {username}: {e}")

    def send_file(self, filepath):
        if not self.peers:
            print("No peers connected. Please connect first.")
            return

        if not os.path.exists(filepath):
            print("file not found")
            return

        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath)

        for (host, port), username in self.peers.items():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((host, port))

                header = self.create_header(
                    msg_type="FILE",
                    recipient=username,
                    filename=filename,
                    filesize=filesize
                )

                sock.sendall(header.encode())

                with open(filepath, "rb") as f:
                    while True:
                        chunk = f.read(BUFFER_SIZE)
                        if not chunk:
                            break
                        sock.sendall(chunk)

                sock.close()
                print(f"sent file {filename} to {username}")

            except Exception as e:
                print(f"failed to send file to {username}: {e}")

    def close(self):
        self.running = False
        self.server.close()
        print(f"[{self.username}] closed")


if __name__ == "__main__":
    username = input("Enter your username: ")
    port = int(input("Enter listening port: "))

    peer = Peer(username, port)

    print("\nCommands:")
    print(" connect <host> <port> <peer_username>")
    print("   msg <message>   ")
    print("   file <filepath> ")
    print(" exit\n")

    while True:
        try:
            command = input(">> ").strip()

            if command.startswith("connect"):
                _, host, port_str, peer_user = command.split()
                peer.connect_to_peer(host, int(port_str), peer_user)

            elif command.startswith("msg"):
                message = command[len("msg"):].strip()
                peer.send_message(message)

            elif command.startswith("file"):
                filepath = command[len("file"):].strip()

                # Remove quotes if user typed them
                if filepath.startswith('"') and filepath.endswith('"'):
                    filepath = filepath[1:-1]

                peer.send_file(filepath)

            elif command.startswith("exit"):
                peer.close()
                break

        except KeyboardInterrupt:
            peer.close()
            break