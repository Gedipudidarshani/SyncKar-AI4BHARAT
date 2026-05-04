"""
Unit tests for Circuit Breaker — AGENTS.md §9.
Verifies OPEN, HALF_OPEN, and CLOSED transitions.
"""

from unittest import mock

import pytest

from synckar.pipeline.circuit_breaker import CircuitBreaker, CircuitState


@pytest.fixture
def mock_redis():
    with mock.patch("synckar.pipeline.circuit_breaker.redis.Redis") as mock_r:
        r_instance = mock.Mock()
        mock_r.from_url.return_value = r_instance
        yield r_instance


def test_circuit_breaker_initial_state(mock_redis):
    cb = CircuitBreaker("sws", redis_client=mock_redis)
    mock_redis.get.return_value = None  # No state stored

    assert cb.get_state() == CircuitState.CLOSED
    assert cb.is_call_permitted() is True


def test_circuit_breaker_transitions_to_open_on_failures(mock_redis):
    cb = CircuitBreaker("sws", redis_client=mock_redis)
    mock_redis.get.return_value = CircuitState.CLOSED.value
    # Simulate 5 failures returned by zcard
    mock_redis.zcard.return_value = 5

    cb.record_failure()

    # Should set state to OPEN
    mock_redis.set.assert_any_call(cb._state_key, CircuitState.OPEN.value)


def test_circuit_breaker_half_open_allows_one_call(mock_redis):
    cb = CircuitBreaker("sws", redis_client=mock_redis)
    mock_redis.get.return_value = CircuitState.HALF_OPEN.value

    # First call permitted
    assert cb.is_call_permitted() is True


def test_circuit_breaker_success_closes_half_open(mock_redis):
    cb = CircuitBreaker("sws", redis_client=mock_redis)
    mock_redis.get.return_value = CircuitState.HALF_OPEN.value

    cb.record_success()

    mock_redis.set.assert_called_with(cb._state_key, CircuitState.CLOSED.value)
