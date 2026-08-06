# dashboard

Current Tk GUI (`three_cam_controller.py`) lives here unchanged for Phase 1 — it still
talks HTTP directly to phones today.

Once the new networking core exists (`server/`), this process's Tk mainloop will call
into it *only* through `server/gateway` (a plain Python interface) via
`asyncio.run_coroutine_threadsafe` — never sharing a thread or event loop with asyncio.
No gRPC for this boundary: Dashboard and the core are two threads in one process, not
two processes, so a network protocol between them would add nothing but overhead. See
`docs/network_architecture.md` §Threading Model.

Future option (not decided): replace Tk with a web dashboard served by the same asyncio
process, removing this threading boundary entirely.
