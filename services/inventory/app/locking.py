import asyncio
import time
from contextlib import asynccontextmanager

import structlog
from redis.asyncio import Redis

logger = structlog.get_logger()

@asynccontextmanager
async def acquire_lock(
    redis: Redis,
    lock_key: str,
    expire_seconds: int = 10,
    timeout_seconds: int = 5
):
    """Context manager for distributed locks using Redis."""
    token = str(time.time())
    acquired = False
    start_time = time.monotonic()

    while time.monotonic() - start_time < timeout_seconds:
        # SET key value NX (only if not exists) EX (expire in seconds)
        res = await redis.set(lock_key, token, ex=expire_seconds, nx=True)
        if res:
            acquired = True
            break
        await asyncio.sleep(0.05) # Poll with minor delay

    if not acquired:
        logger.warn("Distributed lock acquisition timed out", lock_key=lock_key)
        raise TimeoutError(f"Unable to acquire lock for key {lock_key} within timeout window.")

    logger.debug("Distributed lock acquired", lock_key=lock_key)
    try:
        yield
    finally:
        # Lua script guarantees atomic delete only if token matches, preventing removing another lock
        lua_release = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        try:
            await redis.eval(lua_release, 1, lock_key, token)
            logger.debug("Distributed lock released", lock_key=lock_key)
        except Exception as e:
            logger.error("Failed to release distributed lock safely", lock_key=lock_key, error=str(e))
