import asyncio
from utils.runtime import process_options

async def spawn(args):
    return await asyncio.create_subprocess_exec(*args, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE, **process_options())

async def stop(process):
    if process.returncode is not None: return
    try:
        process.stdin.write(b'q\n'); await process.stdin.drain()
    except (BrokenPipeError,ConnectionResetError): pass
    try: await asyncio.wait_for(process.wait(), 15)
    except asyncio.TimeoutError:
        process.terminate()
        try: await asyncio.wait_for(process.wait(),5)
        except asyncio.TimeoutError: process.kill(); await process.wait()

async def capture(stream, logger):
    # Redact complete lines so credentials split between read() chunks cannot leak.
    buffer = b''
    dropping = False
    while chunk := await stream.read(4096):
        buffer += chunk
        while b'\n' in buffer:
            line, buffer = buffer.split(b'\n', 1)
            if not dropping: logger.warning(line.decode('utf-8', errors='replace'))
            dropping = False
        if len(buffer) > 65536:
            buffer = b''; dropping = True
    if buffer and not dropping: logger.warning(buffer.decode('utf-8', errors='replace'))
