import logging
import sys

def set_logger(log_file, logger_name):
    # --- SETUP ---
    # Create logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)  # Or DEBUG for more details

    # Remove any previous handlers (avoids duplicate logs when re-running in notebooks)
    if logger.hasHandlers():
        logger.handlers.clear()

    # --- File handler ---
    file_handler = logging.FileHandler(log_file, mode="w")
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)

    # --- Console handler ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(message)s")  # cleaner output in console
    console_handler.setFormatter(console_formatter)

    # --- Attach handlers ---
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger
