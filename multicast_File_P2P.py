import socket
import threading
import json
import os
import struct
import queue
from datetime import datetime

BUFFER_SIZE = 4096
MAX_HEADER_LEN = 10000

MULTICAST_ADDR = "224.0.0.10"
MULTICAST_PORT = 49152


def get_machine_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.254.254.254", 1))
        ip = s.getsockname()[0]
    except OSError:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


class PeerNotifier:
    def __init__(self):
        self.local_ip = get_machine_ip()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", MULTICAST_PORT))

        group = socket.inet_aton(MULTICAST_ADDR)
        mreq = struct.pack("4sL", group, socket.INADDR_ANY)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

        self.notifs = queue.Queue()
        threading.Thread(target=self.listen, daemon=True).start()

    def cast(self, message):
        self.sock.sendto(message.encode(), (MULTICAST_ADDR, MULTICAST_PORT))

    def listen(self):
        while True:
            data, addr = self.sock.recvfrom(1024)
            if addr[0] != self.local_ip:
                self.notifs.put((addr[0], data.decode()))


class Peer:
    def __init__(self, username, port):
        self.username = username
        self.port = port
        self.running = True
        self.msg_counter = 0
        self.peers = {}  # (ip, port) -> username

        # TCP server
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(("0.0.0.0", port))
        self.server.listen()

        print(f"[{self.username}] listening on port {port}")

        # discovery
        self.notifier = PeerNotifier()
        threading.Thread(target=self.discovery_listener, daemon=True).start()

        # TCP listener
        threading.Thread(target=self.listen_for_connections, daemon=True).start()

    def discovery_listener(self):
        while True:
            addr, msg = self.notifier.notifs.get()
            try:
                ip, port = msg.split(":")
                port = int(port)
                self.peers[(ip, port)] = None
                print(f"[DISCOVERY] peer found at {ip}:{port}")
            except:
                pass

    def broadcast_discovery(self):
        self.notifier.cast(f"{self.get_ip()}:{self.port}")

    def get_ip(self):
        return get_machine_ip()

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
                raise ValueError("connection closed before message complete")
            data += chunk

        try:
            text = data.decode(errors="ignore")
            sender = header.get("sender")
            timestamp = header.get("timestamp")
            print(f"\n[{timestamp}] {sender}: {text}")
        except:
            pass

    def send_message(self, host, port, message):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((host, port))
            header = self.create_header("MESSAGE", body_length=len(message))
            sock.sendall(header.encode())
            sock.sendall(message.encode())
        finally:
            sock.close()

    def group_send(self, message):
        for (ip, port) in self.peers:
            try:
                self.send_message(ip, port, message)
            except:
                pass

    def send_file(self, host, port, filepath):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((host, port))

            filename = os.path.basename(filepath)
            filesize = os.path.getsize(filepath)

            header = self.create_header(
                "FILE",
                body_length=filesize,
                filename=filename,
                filesize=filesize
            )

            sock.sendall(header.encode())

            with open(filepath, "rb") as f:
                while chunk := f.read(BUFFER_SIZE):
                    sock.sendall(chunk)

            print(f"[FILE] sent {filename} to {host}:{port}")

        finally:
            sock.close()

    def handle_discovery(self, conn, header):
        sender = header.get("sender")
        print(f"discovery request from {sender}")

    def connect_to_peer(self, host, port, peer_username):
        self.peers[(host, port)] = peer_username
        print(f"connected to {peer_username} at {host}:{port}")

    def close(self):
        self.running = False
        self.server.close()
        print(f"[{self.username}] closed")


if __name__ == "__main__":
    username = input("Enter your username: ")
    port = int(input("Enter listening port: "))

    peer = Peer(username, port)
    peer.broadcast_discovery()

    print("\nCommands:")
    print(" discover")
    print(" connect <host> <port> <peer_username>")
    print("   msg <host> <port> <message>")
    print("   group <message>")
    print("   file <host> <port> <filepath>")
    print(" exit\n")

    while True:
        try:
            command = input(">> ").strip()

            if command == "discover":
                peer.broadcast_discovery()

            elif command.startswith("connect"):
                _, host, port, user = command.split()
                peer.connect_to_peer(host, int(port), user)

            elif command.startswith("msg"):
                _, host, port, *msg = command.split()
                peer.send_message(host, int(port), " ".join(msg))

            elif command.startswith("group"):
                msg = command[len("group"):].strip()
                peer.group_send(msg)

            elif command.startswith("file"):
                _, host, port, filepath = command.split()
                peer.send_file(host, int(port), filepath)

            elif command == "exit":

                peer.close()
                break

        except KeyboardInterrupt:
            peer.close()
            break