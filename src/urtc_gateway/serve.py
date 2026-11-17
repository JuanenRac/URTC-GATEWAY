# =============================================================================
# URTC-GATEWAY - src/urtc_gateway/serve.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The ends of the gateway: a TCP port with one JSON object per line towards the network, and a bus port (SLCAN serial adapter, or a loopback).

One peer is served at a time: the robot controller. A second connection waits until the first one closes. A line longer than
``MAX_LINE`` bytes ends the connection. Nothing here has been run against a real adapter.
"""
from __future__ import annotations

import json
import queue
import socket
import threading
import time
from typing import Any, Protocol

from .config import GatewayConfig
from .gateway import Gateway
from .urtc_protocol import BITRATE as BUS_BITRATE

MAX_LINE = 4096


class Bus(Protocol):
    def send(self, can_id: int, data: bytes) -> None: ...
    def recv(self, timeout: float) -> tuple[int, bytes] | None: ...
    def close(self) -> None: ...


class LoopbackBus:
    """A bus with nothing on it: what is sent is kept for the caller and what the caller injects is received. For tests and for a dry run."""

    def __init__(self) -> None:
        self.sent: list[tuple[int, bytes]] = []
        self._inbox: queue.Queue[tuple[int, bytes]] = queue.Queue()

    def send(self, can_id: int, data: bytes) -> None:
        self.sent.append((can_id, bytes(data)))

    def inject(self, can_id: int, data: bytes) -> None:
        self._inbox.put((can_id, bytes(data)))

    def recv(self, timeout: float) -> tuple[int, bytes] | None:
        try:
            return self._inbox.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self) -> None:
        pass


class SerialSlcanBus:
    """An SLCAN adapter on a serial port (needs the pyserial package). Standard frames only."""

    BITRATE_CODES = {10000: "S0", 20000: "S1", 50000: "S2", 100000: "S3", 125000: "S4", 250000: "S5", 500000: "S6", 800000: "S7", 1000000: "S8"}

    def __init__(self, port: str, bitrate: int = BUS_BITRATE, baudrate: int = 115200) -> None:
        try:
            import serial  # noqa: PLC0415
        except ImportError as error:
            raise RuntimeError("the serial bus needs the pyserial package (pip install pyserial)") from error
        if bitrate not in self.BITRATE_CODES:
            raise ValueError(f"bit rate {bitrate} is not one an SLCAN adapter takes")
        if "://" in port:  # a pyserial URL such as socket://127.0.0.1:7777: the virtual board of URTC-COMMON, or a serial server
            self._port = serial.serial_for_url(port, baudrate=baudrate, timeout=0.05)
        else:
            self._port = serial.Serial(port, baudrate, timeout=0.05)
        self._buffer = b""
        self._lock = threading.Lock()
        for command in ("C", self.BITRATE_CODES[bitrate], "O"):
            self._port.write(command.encode("ascii") + b"\r")

    def send(self, can_id: int, data: bytes) -> None:
        line = f"t{can_id:03X}{len(data)}{data.hex().upper()}\r".encode("ascii")
        with self._lock:
            self._port.write(line)

    def recv(self, timeout: float) -> tuple[int, bytes] | None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self._buffer += self._port.read(64)
            if b"\r" in self._buffer:
                line, _, self._buffer = self._buffer.partition(b"\r")
                text = line.decode("ascii", errors="replace")
                if len(text) >= 5 and text[0] == "t":
                    try:
                        count = int(text[4], 16)
                        return int(text[1:4], 16), bytes.fromhex(text[5:5 + 2 * count])
                    except ValueError:
                        continue
        return None

    def close(self) -> None:
        try:
            self._port.write(b"C\r")
        finally:
            self._port.close()


POLL_S = 0.2


def _send_all(conn: socket.socket, payload: bytes, limit_s: float) -> None:
    """Write all of ``payload``; raise ``TimeoutError`` when the peer lets it take longer than ``limit_s`` seconds (0 = no limit)."""
    if not hasattr(conn, "send"):
        conn.sendall(payload)
        return
    deadline = time.monotonic() + limit_s if limit_s > 0 else None
    view = memoryview(payload)
    while view:
        try:
            sent = conn.send(view)
        except TimeoutError:
            if deadline is not None and time.monotonic() >= deadline:
                raise
            continue
        view = view[sent:]


def _lines(conn: socket.socket, stop: threading.Event, give_up=lambda: False):
    buffer = b""
    conn.settimeout(POLL_S)
    while not stop.is_set() and not give_up():
        try:
            chunk = conn.recv(1024)
        except TimeoutError:
            continue
        except OSError:
            return
        if not chunk:
            return
        buffer += chunk
        while b"\n" in buffer:
            line, _, buffer = buffer.partition(b"\n")
            yield line
        if len(buffer) > MAX_LINE:
            return


def serve_connection(conn: socket.socket, gateway: Gateway, bus: Bus, stop: threading.Event, log=lambda text: None) -> None:
    """Serve one peer until it closes, or the stop event is set. The bus reader runs beside the line reader."""
    send_lock = threading.Lock()
    config = getattr(gateway, "config", None)
    send_limit = float(getattr(getattr(config, "server", None), "send_timeout_s", 0.0))
    sessions_on = bool(getattr(getattr(config, "session", None), "enabled", False))
    auth_limit = float(getattr(getattr(config, "server", None), "auth_timeout_s", 0.0)) if sessions_on else 0.0
    conn.settimeout(POLL_S)         # a write is attempted in short steps, so that a peer that stops reading is noticed after ``send_limit``
    started = time.monotonic()

    def to_network(message: dict[str, Any]) -> None:
        with send_lock:
            _send_all(conn, json.dumps(message, separators=(",", ":")).encode("utf-8") + b"\n", send_limit)

    gateway.to_network = to_network
    try:
        to_network(gateway.hello())
    except OSError as error:
        log(f"peer lost before it was greeted: {error.__class__.__name__}")   # one bad peer must not end the gateway
        return
    done = threading.Event()

    def bus_reader() -> None:
        while not done.is_set() and not stop.is_set():
            frame = bus.recv(0.1)
            if frame is not None:
                try:
                    gateway.from_bus(*frame)
                except OSError as error:
                    log(f"peer lost while writing to it: {error.__class__.__name__}")
                    done.set()      # the connection cannot go on without its bus reader: the line reader gives up too
                    return

    reader = threading.Thread(target=bus_reader, daemon=True, name="urtc-gateway-bus")
    reader.start()
    try:
        def give_up() -> bool:
            if done.is_set():
                return True
            if auth_limit > 0 and not getattr(gateway, "authenticated", True) and time.monotonic() - started >= auth_limit:
                log(f"peer disconnected: it did not prove its key within {auth_limit:g} s")
                return True
            return False

        for raw in _lines(conn, stop, give_up):
            try:
                message = json.loads(raw.decode("utf-8"))
            except ValueError:
                message = "not json"          # the gateway refuses anything that is not a JSON object, and counts it
            decision = gateway.from_network(message)
            if not decision:
                log(f"refused {decision.code}: {decision.detail}")
                to_network({"type": "refused", "code": decision.code})
    except OSError as error:
        log(f"peer lost: {error.__class__.__name__}")      # only this connection ends; the gateway goes on to the next peer
    finally:
        done.set()
        reader.join(timeout=1.0)


def run(config: GatewayConfig, keys: dict[str, bytes] | None, bus: Bus, stop: threading.Event, log=print,
        ready: threading.Event | None = None, bound: list | None = None) -> None:
    """Listen and serve peers one after the other until ``stop`` is set."""
    server = socket.socket(socket.AF_INET6 if ":" in config.server.host else socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((config.server.host, config.server.port))
    server.listen(1)
    server.settimeout(0.2)
    if bound is not None:
        bound.append(server.getsockname()[1])
    if ready is not None:
        ready.set()
    dropped = 0
    try:
        while not stop.is_set():
            try:
                conn, address = server.accept()
            except TimeoutError:
                continue
            except OSError as error:
                # A failed accept (no free descriptors, a connection reset before it was taken) must not end the service.
                dropped += 1
                log(f"accept failed ({error.__class__.__name__}); {dropped} connections dropped")
                stop.wait(0.2)
                continue
            log(f"peer connected from {address[0]}")
            gateway = Gateway(config, keys, bus.send, lambda m: None, time.monotonic)
            try:
                with conn:
                    serve_connection(conn, gateway, bus, stop, log)
            except OSError as error:
                dropped += 1
                log(f"connection ended by {error.__class__.__name__}; {dropped} connections dropped")
            log("peer closed; " + json.dumps({**gateway.summary(), "connections_dropped": dropped}))
    finally:
        server.close()
