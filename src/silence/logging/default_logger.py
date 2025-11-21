import logging

from silence.__main__ import CONFIG
from silence.logging.default_formatter import DefaultFormatter
from silence.logging.handler import MaybeBlockingHandler

logger = logging.getLogger("silence")
log_lvl = logging.DEBUG if CONFIG.debug else logging.INFO
logger.setLevel(log_lvl)

ch = MaybeBlockingHandler()
ch.setLevel(log_lvl)
ch.setFormatter(DefaultFormatter())

logger.addHandler(ch)
