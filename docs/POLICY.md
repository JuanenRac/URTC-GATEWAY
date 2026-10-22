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
  "server": {"host": "127.0.0.1", "port": 8765}
}
```

## The session

When a peer connects, the gateway sends `{"type": "hello", "nonce": "<hex>", "session": true}`. Every message the peer sends is one JSON object per line:

```json
{"id": 304, "data": "012C", "peer": "controller", "counter": 1, "mac": "<32 hex digits>"}
```

`mac` is the first 16 bytes of HMAC-SHA256, with the key of the peer, over `urtc-gw/1|<nonce>|<counter>|<id as three hex digits>|<data as hex>`. The counter has to grow with every message of the connection; the nonce is new for every connection, so a recorded message is useless later and elsewhere. A connection has one peer. The gateway answers a refused message with `{"type": "refused", "code": "<reason>"}` and sends the frames of the bus as `{"type": "frame", "id": ..., "data": "<hex>"}`.

`urtc-gateway keygen FILE PEER [PEER ...]` writes a key file with a new random key for each peer (readable by its owner only, never over an existing file) and does not show the keys. Give each peer only its own line.

## What it does not do

It does not encrypt: the bus is not a secret. It does not stop a peer that holds the key and misbehaves; the list, the payload check and the rate limit are there for that, and the watchdogs of the tool heads. It does not replace the hardware measures of the CAN threat model (an interlock that no frame can close, a closed bus, a stop that cuts power). It has never been used on a real bus.
