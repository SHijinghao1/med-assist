"""Circuit Breaker 状态机单元测试"""
import asyncio
import pytest
from resilience.circuit_breaker import CircuitBreaker, CircuitOpenError, State


class FakeError(Exception):
    pass


@pytest.fixture
def breaker():
    return CircuitBreaker(
        name="test-cb",
        failure_threshold=3,
        recovery_timeout=0.5,
        half_open_probe_count=1,
        success_to_close=2,
    )


@pytest.mark.asyncio
async def test_closed_passes_through(breaker):
    """CLOSED 状态下正常通过"""
    result = await breaker.call(lambda: asyncio.sleep(0.01, result="ok"))
    assert result == "ok"
    assert breaker.state == State.CLOSED


@pytest.mark.asyncio
async def test_opens_after_threshold(breaker):
    """连续失败达到阈值 → OPEN"""
    for i in range(breaker.failure_threshold):
        with pytest.raises(FakeError):
            await breaker.call(lambda: _raise(FakeError("boom")))
    assert breaker.state == State.OPEN


@pytest.mark.asyncio
async def test_open_rejects_immediately(breaker):
    """OPEN 状态下直接拒绝"""
    # 先让它熔断
    for _ in range(breaker.failure_threshold):
        with pytest.raises(FakeError):
            await breaker.call(lambda: _raise(FakeError()))

    # 现在应该直接拒绝
    with pytest.raises(CircuitOpenError):
        await breaker.call(lambda: asyncio.sleep(0, result="should not reach"))


@pytest.mark.asyncio
async def test_half_open_after_timeout(breaker):
    """OPEN 超时后进入 HALF_OPEN"""
    breaker.state = State.OPEN
    breaker.open_at = __import__("time").monotonic() - (breaker.recovery_timeout + 0.1)

    # 应该能通过（进入 HALF_OPEN）
    result = await breaker.call(lambda: asyncio.sleep(0.01, result="probe"))
    assert result == "probe"
    assert breaker.state == State.HALF_OPEN


@pytest.mark.asyncio
async def test_half_open_fail_back_to_open(breaker):
    """HALF_OPEN 探测失败 → 回到 OPEN"""
    breaker.state = State.HALF_OPEN
    breaker.consecutive_successes = 0

    with pytest.raises(FakeError):
        await breaker.call(lambda: _raise(FakeError()))

    assert breaker.state == State.OPEN


@pytest.mark.asyncio
async def test_half_open_success_then_close(breaker):
    """HALF_OPEN 连续成功 → CLOSED"""
    breaker.state = State.HALF_OPEN
    breaker.consecutive_successes = 0

    # 连续成功 success_to_close 次
    for _ in range(breaker.success_to_close):
        await breaker.call(lambda: asyncio.sleep(0.01, result="ok"))

    assert breaker.state == State.CLOSED
    assert breaker.consecutive_failures == 0


@pytest.mark.asyncio
async def test_closed_resets_failure_count_on_success(breaker):
    """CLOSED 状态下一次成功重置失败计数"""
    for _ in range(2):  # 2 次失败（未达阈值）
        with pytest.raises(FakeError):
            await breaker.call(lambda: _raise(FakeError()))
    assert breaker.consecutive_failures == 2

    # 一次成功 → 计数重置
    await breaker.call(lambda: asyncio.sleep(0.01, result="ok"))
    assert breaker.consecutive_failures == 0


def _raise(exc: Exception):
    async def _inner():
        raise exc
    return _inner()  # 返回 coroutine 对象，不是函数
