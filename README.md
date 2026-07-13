# Network Protocols Lab: Heartbeat, Multicast, & P2P

A Python-based networking project demonstrating core distributed systems concepts: node discovery via multicast, connection maintenance via UDP heartbeats, and decentralized communication through a Peer-to-Peer (P2P) network.

## Features

*   **UDP Heartbeat:** Continuous node status monitoring using lightweight UDP ping/pong messages to detect active vs. dead peers.
*   **Multicast Discovery:** Dynamic local network peer discovery using IP multicast, removing the need for hardcoded IP addresses.
*   **Decentralized P2P (`p2p.py`):** Direct peer-to-peer data sharing and messaging architecture with no central server.

## Prerequisites

*   Python 3.8 or higher
*   A local network that supports UDP multicast traffic (or testing via `localhost`)

## Installation & Setup

1. Clone the repository to your local machine:
   ```bash
   git clone https://github.com
   cd html
   ```

2. (Optional) Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

## Usage Guide

### 1. Running the P2P Network
Start multiple instances of `p2p.py` in separate terminal windows to simulate different nodes.

```bash
# Start Peer 1 on port 5001
python p2p.py --port 5001

# Start Peer 2 on port 5002 and connect to Peer 1
python p2p.py --port 5002 --connect 127.0.0.1:5001
```

### 2. Testing Multicast Discovery
Run the discovery script to listen for incoming multicast beacons or broadcast your presence.
```bash
python multicast_discovery.py
```

### 3. Monitoring via UDP Heartbeat
Launch the heartbeat listener to keep track of active node uptimes.
```bash
python heartbeat_monitor.py
```

##  Project Structure

```text
├── p2p.py                # Main peer-to-peer networking logic and message handling
├── multicast.py          # Multicast group broadcasting and automatic peer discovery
├── heartbeat.py          # UDP heartbeat sender and receiver modules for failure detection
└── README.md             # Project documentation
```
