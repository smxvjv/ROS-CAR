from unittest.mock import Mock

import pytest

from xfyun_speech.audio import AplaySink


def test_aplay_sink_close_releases_process_on_success():
    sink = AplaySink('plughw:CARD=Device,DEV=0', 16000)
    process = Mock()
    process.stdin.closed = False
    process.wait.return_value = 0
    sink._process = process

    sink.close()

    process.stdin.close.assert_called_once_with()
    assert sink._process is None


def test_aplay_sink_close_releases_process_on_failure():
    sink = AplaySink('plughw:CARD=Device,DEV=0', 16000)
    process = Mock()
    process.stdin.closed = False
    process.wait.return_value = 1
    process.stderr.read.return_value = b'device unavailable'
    sink._process = process

    with pytest.raises(RuntimeError, match='device unavailable'):
        sink.close()

    assert sink._process is None
    sink.close()
