# VASTOCHNIY AE Copilot — Execution MVP

A local browser interface and Adobe After Effects CEP panel that can execute a small set of real operations in the active composition.

## Implemented
- Animated text layer with scale/opacity keyframes
- Rounded rectangle shape layer
- Liquid-glass starter shape (translucent fill + highlight stroke; not physically accurate refraction)
- Prefix selected layer names

## Architecture
Browser UI → local Python HTTP bridge on `127.0.0.1:8766` → CEP panel → After Effects ExtendScript host script → execution result back to browser.

See `INSTALL_MAC.txt` for installation and troubleshooting. CEP support/unsigned extension loading varies by AE version, so successful installation on the user's actual AE 2026 must be confirmed before adding more features.
