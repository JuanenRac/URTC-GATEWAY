# Changelog

All notable changes to this project are documented here.

## [0.0.1] - A gateway in front of the CAN bus

- First version of the gateway: a program in front of the URTC CAN bus for an installation that cannot keep the bus closed.
- **Identifier list made from the protocol specification**: only the identifiers a host sends cross towards the bus. The dangerous ones (bootloader, update of the expansion slave, erase of the saved state, every persistent setting) are refused unless the operator unlocks them; questions are always allowed. `docs/ALLOWED_IDS.md` is generated and the CI fails when it is out of date.
- **Payload check**: the length and the values of a frame have to be those the specification allows (range, defined values, magic bytes).
- **Rate limit**: a token bucket per identifier and for the whole link, and a harder one for an unlocked dangerous identifier; a limit on the way out too.
- **Session key**: a peer proves it holds a key with an HMAC over a nonce of the connection, a counter and the frame; a recorded frame cannot be replayed in the same connection or in another. A key file is made with `keygen` (owner-only, never overwritten) and a key is never printed.
- **Every protection can be switched off**, from the configuration file or the command line, and the program lists each protection that is off when it starts. Listening on a non-local address without session authentication is refused unless asked for.
- A TCP end (one JSON object per line) and a bus end (an SLCAN serial adapter, or a loopback with nothing on it); the command line has `policy`, `ids`, `keygen` and `run`.
- Tested on the host with fakes and a real local socket; it has not been connected to a CAN bus, an adapter or a board.
