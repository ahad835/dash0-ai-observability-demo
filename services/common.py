import logging

def setup_logging(name):
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root.addHandler(h)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    return logging.getLogger(name)
