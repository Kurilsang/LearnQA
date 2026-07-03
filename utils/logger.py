import logging
import os
from datetime import datetime


class TestLogger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
        os.makedirs(self.log_dir, exist_ok=True)
        log_file = os.path.join(self.log_dir, f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        self.logger = logging.getLogger("UITest")
        self.logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter("[%(asctime)s] %(levelname)s | %(message)s", datefmt="%H:%M:%S")
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        self._steps = []

    def info(self, msg):
        self.logger.info(msg)
        self._steps.append(("INFO", msg))

    def warn(self, msg):
        self.logger.warning(msg)
        self._steps.append(("WARN", msg))

    def error(self, msg):
        self.logger.error(msg)
        self._steps.append(("ERROR", msg))

    def debug(self, msg):
        self.logger.debug(msg)

    def step(self, msg):
        self.info(f"[步骤] {msg}")

    def assertion(self, msg, passed):
        if passed:
            self.info(f"[通过] {msg}")
        else:
            self.error(f"[失败] {msg}")
        self._steps.append(("ASSERT", msg, passed))
        return passed

    @property
    def steps(self):
        return self._steps
