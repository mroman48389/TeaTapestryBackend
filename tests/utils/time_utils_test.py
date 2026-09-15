from datetime import datetime, timedelta, timezone

from src.utils.time_utils import (
    just_expired_td,
    just_valid_td,
    before_now_dt,
    after_now_dt,
    is_older_than,
    is_younger_than,
    is_in_past,
    is_in_future
)

# -----------------------------
# just_expired_td / just_valid_td
# -----------------------------

def test_just_expired_td():

    window = timedelta(seconds = 10)

    assert just_expired_td(window) == timedelta(seconds = 11)


def test_just_valid_td():

    window = timedelta(seconds = 10)

    assert just_valid_td(window) == timedelta(seconds = 9)


# -----------------------------
# before_now_dt
# -----------------------------

def test_before_now_dt_returns_past_datetime():

    now = datetime.now(timezone.utc)

    dt = before_now_dt(timedelta(seconds = 1))

    assert dt < now


def test_before_now_dt_is_timezone_aware():

    dt = before_now_dt(timedelta(seconds = 1))

    assert dt.tzinfo is timezone.utc

# -----------------------------
# after_now_dt
# -----------------------------

def test_after_now_dt_returns_future_datetime():

    now = datetime.now(timezone.utc)

    dt = after_now_dt(timedelta(seconds = 1))

    assert dt > now


def test_after_now_dt_is_timezone_aware():

    dt = after_now_dt(timedelta(seconds = 1))

    assert dt.tzinfo is timezone.utc


# -----------------------------
# is_older_than
# -----------------------------

def test_is_older_than_true_when_older():

    window = timedelta(seconds = 5)

    dt = before_now_dt(just_expired_td(window))  # 6 seconds ago

    assert is_older_than(dt, window) is True


def test_is_older_than_false_when_younger():

    window = timedelta(seconds = 5)

    dt = before_now_dt(just_valid_td(window))  # 4 seconds ago

    assert is_older_than(dt, window) is False


def test_is_older_than_normalizes_naive_datetime():

    window = timedelta(seconds = 5)

    now = datetime.now(timezone.utc)
    dt = (now - timedelta(seconds = 6)).replace(tzinfo = None) # naive datetime

    assert is_older_than(dt, window) is True


# -----------------------------
# is_younger_than
# -----------------------------

def test_is_younger_than_true_when_younger():

    window = timedelta(seconds = 5)

    dt = before_now_dt(just_valid_td(window))  # 4 seconds ago

    assert is_younger_than(dt, window) is True


def test_is_younger_than_false_when_older():

    window = timedelta(seconds = 5)

    dt = before_now_dt(just_expired_td(window))  # 6 seconds ago

    assert is_younger_than(dt, window) is False


def test_is_younger_than_normalizes_naive_datetime():

    window = timedelta(seconds = 5)

    now = datetime.now(timezone.utc)
    dt = (now - timedelta(seconds = 4)).replace(tzinfo = None) # naive datetime

    assert is_younger_than(dt, window) is True


# -----------------------------
# is_in_past
# -----------------------------

def test_is_in_past_true_for_past_datetime():

    dt = before_now_dt(timedelta(seconds = 1))

    assert is_in_past(dt) is True


def test_is_in_past_false_for_future_datetime():

    dt = after_now_dt(timedelta(seconds = 1))

    assert is_in_past(dt) is False


def test_is_in_past_normalizes_naive_datetime():

    now = datetime.now(timezone.utc)
    dt = now - timedelta(seconds = 1)
    dt = dt.replace(tzinfo = None)  # make it naive

    assert is_in_past(dt) is True


# -----------------------------
# is_in_future
# -----------------------------

def test_is_in_future_true_for_future_datetime():

    dt = after_now_dt(timedelta(seconds = 1))

    assert is_in_future(dt) is True


def test_is_in_future_false_for_past_datetime():

    dt = before_now_dt(timedelta(seconds = 1))

    assert is_in_future(dt) is False


def test_is_in_future_normalizes_naive_datetime():

    now = datetime.now(timezone.utc)
    dt = now + timedelta(seconds = 1)
    dt = dt.replace(tzinfo = None)  # make it naive

    assert is_in_future(dt) is True