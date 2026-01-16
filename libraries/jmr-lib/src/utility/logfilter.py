import logging

class InfoFilter(logging.Filter):
    def filter(self, record):
        # Allow only INFO-level messages
        return record.levelno == logging.INFO
    
class ErrorFilter(logging.Filter):
    def filter(self, record):
        # Allow only ERROR-level messages
        return record.levelno == logging.ERROR

class WarningFilter(logging.Filter):
    def filter(self, record):
        # Allow only WARNING-level messages
        return record.levelno == logging.WARNING