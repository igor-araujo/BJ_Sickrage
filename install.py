# coding: utf-8

import sys
import os
import re
import shutil
import logging

def start_logging():
    logger = logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
    logger = logging.getLogger('')
    
    return logger

def main(SICKRAGE_PATH):
    logger = start_logging()
    if not SICKRAGE_PATH:
        logger.info("No SickRage Path informed.")
        sys.exit(1)
    
    if SICKRAGE_PATH[-1] == "/":
        SICKRAGE_PATH = SICKRAGE_PATH[:-1]
    logger.debug("SickRage Path: {}".format(SICKRAGE_PATH))
    PROVIDERS_PATH = SICKRAGE_PATH + r"/sickbeard/providers"
    logger.debug("Providers Path: {}".format(PROVIDERS_PATH))
    IMG_PATH = SICKRAGE_PATH + r"/gui/slick/images/providers"
    logger.debug("Image Path: {}".format(IMG_PATH))

    if os.path.isdir(PROVIDERS_PATH) and os.path.exists(PROVIDERS_PATH):
        if os.path.exists(PROVIDERS_PATH + "/bjshare.py"):
            logger.info("An old version of bjshare.py was found. It will be replaced")
            os.remove(PROVIDERS_PATH + "/bjshare.py")

        shutil.copy("bjshare.py",PROVIDERS_PATH)
        logger.info("bjshare.py was copied")


        with open("{0}/__init__.py".format(PROVIDERS_PATH), "r+") as f:
            file_text = f.read()

            if not re.search("from sickbeard.providers import bjshare,", file_text):
                file_text = re.sub("from sickbeard.providers import", "from sickbeard.providers import bjshare,", file_text)
            if not re.search("__all__ = \[\n    'bjshare', ", file_text):
                file_text = re.sub("__all__ = \[\n    ", "__all__ = [\n    'bjshare', ",file_text)

            logger.info("{}/__init__.py was successfully modified".format(PROVIDERS_PATH))

            f.seek(0)
            f.write(file_text)
            f.truncate()

    if os.path.isdir(IMG_PATH) and os.path.exists(IMG_PATH):
        if os.path.exists(IMG_PATH + "/bj_share.png"):
            logger.info("An old version of bj_share.png was found. It will be replaced")
            os.remove(IMG_PATH + "/bj_share.png")

        shutil.copy("bj_share.png", IMG_PATH)
        logger.info("bj_share.png was copied".format(IMG_PATH))

if __name__ == "__main__":
	if len(sys.argv) < 2:
		sys.stderr.write("usage:\n  python install.py sickrage_absolute_path\n")
		sys.exit(1)
    
	main(sys.argv[1])
