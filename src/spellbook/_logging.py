from __future__ import annotations

CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "%(message)s"},
        "detail": {
            "format": "[%(levelname)s - %(asctime)s] [%(name)s - %(module)s.%(funcName)s %(lineno)d] %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S%z",
        },
    },
    "handlers": {
        "to_console": {
            "class": "rich.logging.RichHandler",
            "level": "INFO",
            "formatter": "simple",
            # RichHandler.__init__()
            # "console": rich_console,
            "show_level": True,
            "rich_tracebacks": True,
            "markup": True,
            "log_time_format": "[%X]",
        },
        # "to_file": {
        #     "()": "cs_tools.cli._logging.LimitedFileHistoryHandler",
        #     "level": "DEBUG",
        #     "formatter": "detail",
        #     "filename": f"{logs_dir}/{now}.log",
        #     "mode": "w",
        #     "max_files_to_keep": 25,
        #     "encoding": "utf-8",
        #     "delay": True,
        # },
    },
    "loggers": {
        "": {
            "level": "DEBUG",
            "handlers": [
                "to_console",
                # "to_file",
            ],
            "propagate": False,
        },
        "uvicorn.error": {
            "level": "INFO",
            "handlers": [
                "to_console",
            ],
            "propagate": False,
        },
        "uvicorn.access": {
            "level": "INFO",
            "handlers": [
                "to_console",
            ],
            "propagate": False,
        },
    },
}
