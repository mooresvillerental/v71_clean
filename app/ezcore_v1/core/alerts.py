from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import Optional

from .logger import EventLogger


def _which(cmd: str) -> Optional[str]:
    for d in os.environ.get("PATH", "").split(":"):
        c = os.path.join(d, cmd)
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


@dataclass
class Alerts:
    log: EventLogger
    enable_tts: bool = True
    tts_rate: float = 1.0
    tts_engine: Optional[str] = None

    def speak(self, text: str) -> None:
        if os.environ.get("EZ_SILENT_TESTS") == "1":
            return
        if not self.enable_tts:
            return

        engine = self.tts_engine
        if engine is None and _which("termux-tts-speak"):
            engine = "termux-tts-speak"

        if engine == "termux-tts-speak":
            try:
                subprocess.run(
                    ["termux-tts-speak", "-r", str(self.tts_rate), text],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception as e:
                self.log.line(f"TTS failed: {e}")
        else:
            # still log the message even if TTS unavailable
            self.log.line(f"TTS unavailable; text: {text}")

    def announce(self, text: str) -> None:
        # Regression-proof: always log announcements
        self.log.line(f"ALERT: {text}")
        self.speak(text)
