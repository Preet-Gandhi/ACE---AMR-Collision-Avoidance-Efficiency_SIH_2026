"""Launcher for the ACE AMR Fleet Control Streamlit Dashboard.

Usage:
    python run_dashboard.py
"""

from __future__ import annotations

import atexit
import os
import signal
import subprocess
import sys
from pathlib import Path


_JOB_OBJECT = None


def _bind_to_job_object(process_handle: int) -> None:
    """On Windows, bind the child process to a Job Object so it terminates if the parent dies."""
    global _JOB_OBJECT
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_uint64),
                ("WriteOperationCount", ctypes.c_uint64),
                ("OtherOperationCount", ctypes.c_uint64),
                ("ReadTransferCount", ctypes.c_uint64),
                ("WriteTransferCount", ctypes.c_uint64),
                ("OtherTransferCount", ctypes.c_uint64),
            ]

        class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryLimit", ctypes.c_size_t),
                ("PeakJobMemoryLimit", ctypes.c_size_t),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        job = kernel32.CreateJobObjectW(None, None)
        if job:
            info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
            # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
            info.BasicLimitInformation.LimitFlags = 0x2000
            kernel32.SetInformationJobObject(
                job,
                9,  # JobObjectExtendedLimitInformation
                ctypes.byref(info),
                ctypes.sizeof(info),
            )
            kernel32.AssignProcessToJobObject(job, int(process_handle))
            _JOB_OBJECT = job
    except Exception:
        pass


def run() -> None:
    app_path = str(Path(__file__).parent / "dashboard" / "app.py")
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        app_path,
        "--server.address=localhost",
        "--server.port=8501",
        "--browser.gatherUsageStats=false",
    ]
    # Pass any additional CLI flags from caller
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])

    proc = subprocess.Popen(cmd)

    # Ensure child process is bound to Job Object on Windows so termination of parent terminates child
    if hasattr(proc, "_handle"):
        _bind_to_job_object(proc._handle)

    def _cleanup(*_args):
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()

    atexit.register(_cleanup)
    try:
        signal.signal(signal.SIGINT, _cleanup)
        signal.signal(signal.SIGTERM, _cleanup)
    except (ValueError, AttributeError):
        pass

    try:
        sys.exit(proc.wait())
    except KeyboardInterrupt:
        _cleanup()
        sys.exit(0)


if __name__ == "__main__":
    run()
