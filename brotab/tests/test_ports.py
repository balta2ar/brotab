import pytest

from brotab.inout import get_available_tcp_port


def test_no_free_port_raises_runtime_error():
    # An empty port range cannot yield a port: the helper must raise
    # instead of returning the RuntimeError instance as a value.
    with pytest.raises(RuntimeError):
        get_available_tcp_port(start=10000, end=10000)
