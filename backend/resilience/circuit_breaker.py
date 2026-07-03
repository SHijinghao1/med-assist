"""熔断器: 连败熔断 → 降级 → 半开探测 → 自动恢复"""
import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum

from utils.logging import log


class State(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """熔断器打开时抛出, 由降级逻辑接管"""
    pass


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_probe_count: int = 1
    success_to_close: int = 2

    state: State = State.CLOSED
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_at: float = 0.0
    open_at: float = 0.0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _probe_in_flight: bool = False

    async def call(self, coro_factory):
        """
        执行受保护的调用。
        coro_factory: 无参 async callable (传 factory 而非 coroutine)
        """

        if self.state == State.OPEN:
            elapsed = time.monotonic() - self.open_at
            if elapsed < self.recovery_timeout:
                raise CircuitOpenError(
                    f"[{self.name}] 熔断中 ({self.consecutive_failures}次连败), "
                    f"{self.recovery_timeout - elapsed:.0f}s 后探测"
                )
            async with self._lock:
                if self.state == State.OPEN:
                    self.state = State.HALF_OPEN
                    self.consecutive_successes = 0
                    log.warning("circuit.half_open", breaker=self.name)

        if self.state == State.HALF_OPEN:
            async with self._lock:
                if self._probe_in_flight:
                    raise CircuitOpenError(
                        f"[{self.name}] 半开探测进行中，请稍后"
                    )
                self._probe_in_flight = True

        try:
            result = await coro_factory()

            async with self._lock:
                if self.state == State.HALF_OPEN:
                    self.consecutive_successes += 1
                    self._probe_in_flight = False
                    if self.consecutive_successes >= self.success_to_close:
                        self.state = State.CLOSED
                        self.consecutive_failures = 0
                        log.info("circuit.closed", breaker=self.name)
                else:
                    self.consecutive_failures = 0

            return result

        except CircuitOpenError:
            raise
        except Exception as e:
            async with self._lock:
                self.consecutive_failures += 1
                self.last_failure_at = time.monotonic()

                if self.state == State.HALF_OPEN:
                    self._probe_in_flight = False
                    self.state = State.OPEN
                    self.open_at = time.monotonic()
                    log.error("circuit.half_open_failed",
                              breaker=self.name, error=str(e))
                elif self.consecutive_failures >= self.failure_threshold:
                    self.state = State.OPEN
                    self.open_at = time.monotonic()
                    log.error("circuit.opened",
                              breaker=self.name,
                              failures=self.consecutive_failures)

            raise
