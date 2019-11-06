#!/usr/bin/python3
# This file is part of Epoptes, https://epoptes.org
# Copyright 2010-2018 the Epoptes team, see AUTHORS.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Create a thumbshot of the current screen.
"""
import os
import sys

import cairo

from _common import gettext as _
from gi.repository import Gdk


def thumbshot(width, height):
    """Return a thumbshot of the current screen as bytes."""
    root = Gdk.get_default_root_window()
    if root is None:
        raise RuntimeError('Cannot find the root window, is xorg running?')
    geometry = root.get_geometry()
    surface = cairo.ImageSurface(cairo.FORMAT_RGB24, width, height)
    ctx = cairo.Context(surface)
    # TODO: check if this actually does client-size resizing
    ctx.scale(float(width) / geometry.width, float(height) / geometry.height)
    Gdk.cairo_set_source_window(ctx, root, 0, 0)
    ctx.paint()

    # TODO: is a pixbuf necessary, or can we get the bytes from the surface?
    pixbuf = Gdk.pixbuf_get_from_surface(surface, 0, 0, width, height)
    rowst = pixbuf.get_rowstride()
    pixels = pixbuf.get_pixels()

    return (b"%i\n%ix%i\n" % (rowst, width, height)
            + pixels
            # TODO: the last padding isn't included, so do it manually
            + b"\0"*(rowst*height - len(pixels)))


def main():
    """Run the module from the command line."""
    if len(sys.argv) == 3:
        sys.stdout.buffer.flush()
        sys.stdout.buffer.write(thumbshot(int(sys.argv[1]), int(sys.argv[2])))
        sys.stdout.buffer.flush()
    else:
        print(_("Usage: {} width height").format(
            os.path.basename(__file__)), file=sys.stderr)
        exit(1)


if __name__ == '__main__':
    main()
