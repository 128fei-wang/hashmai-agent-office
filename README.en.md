# RoostOffice — a Roost-style Multi-Agent Office

A pixel-style, single-page **multi-agent office dashboard**. A company laid out as a walkable
office map: the boss's office issues orders, the operations center dispatches them, and every
department (HR, Finance, Tech, Data, UI, QA — at most **3 seats each**) has agents that walk to
their desk, take the task, and report back. You see *who is where, doing what, at which step*,
instead of a wall of logs.

Built with **PixiJS 8** and plain JavaScript — no bundler, no npm dependencies, one HTML page.

- 10 zones, 23 seats, 53×24 tile grid, 1600×800 target viewport
- WebGL first, automatic Canvas2D fallback (`?force2d=1`)
- `?selfcheck=1` emits machine-readable JSON for CI / third-party verification
- Ships a **single-file build** (all deps inlined as data URIs) for review environments
- Measured 60.0 fps, p95 16.8 ms, 0 slow frames (>20 ms) on WebGL2 / ANGLE Metal, 1600×800

## Quick start

```bash
git clone https://github.com/128fei-wang/hashmai-agent-office.git
cd hashmai-agent-office
python3 -m http.server 8080
# open http://localhost:8080/demo/office-demo.html
```

Or open `demo/office-demo-single.html` directly by double-click — no server needed.

## Verify

```bash
node tools/test_sim.js                              # 9/9
python3 tools/check_seat_ids.py --require-unified   # seats=23 zones=8 fail=0
```

Requirements: Python 3.10+, Node 18+. See [README.md](README.md) for the full Chinese
documentation, architecture notes and design rationale.

## Contributing / License

Read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) first;
report security issues privately per [SECURITY.md](SECURITY.md).
Released under the [Apache License 2.0](LICENSE) (with an express patent grant; see [NOTICE](NOTICE)).
The "Hashmai / 哈希麦" name and logo are trademarks and are not covered by that grant.
