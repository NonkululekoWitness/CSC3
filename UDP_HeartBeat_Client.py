import socket
import threading
import time
import argparse

server_ip= socket.gethostbyname(socket.gethostname())
server_port = 4010

class UDPHeartbeatClient:
  def __init__(self, server_ip, server_port, beat_period=3):
    self.server_ip = server_ip
    self.server_port = server_port
    self.beat_period = beat_period
    self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.socket.settimeout(1)
    self.sequence_number = 0
    self.running = True

  def receive_messages(self):
    while self.running:
      try:
        message, address = self.socket.recvfrom(1024)
        print(f"Received from {address}: {message.decode()}")
      except socket.timeout:
        continue
      except Exception as e:
        print(f"Error receiving: {e}")

  def send_heartbeat(self):
    while self.running:
      try:
        self.sequence_number += 1
        timestamp = time.time()

        # message = f"HEARTBEAT {self.sequence_number} {timestamp}".encode()

        text  = input("Enter heartbeat message (or 'exit' to quit): ")

        if text.lower() == 'exit':
          self.running = False
          break

        message = f"HEARTBEAT {self.sequence_number} {timestamp} {text}".encode()

        self.socket.sendto(message, (self.server_ip, self.server_port))
        print(f"Sent heartbeat #{self.sequence_number}")
        time.sleep(self.beat_period)
      except Exception as e:
        print(f"Error sending: {e}")

  def start(self):
    recv_thread = threading.Thread(target=self.receive_messages, daemon=True)
    recv_thread.start()
    
    try:
      self.send_heartbeat()
    except KeyboardInterrupt:
      print("\nShutting down client...")
      self.running = False
    finally:
      self.socket.close()

if __name__ == '__main__':
  # parser = argparse.ArgumentParser(description="UDP Heartbeat Client")
  # parser.add_argument('--serverip', required=True, help="Server IP address")
  # parser.add_argument('--serverport', type=int, required=True, help="Server port (1024-65535)")
  # args = parser.parse_args()

  # client = UDPHeartbeatClient(args.serverip, args.serverport)
  # client.start()   

  
  client = UDPHeartbeatClient(server_ip, server_port)
  client.start()
