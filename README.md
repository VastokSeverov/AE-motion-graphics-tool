# VASTOCHNIY AE Copilot — Execution MVP

A local browser interface and Adobe After Effects CEP panel that executes a small, explicit set of operations in the active composition.

## Implemented in source
- Animated text layer with scale/opacity keyframes
- Rounded rectangle shape layer
- Liquid-glass starter shape (translucent fill + highlight stroke; not physically accurate refraction)
- Prefix selected layer names
- Serial command lifecycle with command IDs, explicit execution results, status logging, and a timeout state that warns against blind retries
- Python bridge integration tests that run without After Effects

## Important: implementation vs verification
Source code and automated bridge tests do **not** prove that the extension loads or works inside a user's After Effects installation. Live tests are still required on the target macOS/After Effects version. Do not treat a running browser page as proof that AE is connected; the CEP panel must poll the bridge, and an actual command must return a result.

## Architecture
Browser UI → loopback Python HTTP bridge at `127.0.0.1:8766` → CEP panel → ExtendScript host script → execution result back to browser.

## Test the bridge
From the repository root:
```bash
python3 -m unittest discover -s tests -v
```
These tests exercise queue/status/result behavior only. They do not launch After Effects.

## Installation
See `INSTALL_MAC.txt`. CEP support and unsigned-extension loading vary by After Effects/macOS version. If the panel is absent from the Extensions (Legacy) menu, the installation has not been verified on that setup; do not claim compatibility without testing.