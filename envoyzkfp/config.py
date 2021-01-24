import configparser
import os
import logging
import logging.handlers
import sys


logger = logging.getLogger(__name__)


def get_config():
    return singleton.get_config()


class ManagedLogger:
    def __init__(self):
        self.cli_handler = logging.StreamHandler(sys.stderr)
        self.syslog_handler = logging.handlers.SysLogHandler()
        self.file_handler = None
        logging.getLogger().addHandler(self.cli_handler)
        logging.getLogger().addHandler(self.syslog_handler)
        logging.getLogger().setLevel(logging.DEBUG)

    def parse_level(self, level_str):
        try:
            return getattr(logging, level_str.upper())
        except AttributeError:
            raise ValueError("Unknown log level: %s" % (level_str));

    def load_config(self, config):
        self.cli_handler.setLevel(
            self.parse_level(config['logging']['cli_level'])
        )

        cli_formatter = logging.Formatter(config['logging']['cli_format'],
            datefmt=config['logging']['date_format'])
        self.cli_handler.setFormatter(cli_formatter)

        self.syslog_handler.setLevel(
            self.parse_level(config['logging']['syslog_level'])
        )

        try:
            self.file_handler = logging.FileHandler(config['logging']['file_target'])
            self.file_handler.setLevel(
                self.parse_level(config['logging']['file_level'])
            )
            self.file_handler.setFormatter(cli_formatter)
            logging.getLogger().addHandler(self.file_handler)
        except KeyError:
            # ignore, just don't log to files
            pass

    def setup_formatter(self):
        pass

class Config:
    default_config = {
        'logging': {
            'date_format': '%Y-%m-%d %H:%M:%S %z',
            'cli_target': 'stdout',
            'cli_level': 'warning',
            'cli_format': '[%(asctime)s] [%(levelname) 7s] [%(name)  21s] %(message)s',
            'file_level': 'info',
            'syslog_level': 'warn',
        },
        'envoy': {
            'access_log': '/dev/stdout'
        },
    }

    search_paths = (
        os.path.join(os.getcwd(), 'conf', 'envoy-zkfp.ini'),
        '/etc/envoy/zkfp.ini',
    )

    def __init__(self):
        """
        Load the application configuration.

        Note that this
        """
        self.managed_logger = ManagedLogger()
        self.loaded_config = configparser.RawConfigParser()
        self.loaded_config.read_dict(self.default_config)
        # Do an initial logging config to set up our formatter. On the first
        # pass, this won't load the configuration from a file.
        self.configure_logging()

        path = self.read_config_from_file()

        if path is not None:
            logger.info('Successfully loaded the configuration from %s' % (path))

        self.configure_logging()


    def read_config_from_file(self):
        for path in self.search_paths:
            if os.path.isfile(path):
                self.force_load_file(path)


    def force_load_file(self, path):
        if not os.path.isfile(path):
            logger.error("Cannot read config file: %s" % (path))

        try:
            logger.debug('Trying to open config path: %s' % (path))
            with open(path, 'r') as fp:
                self.loaded_config.read_file(fp)

            return path
        except (PermissionError, FileNotFoundError) as e:
            logger.debug('Unable to open config: %s: %s: %s' % (
                path,
                e.__class__.__name__,
                repr(e)
            ))

    def configure_logging(self):
        self.managed_logger.load_config(self.loaded_config)


    def get_config(self):
        return self.loaded_config


singleton = Config()