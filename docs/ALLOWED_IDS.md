<!-- GENERATED from the protocol specification by tools/make_id_table.py - do not edit by hand. -->

# Identifiers and the gateway

| Identifier | Name | Towards the bus | Towards the network |
|---|---|---|---|
| 0x095 | IMPACT_EVENT | refused | forwarded |
| 0x100 | GLOBAL_STATUS | forwarded | refused |
| 0x110 | QUERY_ACTIVE_TOOL | forwarded | refused |
| 0x111 | ACTIVE_TOOL_RESP | refused | forwarded |
| 0x120 | MOTION_CMD | forwarded | refused |
| 0x130 | SOLDER_SETPOINT | forwarded | refused |
| 0x131 | SOLDER_FEEDER_RESET | refused (dangerous) | refused |
| 0x132 | SOLDER_FEEDER_POS | forwarded | forwarded |
| 0x135 | SOLDER_TELEMETRY | refused | forwarded |
| 0x140 | DRILL_CMD | forwarded | refused |
| 0x145 | VACUUM_TELEMETRY | refused | forwarded |
| 0x147 | DRILL_TELEMETRY | refused | forwarded |
| 0x150 | AOI_CMD | forwarded | refused |
| 0x155 | AOI_TELEMETRY | refused | forwarded |
| 0x160 | LASER_CMD | forwarded | refused |
| 0x165 | LASER_TELEMETRY | refused | forwarded |
| 0x170 | PRINTER_THERMAL_MOTION | forwarded | refused |
| 0x173 | PRINTER_LAYERFAN_CMD | forwarded | refused |
| 0x175 | PRINTER_HOTEND_TELEMETRY | refused | forwarded |
| 0x177 | PRINTER_LAYERFAN_RPM | refused | forwarded |
| 0x178 | PRINTER_HOTENDFAN_CMD | forwarded | refused |
| 0x179 | PRINTER_HOTENDFAN_RPM | refused | forwarded |
| 0x180 | EXPANSION_SPI_REQ | forwarded | refused |
| 0x181 | EXPANSION_SPI_RESP | refused | forwarded |
| 0x182 | EXPANSION_DIAG0_REQ | forwarded | refused |
| 0x183 | EXPANSION_DIAG0_RESP | refused | forwarded |
| 0x190 | FRAM_QUERY | forwarded | refused |
| 0x191 | FRAM_STATE_RESP | refused | forwarded |
| 0x192 | ERASE_FRAM | refused (dangerous) | refused |
| 0x1A0 | SET_EXPANSION_TYPE | refused (dangerous) | refused |
| 0x1A1 | EXPANSION_TYPE_RESP | forwarded | forwarded |
| 0x1A2 | SET_FREE_TOOL | refused (dangerous) | refused |
| 0x1A3 | FREE_TOOL_CONFIG_RESP | forwarded | forwarded |
| 0x1A4 | SET_DEVICE_SERIAL | refused (dangerous) | refused |
| 0x1A5 | PERIPHERAL_INFO_RESP | forwarded | forwarded |
| 0x1A6 | SET_MLX_VARIANT | refused (dangerous) | refused |
| 0x1A7 | MLX_VARIANT_RESP | forwarded | forwarded |
| 0x1A8 | BLACKBOX_QUERY | forwarded | refused |
| 0x1A9 | BLACKBOX_CHUNK | refused | forwarded |
| 0x1AA | THERMAL_STATS_QUERY | forwarded | refused |
| 0x1AB | THERMAL_STATS_RESP | refused | forwarded |
| 0x1AC | SET_MULTINODE | refused (dangerous) | refused |
| 0x1AD | MULTINODE_CONFIG_RESP | forwarded | forwarded |
| 0x1AE | SET_FEATURES | refused (dangerous) | refused |
| 0x1AF | FEATURES_RESP | forwarded | forwarded |
| 0x1B0 | ELECTROMAGNET_CMD | forwarded | refused |
| 0x1B8 | HEALTH_PROFILE | refused | forwarded |
| 0x1B9 | PID_CONFIG | refused (dangerous) | refused |
| 0x1BA | PID_STATE_RESP | forwarded | forwarded |
| 0x1C0 | SPOT_WELD_CMD | forwarded | refused |
| 0x1D0 | UV_CURING_CMD | forwarded | refused |
| 0x1E0 | HOTAIR_CMD | forwarded | refused |
| 0x1F0 | CRIMPING_CMD | forwarded | refused |
| 0x200 | ULTRASONIC_WELD_CMD | forwarded | refused |
| 0x210 | SLAVE_ENTER_BOOTLOADER | refused (dangerous) | refused |
| 0x211 | SLAVE_START_UPDATE | refused (dangerous) | refused |
| 0x212 | SLAVE_HMAC_CHUNK | refused (dangerous) | refused |
| 0x213 | SLAVE_DATA | refused (dangerous) | refused |
| 0x214 | SLAVE_END_UPDATE | refused (dangerous) | refused |
| 0x215 | SLAVE_STATUS | refused (dangerous) | forwarded |
| 0x216 | SLAVE_PROGRESS | refused (dangerous) | forwarded |
| 0x217 | SLAVE_VERSION_RESP_1 | refused (dangerous) | forwarded |
| 0x218 | SLAVE_VERSION_RESP_2 | refused | forwarded |
| 0x219 | SLAVE_VERIFY_FAIL_REASON | refused (dangerous) | forwarded |
| 0x220 | SLAVE_REG_WRITE | refused (dangerous) | refused |
| 0x221 | SLAVE_REG_READ | refused (dangerous) | forwarded |
| 0x230 | PASTE_JETTING_CONFIG | forwarded | refused |
| 0x231 | PASTE_JETTING_PULSE | forwarded | refused |
| 0x240 | ADS1115_CONFIG | forwarded | refused |
| 0x241 | ADS1115_TRIGGER | forwarded | refused |
| 0x242 | ADS1115_RESULT | forwarded | forwarded |
| 0x243 | FLYING_PROBE_BASIC | refused | forwarded |
| 0x250 | THERMAL_TRIGGER | forwarded | refused |
| 0x251 | THERMAL_STATUS | forwarded | forwarded |
| 0x252 | THERMAL_RAW_CHUNK_REQ | forwarded | refused |
| 0x253 | THERMAL_RAW_CHUNK | refused | forwarded |
| 0x254 | THERMAL_CAL_CHUNK_REQ | forwarded | refused |
| 0x255 | THERMAL_CAL_CHUNK | refused | forwarded |
| 0x7E9 | VERSION_PATCH_RESPONSE | refused | forwarded |
| 0x7F0 | ENTER_BOOTLOADER | refused (dangerous) | refused |
| 0x7F1 | START_UPDATE | refused (dangerous) | refused |
| 0x7F2 | DATA | refused (dangerous) | refused |
| 0x7F3 | PAGE_ACK | refused | forwarded |
| 0x7F4 | END_UPDATE | refused (dangerous) | refused |
| 0x7F5 | STATUS | refused | forwarded |
| 0x7F6 | HEARTBEAT | refused | forwarded |
| 0x7F7 | HMAC_CHUNK | refused (dangerous) | refused |
| 0x7F8 | QUERY_VERSION | forwarded | refused |
| 0x7F9 | VERSION_RESPONSE | refused | forwarded |
| 0x7FA | BOOTLOADER_VERSION_RESPONSE | refused | forwarded |
| 0x7FB | QUERY_ERROR_COUNTERS | forwarded | refused |
| 0x7FC | ERROR_COUNTERS_RESPONSE | refused | forwarded |
| 0x7FD | AUTHORIZE_DOWNGRADE | refused (dangerous) | refused |
| 0x7FE | READBACK | refused (dangerous) | forwarded |
| 0x7FF | READBACK_PAGE_ACK | refused (dangerous) | refused |
