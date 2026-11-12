# Options of the gateway

Every protection is **on by default** and every one can be switched off, in the configuration file and on the command line. A protection that is off, or loosened, is listed as a warning when the program starts (`urtc-gateway policy` shows the same list). The flags of the command line override the file; `--session` and `--no-session` (and the same for the other protections) are alternatives of each other.

| Protection | File section | Switch off | Switch on | What it does |
|---|---|---|---|---|
| Identifier list | `whitelist.enabled` | `--no-whitelist` | `--whitelist` | only the identifiers a host sends (taken from the specification) cross towards the bus |
| Dangerous identifiers | `whitelist.unlock_dangerous` | (default) | `--unlock-dangerous` | the bootloader, the update of the expansion slave, the erase of the saved state and every persistent setting are refused until unlocked |
| Added / removed identifiers | `whitelist.extra_allow`, `whitelist.deny` | | `--allow-id`, `--deny-id` | add an identifier to the list by hand, or take one out whatever the rest says |
| Payload check | `payload.enabled` | `--no-payload-check` | `--payload-check` | the length and the values of a frame must be those the specification allows |
| Rate limit | `rate.*` | `--no-rate-limit` | `--rate-limit` | a token bucket per identifier and for the whole link; `rate.overrides` gives an identifier its own rate and burst |
| Session key | `session.enabled`, `session.key_file` | `--no-session` | `--session`, `--key-file` | a peer proves it holds a key (HMAC with a nonce and a counter) |
| Outbound filter | `outbound.enabled`, `outbound.rate_hz` | `--no-outbound-filter` | `--outbound-filter` | only what a board sends goes towards the network, at a limited rate |
| Open network | `server.allow_open_network` | (default) | `--allow-open-network` | listening on a non-local address without a session key is refused unless asked for |

## The configuration file

A JSON object with the sections above; `schema` is 1. An unknown section or option, a wrong type or a negative rate is an error that says what is wrong. Example:

```json
{
  "schema": 1,
  "session": {"enabled": true, "key_file": "keys.txt"},
  "rate": {"per_id_hz": 20, "per_id_burst": 10, "overrides": {"0x160": [5, 2]}},
  "whitelist": {"extra_allow": ["0x1B0"], "deny": []},
  "server": {"host": "127.0.0.1", "port": 8765},
  "update_image": {"header": "warn"}
}
```

## The header inside a firmware image

The identifiers of a firmware update (the main board `0x7F1`/`0x7F2`/`0x7F4`, the expansion slave `0x211`/`0x213`/`0x214`) are dangerous ones, so they cross only with `whitelist.unlock_dangerous`. When they do, the gateway follows each update: the start frame says the size and the hardware, and the first bytes of the data show the 32-byte header that an image built with the header slot sealed carries inside it, at the fixed offset `0x200` (`IMAGE_HEADER.md` of URTC-COMMON). The header must hold (its CRC-32, the form that sits inside the image, no signature trailer), state the size the start frame announced and name the hardware of the start frame. If not, the rest of that update, and its end frame, are refused with the code `bad_image_header`.

An image with no header follows `update_image.header` (or `--image-header`): `accept` forwards it, `warn` (the default) forwards it and leaves a note in the audit, `require` refuses it. A header that is there is always checked, whatever the switch says.

It is a cut, not a prevention: the bytes before the decision (the first `0x220`) have already crossed, so a refused update starts and never ends; the board installs nothing, and its own verification of the image is what decides what runs. The CRC-32 of the whole image is the board's to check.

## The session

When a peer connects, the gateway sends `{"type": "hello", "nonce": "<hex>", "session": true}`. Every message the peer sends is one JSON object per line:

```json
{"id": 304, "data": "012C", "peer": "controller", "counter": 1, "mac": "<32 hex digits>"}
```

`mac` is the first 16 bytes of HMAC-SHA256, with the key of the peer, over `urtc-gw/1|<nonce>|<counter>|<id as three hex digits>|<data as hex>`. The counter has to grow with every message of the connection; the nonce is new for every connection, so a recorded message is useless later and elsewhere. A connection has one peer. The gateway answers a refused message with `{"type": "refused", "code": "<reason>"}` and sends the frames of the bus as `{"type": "frame", "id": ..., "data": "<hex>"}`.

`urtc-gateway keygen FILE PEER [PEER ...]` writes a key file with a new random key for each peer (readable by its owner only, never over an existing file) and does not show the keys. Give each peer only its own line.

## Trying it without a board

The gateway can be run against the virtual board of URTC-COMMON, which answers like the application of a tool head, with no adapter and no board:

```
python -m urtc_common.virtual_board --port 7777        # in URTC-COMMON/src (add it to PYTHONPATH)
urtc-gateway run --key-file gateway.keys --bus socket://127.0.0.1:7777
```

A peer that signs its frames with the session key (`urtc_gateway.gateway.sign_message`) can then send a version query and read the answer. `tests/test_virtual_board_end_to_end.py` does exactly this on every push: a signed query is answered, and a wrong key, a replayed counter and the order to enter the bootloader are refused without reaching the board. The tests find the shared package beside this repository or in the folder named by `URTC_COMMON_SRC`, and are skipped without it. This says nothing about a real adapter, the timing of a real bus or a real board.

## What it does not do

It does not encrypt: the bus is not a secret. It does not stop a peer that holds the key and misbehaves; the list, the payload check and the rate limit are there for that, and the watchdogs of the tool heads. It does not replace the hardware measures of the CAN threat model (an interlock that no frame can close, a closed bus, a stop that cuts power). It has never been used on a real bus.
