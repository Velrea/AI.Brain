import os
import sys
import time

import pytest

import brain.write
from brain.lock import FileLock, LockTimeout
from brain.write import AppendBlocked, Writer

from conftest import entry, event_files, python, records_of

HOLD_LOCK = """
import sys, time
from brain.lock import FileLock
with FileLock(sys.argv[1]):
    print("held", flush=True)
    time.sleep(float(sys.argv[2]))
"""


def hold_lock(path, seconds):
    proc = python(HOLD_LOCK, str(path), str(seconds))
    assert proc.stdout.readline().strip() == "held", proc.stderr.read()
    return proc


def test_a_session_that_cannot_take_the_lock_gets_an_error(store, state):
    writer = Writer(store, state, lock_timeout=0.5)
    writer.append(entry())
    holder = hold_lock(writer._lock.path, 30)
    try:
        started = time.monotonic()
        with pytest.raises(LockTimeout):
            writer.append(entry(description="waits"))
        assert 0.4 < time.monotonic() - started < 5
    finally:
        holder.kill()
        holder.wait()
    [path] = event_files(store)
    assert len(records_of(path)) == 1


def test_a_session_waits_while_the_lock_is_held_briefly(store, state):
    writer = Writer(store, state, lock_timeout=10)
    holder = hold_lock(writer._lock.path, 0.5)
    try:
        writer.append(entry())
    finally:
        holder.wait()
    assert len(event_files(store)) == 1


def test_a_process_that_dies_holding_the_lock_blocks_nothing(store, state):
    writer = Writer(store, state, lock_timeout=2)
    holder = hold_lock(writer._lock.path, 60)
    holder.kill()
    holder.wait()

    writer.append(entry())

    assert writer._lock.path.exists()
    assert len(event_files(store)) == 1


def test_the_lock_is_released_after_each_append(store, state):
    writer = Writer(store, state)
    writer.append(entry())
    with FileLock(writer._lock.path, timeout=0):
        pass


def test_an_append_blocked_by_another_process_retries_until_released(store, state):
    """The sync service stands in as a process that holds the file open and shares nothing."""
    if os.name != "nt":
        pytest.skip("only Windows blocks an open file from other processes")
    writer = Writer(store, state)
    writer.append(entry(description="first"))
    [path] = event_files(store)
    holder = hold_exclusively(path, 1.0)
    try:
        started = time.monotonic()
        writer.append(entry(description="second"))
        assert time.monotonic() - started > 0.5
    finally:
        holder.wait()
    assert [r["description"] for r in records_of(path)] == ["first", "second"]


def test_an_append_blocked_past_the_retries_gets_an_error(store, state):
    if os.name != "nt":
        pytest.skip("only Windows blocks an open file from other processes")
    writer = Writer(store, state, append_retry=0.5)
    writer.append(entry(description="first"))
    [path] = event_files(store)
    holder = hold_exclusively(path, 2)
    try:
        with pytest.raises(AppendBlocked):
            writer.append(entry(description="second"))
    finally:
        holder.wait()
    assert [r["description"] for r in records_of(path)] == ["first"]


def test_an_append_retries_a_blocked_open(writer, store, monkeypatch):
    """The same retry, on any platform, with the block simulated."""
    blocked = [3]
    real_open = open

    def flaky_open(path, mode="r", *args, **kwargs):
        if "a" in mode and blocked[0]:
            blocked[0] -= 1
            raise PermissionError(13, "The process cannot access the file", str(path))
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(brain.write, "open", flaky_open, raising=False)
    writer.append(entry())

    assert blocked[0] == 0
    [path] = event_files(store)
    assert len(records_of(path)) == 1


HOLD_EXCLUSIVELY = """
import ctypes, sys, time
from ctypes import wintypes
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.CreateFileW.restype = wintypes.HANDLE
GENERIC_READ, OPEN_EXISTING, NO_SHARING = 0x80000000, 3, 0
handle = kernel32.CreateFileW(sys.argv[1], GENERIC_READ, NO_SHARING, None, OPEN_EXISTING, 0, None)
if handle == wintypes.HANDLE(-1).value:
    raise ctypes.WinError(ctypes.get_last_error())
print("held", flush=True)
time.sleep(float(sys.argv[2]))
kernel32.CloseHandle(handle)
"""


def hold_exclusively(path, seconds):
    proc = python(HOLD_EXCLUSIVELY, str(path), str(seconds))
    assert proc.stdout.readline().strip() == "held", proc.stderr.read()
    return proc
