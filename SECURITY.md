# Security Policy 🔒 (URTC-GATEWAY)

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.x.x  | ✅ Yes             |

## Reporting a Vulnerability

**CRITICAL: Do not report safety-critical vulnerabilities through public GitHub issues.**

This repository is a gateway whose whole job is to stand between a network and a machine. What a report here can be about:

1. **A frame that crosses when it should not**, for example an identifier, a length or a value the specification refuses that the gateway forwards, or a dangerous identifier that gets through without being unlocked.
2. **A way around the session key**: a replayed frame, a frame accepted with the wrong key, nonce or counter, or a key that is printed, logged or left readable.
3. **A way to exhaust the gateway**: a message that stops it, fills its memory or starves the peer that is allowed.
4. **A secret or private detail** in a public file.

How to report:

1. **Email**: send a detailed report to `electrohobby3d@gmail.com`.
2. **Response**: initial acknowledgment within 48 hours.

We follow a coordinated disclosure policy so that hardware safety is addressed before a public release. The gateway does not replace the measures of the CAN threat model (an interlock that no frame can close, a closed bus, a stop that cuts power); it has not been used on a real bus.
