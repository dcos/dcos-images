import time
import sys
import logging
log = logging.getLogger(__name__)
while True:
    time.sleep(1)
    log.info('hello world')
    sys.stdout.flush()
