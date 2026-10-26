# VASTOCHNIY AE Copilot — Execution MVP

An Adobe After Effects CEP panel with in-panel controls for a small, explicit set of operations in the active composition. The local browser interface remains optional for diagnostics.

## Implemented in source
- Animated text layer with scale/opacity keyframes
- Rounded rectangle shape layer
- Liquid-glass starter shape (translucent fill + highlight stroke; not physically accurate refraction)
- Prefix selected layer names
- In-panel natural-language request box with a review-before-execution plan
- Local, rule-based planner that maps requests only to the four allowlisted actions (no AI provider/API key yet)
- Serial command lifecycle with command IDs, explicit execution results, status logging, and a timeout state that warns against blind retries
- Python bridge integration tests that run without After Effects

## Important: implementation vs verification
Source code and automated bridge tests do **not** prove that the extension loads or works inside a user's After Effects installation. Live tests are still required on the target macOS/After Effects version. Do not treat a running browser page as proof that AE is connected; the CEP panel must poll the bridge, and an actual command must return a result.

## Natural-language planner: current scope
The planner is intentionally constrained and runs locally. It can recognize requests for animated text, rounded rectangles, the liquid-glass starter, and prefixing selected layer names. It extracts simple text/duration/prefix parameters, shows a proposed action, and requires a separate **Review & Run** click. Unsupported requests are rejected rather than converted into arbitrary scripts. This first implementation is rule-based, not an LLM; AI planning, reference-image interpretation, background removal, and media downloading are not implemented.

## Architecture
AE CEP panel UI → loopback Python HTTP bridge at `127.0.0.1:8766` → CEP panel → ExtendScript host script → execution result back to the panel. The browser dashboard is optional and can be opened manually at `http://127.0.0.1:8766`.

## Test the bridge
From the repository root:
```bash
python3 -m unittest discover -s tests -v
```
These tests exercise queue/status/result behavior only. They do not launch After Effects.

## Installation
See `INSTALL_MAC.txt`. CEP support and unsigned-extension loading vary by After Effects/macOS version. If the panel is absent from the Extensions (Legacy) menu, the installation has not been verified on that setup; do not claim compatibility without testing.