# Contributing to URTC-GATEWAY 🛡️

This repository is the gateway of the URTC CAN threat model: it decides which frames cross between a network and the bus. A contribution that makes it refuse more of what it should refuse, or that makes an option clearer, is the most useful kind.

## Technology Stack
- **Gateway**: Python 3.10+, standard library only at run time; pyserial is optional and only needed for a real SLCAN adapter.
- **Tests**: pytest, including a test over a real local socket; ruff for the lint.
- **Protocol**: `src/urtc_gateway/urtc_protocol.py` is a checked copy of the generated module of URTC-COMMON (`tools/vendor_copy.py` of that repository writes it and its lock file); it is never edited by hand.

## Guidelines
1. **The specification is the only source of identifiers.** Do not type an identifier into the gateway; change the specification in URTC-COMMON, copy the module again, and run `python tools/make_id_table.py`.
2. **Every protection stays switchable.** A new protection needs an option in `config.py`, a flag in `cli.py`, a sentence in `warnings()` for when it is off, and a test for each of the two states.
3. **Fail closed.** A frame that cannot be understood is refused; a key file that cannot be read stops the gateway instead of turning the session check off.
4. **Never print or log a key.** Tests check that a key does not appear in messages.
5. **Eight languages.** The README exists in English, Spanish, French, Italian, German, Chinese, Japanese and European Portuguese, with the same sections and links; `tools/ci_validate.py` compares them.
6. **Nothing private in public files.** No dates, no names of private notes, no tracking codes, no secrets, no addresses of a real installation.
7. **Tests.** `python -m pytest tests -q` must pass. Use `build-test.sh` / `build-test.bat` to check without changing the version; `build.sh` / `build.bat` raise it.
