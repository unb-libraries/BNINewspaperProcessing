#!/usr/bin/env python3
"""BNINewspaperProcessing

Manipulates and transfers scanned newspaper images in a defined workflow.

This suite is really only useful in our specific situation. If you are looking at
this project from afar, you probably do not want to use it.

New surrogate generation definition can be by creating a new '<ID>Surrogate'
module and saving it within the lib directory. The worker will automatically
import it if the surrogate type ID is requested in the SQS message.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from lib.BNIEncodingDaemon import BNIEncodingDaemon
from lib.simpleDaemon import Daemon
from optparse import OptionParser
from os import path as path
import sys


def check_options(options, parser):
    if options.action_start:
        if options.config_file is None or not path.exists(options.config_file):
            parser.print_help()
            print("\nERROR: Cannot read configuration file! (--config)")
            sys.exit(2)
    if not one_is_true(
            (
                    options.action_start,
                    options.action_stop,
            )
    ):
        parser.print_help()
        print("\nERROR: Please specify ONE of [--start, --stop]")
        sys.exit(2)


def init_options():
    option_parser = OptionParser()
    option_parser.add_option(
        "-c", "--config",
        dest="config_file",
        default='',
        help="The config file to process with.",
    )
    option_parser.add_option(
        "--start",
        dest="action_start",
        action="store_true",
        default=False,
        help="Start the encoding daemon.",
    )
    option_parser.add_option(
        "--stop",
        dest="action_stop",
        action="store_true",
        default=False,
        help="Stop the encoding daemon.",
    )
    option_parser.add_option(
        "--pidfile",
        dest="pid_filepath",
        default="/tmp/bni-worker.pid",
        help="Filepath to the PID file used in daemon (Default: /tmp/bni-worker.pid).",
    )
    option_parser.add_option(
        "--stdout",
        dest="stdout",
        default="/dev/null",
        help="Filepath to write the stdout (Default: /dev/null).",
    )
    option_parser.add_option(
        "--stderr",
        dest="stderr",
        default="/dev/null",
        help="Filepath to write the stderr (Default: /dev/null).",
    )
    (options, args) = option_parser.parse_args()
    check_options(options, option_parser)
    return options


def one_is_true(iterable):
    it = iter(iterable)
    return any(it) and not any(it)


if __name__ == "__main__":
    options = init_options()

    if options.action_stop:
        print("Stopping " + sys.argv[0])
        daemon = Daemon(
            options.pid_filepath,
        )
        daemon.stop()
    elif options.action_start:
        print("Starting " + sys.argv[0])
        daemon = BNIEncodingDaemon(
            options.pid_filepath,
            '/dev/null',
            options.stdout,
            options.stderr,
            options.config_file,
        )
        daemon.start()
    sys.exit(0)
