import logging
import signal
import threading

# from pg_dump import config, core

log = logging.getLogger(__name__)
exit_event = threading.Event()


def main():
    while not exit_event.is_set():
        # do_my_thing()
        exit_event.wait(60)
    log.info("Gracefully exited")


def exit(sig, frame):
    log.info("Interrupted by %s, shutting down" % sig)
    exit_event.set()


if __name__ == "__main__":
    signal.signal(signalnum=signal.SIGINT, handler=exit)
    signal.signal(signalnum=signal.SIGTERM, handler=exit)

    main()
