import socket
import time
import threading


SERVER_IP = socket.gethostbyname(socket.gethostname())
SERVER_PORT = 4010
HEARTBEAT_TIMEOUT = 10  
HEARTBEAT_TOKEN = b"HEARTBEAT"


clients = {}
clients_lock = threading.Lock()


def start_server():
  """Start UDP heartbeat server"""
  server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  server_socket.bind(('', SERVER_PORT))
  server_socket.settimeout(1)
  
  print(f"UDP Heartbeat Server listening on {SERVER_IP}:{SERVER_PORT}")
  print(f"Heartbeat timeout: {HEARTBEAT_TIMEOUT}s\n")
  
  
  monitor_thread = threading.Thread(target=check_inactive_clients, args=(clients,), daemon=True)
  monitor_thread.start()
  
  try:
    while True:
      try:
        data, client_address = server_socket.recvfrom(1024)
        current_time = time.time()
        
        
        with clients_lock:
          clients[client_address] = current_time
        
        print(f"[{time.strftime('%H:%M:%S')}] Heartbeat from {client_address}: {data.decode()}")
        
        
        ack_message = f"ACK {current_time}".encode()
        server_socket.sendto(ack_message, client_address)
        
      except socket.timeout:
        continue
        
  except KeyboardInterrupt:
    print("\nServer shutting down...")
  finally:
    server_socket.close()


def check_inactive_clients(clients_dict):
  """Monitor and remove inactive clients"""
  while True:
    time.sleep(2)
    current_time = time.time()
    
    with clients_lock:
      inactive = [addr for addr, last_time in clients_dict.items() 
            if current_time - last_time > HEARTBEAT_TIMEOUT]
      
      for client_address in inactive:
        del clients_dict[client_address]
        print(f"[TIMEOUT] Client {client_address} removed (no heartbeat for {HEARTBEAT_TIMEOUT}s)")


if __name__ == '__main__':
  start_server()