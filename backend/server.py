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

        if mode != last_mode or path != last_path or typed_input != last_typed_input:
            last_mode = mode
            last_path = list(path)  # snapshot — path is mutated in place elsewhere
            last_typed_input = typed_input

            message = json.dumps({
                "mode": mode,
                "path": path,
                "typed_input": typed_input,
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