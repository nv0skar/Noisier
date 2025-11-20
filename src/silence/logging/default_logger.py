import logging

from ..settings import settings
from ..logging.default_formatter import DefaultFormatter
from ..logging.handler import MaybeBlockingHandler

logger = logging.getLogger("silence")
log_lvl = logging.DEBUG if settings.DEBUG_ENABLED else logging.INFO
logger.setLevel(log_lvl)

ch = MaybeBlockingHandler()
ch.setLevel(log_lvl)
ch.setFormatter(DefaultFormatter())

logger.addHandler(ch)
