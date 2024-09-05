import sys
import subprocess
import os

import logging
import logging.handlers
from datetime import datetime, timedelta

try: # rich
    from rich.logging import RichHandler
except:
    subprocess.check_call([sys.executable,'-m', 'pip', 'install', '--upgrade', 'rich'])
    from rich.logging import RichHandler

try: # BackgroundScheduler
    from apscheduler.schedulers.background import BackgroundScheduler
except:
    subprocess.check_call([sys.executable,'-m', 'pip', 'install', '--upgrade', 'apscheduler'])
    from apscheduler.schedulers.background import BackgroundScheduler

import sys

# 로그 포맷 설정
RICH_FORMAT = "[%(filename)s:%(lineno)s] >> %(message)s"
FILE_HANDLER_FORMAT = "[%(asctime)s] %(levelname)s [%(filename)s:%(funcName)s:%(lineno)s] >> %(message)s"

LOG_PATH = os.path.join(os.path.join(os.getcwd(), "files") , "logs")

def setup_logging() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format=RICH_FORMAT,
        handlers=[RichHandler(rich_tracebacks=True)]
    )
    logger = logging.getLogger(os.path.join(LOG_PATH , f"{datetime.now().year}{datetime.now().month}{datetime.now().day}_log.txt"))

    if len(logger.handlers) > 0:
        return logger

    file_handler = logging.FileHandler(os.path.join(LOG_PATH , f"{datetime.now().year}{datetime.now().month}{datetime.now().day}_log.txt"), mode="a", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(FILE_HANDLER_FORMAT))
    logger.addHandler(file_handler)

    start_scheduler()
    return logger

def remove_old_log_files(directory):
    today = datetime.today()

    for filename in os.listdir(directory):
        if filename.endswith("_log.txt"):
            file_date_string = filename.split("_")[0]
            file_date = datetime.strptime(file_date_string, "%Y%m%d")
            if today - file_date > timedelta(days=7):

                file_path = os.path.join(directory, filename)
                os.remove(file_path)

def start_scheduler():
    scheduler = BackgroundScheduler(timezone="Asia/Seoul")
    scheduler.add_job(remove_old_log_files, 'cron', hour=0, minute=0, args=[LOG_PATH])
    scheduler.start()                

def handle_exception(exc_type, exc_value, exc_traceback):
    logger = logging.getLogger()
    logger.error("Unexpected exception", exc_info=(exc_type, exc_value, exc_traceback))


