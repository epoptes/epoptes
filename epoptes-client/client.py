#!/usr/bin/python3
# This file is part of Epoptes, https://epoptes.org
# Copyright 2023 the Epoptes team, see AUTHORS.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Epoptes client class.
"""

import os
import ssl
import sys


def die(msg, code=1):
    """Print msg to stderr and exit."""
    print(msg, file=sys.stderr)
    sys.exit(code)


def require_root():
    """Exit if not root."""
    if os.getuid() != 0:
        die("Root access is required")


class Client():
    """Epoptes client class."""

    def __init__(self):
        self.server = 'server'
        self.port = 789

    def fetch_certificate(self):
        """Save server certificate to /etc/epoptes-new/server.crt"""
        cert = ssl.get_server_certificate((self.server, self.port))
        if not os.path.isdir("/etc/epoptes-new"):
            os.mkdir("/etc/epoptes-new", 0o755)
        with open("/etc/epoptes-new/server.crt", "w", encoding="utf-8") as crt:
            crt.write(cert)
        print(
            f"Saved {self.server}:{self.port} certificate to /etc/epoptes-new/server.crt")


def main():
    """Usage: epoptes-client [--version]."""
    if len(sys.argv) > 1:
        if sys.argv[1] in ("--version", "-version"):
            version = 0.1
            print(f"epoptes-client {version}")
            sys.exit(0)
        elif sys.argv[1] in ("-c"):
            client = Client()
            client.fetch_certificate()
            sys.exit(0)
    client = Client()
    client.connect()
    input("Press [Enter] to finish")


if __name__ == "__main__":
    main()
