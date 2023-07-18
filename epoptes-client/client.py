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
    client = Client()
    client.fetch_certificate()


if __name__ == '__main__':
    main()
