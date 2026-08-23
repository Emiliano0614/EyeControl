import asyncio
import json
import websockets


async def handler(websocket, shared_data, state_machine):
    print("Client connected!")
    last_mode = None
    last_path = None
    last_typed_input = None

    while shared_data["running"]:
        mode = state_machine.mode
        path = state_machine.path
        typed_input = state_machine.typed_input

        changed = (mode != last_mode or path != last_path or typed_input != last_typed_input)

        if changed:
            last_mode = mode
            last_path = list(path)  # snapshot — path is mutated in place elsewhere
            last_typed_input = typed_input

        # CHANGED (scroll bug fix): originally this only sent when
        # changed was True, which meant SCROLL only ever announced
        # itself ONCE per tilt — content.js would scrollBy() a single
        # time and then wait for the next state change, giving a tiny
        # one-shot jump instead of continuous scrolling. Now it also
        # sends on every tick while mode == "SCROLL", so the browser
        # keeps getting told to scroll for as long as the tilt holds.
        # SELECT/typed_input behavior is untouched — still change-only,
        # so ENTER-confirmation logic in content.js doesn't get spammed.
        if changed or mode == "SCROLL":
            message = json.dumps({
                "mode": mode,
                "path": path,
                "typed_input": typed_input,
                # CHANGED: scroll_direction was missing from this payload
                # entirely at first — the browser had no way to know UP
                # vs DOWN even when it did receive a SCROLL message.
                "scroll_direction": state_machine.scroll_direction,
            })
            await websocket.send(message)

        await asyncio.sleep(0.05)


async def start_server(shared_data, state_machine):
    # functools.partial-style wrapping: websockets.serve only ever calls
    # handler with (websocket) — it doesn't know about shared_data/
    # state_machine. This lambda closes over them so handler still gets
    # access, without changing what websockets.serve expects to call.
    async def bound_handler(websocket):
        await handler(websocket, shared_data, state_machine)

    async with websockets.serve(bound_handler, "localhost", 8765):
        print("WebSocket server running on ws://localhost:8765")
        await asyncio.Future()  # run forever


def run_server_thread(shared_data, state_machine):
    asyncio.run(start_server(shared_data, state_machine))