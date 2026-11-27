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
import re
import socket
import threading
import time
from typing import Any, Protocol

from .config import GatewayConfig
from .gateway import Gateway
from .update_guard import UpdateGuard
from .urtc_protocol import BITRATE as BUS_BITRATE

MAX_LINE = 4096
MAX_SERIAL_LINE = 128    # the longest line of a frame is about 25 characters; more without a line end is noise
# "tIIIL" + the data, and after it only the four digits of the time stamp that some adapters add
_SLCAN_FRAME = re.compile(r"t([0-7][0-9A-Fa-f]{2})([0-8])((?:[0-9A-Fa-f]{2}){0,10})")


def _slcan_frame(line: bytes) -> tuple[int, bytes] | None:
    """The identifier and data of a received SLCAN line, or None when it is not a whole standard data frame."""
    match = _SLCAN_FRAME.fullmatch(line.decode("ascii", errors="replace").lstrip("\a\n"))
    if match is None:
        return None
    count, digits = int(match.group(2)), match.group(3)
    if len(digits) not in (2 * count, 2 * count + 4):
        return None   # cut, or run together with another line: it must not be forwarded as a shorter frame
    return int(match.group(1), 16), bytes.fromhex(digits[:2 * count])


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
        while True:
            while b"\r" in self._buffer:       # what already arrived goes out first, so a busy bus does not pile up here
                line, _, self._buffer = self._buffer.partition(b"\r")
                frame = _slcan_frame(line)
                if frame is not None:
                    return frame
            if len(self._buffer) > MAX_SERIAL_LINE:
                self._buffer = b""
            if time.monotonic() >= deadline:
                return None
            self._buffer += self._port.read(64)

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
    idle_limit = float(getattr(getattr(config, "server", None), "idle_timeout_s", 0.0))
    started = time.monotonic()
    last_heard = [started]          # when the peer last sent a line
    queue_size = max(0, int(getattr(getattr(config, "server", None), "send_queue", 0)))
    outbox: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=queue_size)    # not used when queue_size is 0
    done = threading.Event()

    def write(message: dict[str, Any]) -> None:
        with send_lock:
            _send_all(conn, json.dumps(message, separators=(",", ":")).encode("utf-8") + b"\n", send_limit)

    def enqueue(message: dict[str, Any]) -> None:
        """Queue a frame for the writer; when the queue is full the oldest frame goes, and the drop is counted as ``out_slow_peer``."""
        while True:
            try:
                outbox.put_nowait(message)
                return
            except queue.Full:
                try:
                    outbox.get_nowait()
                except queue.Empty:
                    continue
                stats = getattr(gateway, "stats", None)
                if stats is not None:
                    stats.refused["out_slow_peer"] += 1

    def to_network(message: dict[str, Any]) -> None:
        # Messages of control (the greeting, a refusal, an answer) are written at once; frames of the bus go through the queue when there is one, so a peer that reads
        # slowly costs frames (counted) and not the bus reader. The writer holds the same lock, so a line is never written in pieces among others.
        if queue_size > 0 and message.get("type") == "frame":
            enqueue(message)
        else:
            write(message)

    gateway.to_network = to_network
    try:
        to_network(gateway.hello())
    except OSError as error:
        log(f"peer lost before it was greeted: {error.__class__.__name__}")   # one bad peer must not end the gateway
        return

    def writer() -> None:
        while not done.is_set() and not stop.is_set():
            try:
                message = outbox.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                write(message)
            except OSError as error:
                log(f"peer lost while writing to it: {error.__class__.__name__}")
                done.set()      # as for the bus reader: the connection cannot go on, and the line reader gives up too
                return

    def bus_reader() -> None:
        while not done.is_set() and not stop.is_set():
            try:
                frame = bus.recv(0.1)
            except OSError as error:       # the adapter was unplugged or its port failed
                log(f"the bus failed: {error.__class__.__name__}; the connection ends")
                done.set()
                return
            if frame is not None:
                try:
                    gateway.from_bus(*frame)
                except OSError as error:
                    log(f"peer lost while writing to it: {error.__class__.__name__}")
                    done.set()      # the connection cannot go on without its bus reader: the line reader gives up too
                    return

    reader = threading.Thread(target=bus_reader, daemon=True, name="urtc-gateway-bus")
    reader.start()
    emitter = threading.Thread(target=writer, daemon=True, name="urtc-gateway-writer")
    if queue_size > 0:
        emitter.start()
    try:
        def give_up() -> bool:
            if done.is_set():
                return True
            if auth_limit > 0 and not getattr(gateway, "authenticated", True) and time.monotonic() - started >= auth_limit:
                log(f"peer disconnected: it did not prove its key within {auth_limit:g} s")
                return True
            if idle_limit > 0 and time.monotonic() - last_heard[0] >= idle_limit:
                log(f"peer disconnected: it sent nothing for {idle_limit:g} s")
                return True
            return False

        for raw in _lines(conn, stop, give_up):
            last_heard[0] = time.monotonic()
            try:
                message = json.loads(raw.decode("utf-8"))
            except (ValueError, RecursionError):   # a very deeply nested line raises the second one on some versions of Python
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
        if queue_size > 0:
            emitter.join(timeout=1.0)


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
    guard = UpdateGuard(config.update_image.header)   # one for all the connections: an update the board is in does not end with the peer
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
            gateway = Gateway(config, keys, bus.send, lambda m: None, time.monotonic, guard)
            try:
                with conn:
                    serve_connection(conn, gateway, bus, stop, log)
            except OSError as error:
                dropped += 1
                log(f"connection ended by {error.__class__.__name__}; {dropped} connections dropped")
            log("peer closed; " + json.dumps({**gateway.summary(), "connections_dropped": dropped}))
    finally:
        server.close()
