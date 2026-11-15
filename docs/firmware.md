<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Portable firmware reference gate

`firmware/ctl01/command_gate.hpp` is a small C++17 host-reference command gate. Construction rejects every non-finite or non-positive speed/yaw/heartbeat limit with `std::invalid_argument`; invalid limits never reach clamps or watchdog comparisons. It boots disabled/zero, requires zero-command arming, bounds finite commands, latches e-stop/protective/watchdog faults, stops for pause/manual override, requires zero-command reset after causes clear, and never automatically resumes.

**It is non-safety-rated, simulation-only reference code. It has no MCU pins, interrupts, actuator drivers, bootloader, communications peripheral, flashing support or deployment integration. It is not a substitute for the independent protective chain or a validated embedded controller.**

## Host test

```sh
python3 firmware/ctl01/run_host_tests.py
# or
make firmware-test
```

The script uses `$CXX` or `g++` with `-std=c++17 -Wall -Wextra -Wpedantic -Werror -Wconversion -Wsign-conversion`, writes the executable under ignored `builds/firmware/`, and runs 45 host checks. No target tool is invoked.

## Python versus C++ roles

Python is the executable system reference: strict configuration, geometry, planning, tracking, environment/telemetry checks, simulation, missions and reports. C++ is a small language-portability reference for core disabled/arm/stop/fault and watchdog command-gating semantics. Shared names and transition expectations reduce divergence, but C++ deliberately does not duplicate geometry, planning or maintenance logic. Python integration tests and C++ host tests both run in `tools/check_all.py`.

Any far-future embedded implementation would require selected hardware/toolchain qualification, timing and memory analysis, defined safe states, independent protective architecture, fault diagnostics, formal requirements/traceability, appropriate coding rules, verification on reviewed target hardware, cybersecurity and signed release. None is claimed or supplied.
