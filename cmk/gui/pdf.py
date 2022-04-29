#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Coords:
# 0,0 is at the *bottom* left of the page. When you specify
# left and top, then a larger top is nearer to the top of the
# page.

import io
import os
import subprocess
import tempfile
from textwrap import wrap
from typing import Any, List, Optional, Tuple, Union

from PIL import PngImagePlugin  # type: ignore[import]
from reportlab.lib.units import mm  # type: ignore[import]
from reportlab.lib.utils import ImageReader  # type: ignore[import]

# Import software from reportlab (thanks to them!)
from reportlab.pdfgen import canvas  # type: ignore[import]
from six import ensure_str

import cmk.utils.paths
import cmk.utils.version as cmk_version

from cmk.gui.exceptions import MKInternalError
from cmk.gui.http import response
from cmk.gui.i18n import _

RawIconColumn = Tuple[str, Optional[str]]
# TODO: ("object", ...) missing
RawTableColumn = Tuple[str, Union[str, RawIconColumn]]
RawTableRow = List[RawTableColumn]
RawTableRows = List[RawTableRow]


def from_mm(dim):
    if isinstance(dim, (int, float)):
        return dim * mm
    return [x * mm for x in dim]


# Constants used for conveniance for internal use
white = (1.0, 1.0, 1.0)
black = (0.0, 0.0, 0.0)
green = (0.4, 1.0, 0.4)
yellow = (1.0, 1.0, 0.0)
orange = (1.0, 0.6, 0.3)
red = (1.0, 0.4, 0.4)
blue = (0.4, 0.6, 1.0)
gray = (0.5, 0.5, 0.5)
lightgray = (0.8, 0.8, 0.8)

# Note: these are monitoring specific colors. They do really not belong
# here.
css_class_colors = {
    "up": green,
    "down": red,
    "unreach": orange,
    "pending": lightgray,
    "ok": green,
    "warn": yellow,
    "crit": red,
    "unknown": orange,
    "hstate0": green,
    "hstate1": red,
    "hstate2": red,
    "hstatep": lightgray,
    "state0": green,
    "state1": yellow,
    "state2": red,
    "state3": orange,
    "statep": lightgray,
    "downtime": blue,
    "unmonitored": lightgray,
    "hostdown": (0.2, 0.3, 0.8),
    "flapping": (1.0, 0.0, 1.0),
    "ooservice": (0.8, 0.8, 0.8),
    "chaos": (0.5, 0.3, 1.0),
}


# Make a color darker. v ranges from 0 (not darker) to 1 (black)
def darken_color(rgb, v):
    def darken(x, v):
        return x * (1.0 - v)

    return tuple(darken(x, v) for x in rgb)


# Make a color lighter. v ranges from 0 (not lighter) to 1 (white)
def lighten_color(rgb, v):
    def lighten(x, v):
        return 1.0 - ((1.0 - x) * (1.0 - v))

    return tuple(lighten(x, v) for x in rgb)


# All dimensions that the user (caller) uses are in mm. All our internal
# state variables are in the native PDF dimension, which is convered by
# reportlab.lib.units.mm. The function from_mm convert from user-style into
# internal-style. In a later version we could have the user himself decide
# about the unit he wants to use.


class Document:
    def __init__(self, **args):
        # Static paper settings for this document
        self._pagesize = from_mm(args["pagesize"])
        self._margins = from_mm(args["margins"])
        self._mirror_margins = args["margins"]
        self._pagebreak_function = args.get("pagebreak_function")
        self._pagebreak_arguments = args.get("pagebreak_arguments", [])

        # set derived helper variables (all in pt)
        self._width, self._height = self._pagesize
        self._height = self._pagesize[1]

        self._margin_top, self._margin_right, self._margin_bottom, self._margin_left = self._margins

        self._inner_width = self._width - self._margin_left - self._margin_right
        self._inner_height = self._height - self._margin_top - self._margin_bottom
        self._left = self._margin_left
        self._right = self._width - self._margin_right
        self._top = self._height - self._margin_top
        self._bottom = self._margin_bottom

        # create PDF document
        self._output_buffer = io.BytesIO()
        self._canvas = canvas.Canvas(self._output_buffer, pagesize=self._pagesize)
        self._heading_entries = []

        # initialize our page state
        self._page_number = 1
        self._tabstops = []
        self._heading_numbers = {}
        # The level number of the last added heading
        self._heading_level = 0
        # Increase all future added headings by this level offset
        self._heading_level_offset = 0
        self._linepos = self._top  # current vertical cursor position

        # Create initial graphics state, i.e. all style settings,
        # that can change while the document is being rendered. We keep a stack
        # a graphics states to that can be pushed and from that can be pulled.
        self._gfx_state = {
            "font_family": args["font_family"],
            "font_size": args["font_size"],  # pt
            "font_zoom_factor": 1.0,
            "line_width": 0.05 * mm,
            "line_height": args["lineheight"],  # in relation to font_size
            "fill_color": black,
            "dashes": [],
            "line_color": black,
            "bold": False,
            "tt": False,
            "heading_offset": 0,
        }
        self._gfx_state_stack = []
        self.set_gfx_state()

    def end(self, sendas=None, do_send=True):
        self._canvas.showPage()
        self._canvas.save()
        pdf_source = self._output_buffer.getvalue()
        self._output_buffer.close()

        if do_send:
            Document.send(pdf_source, sendas)
        else:
            return pdf_source

    @classmethod
    def send(cls, pdf_source, sendas):
        # ? sendas seems to be used with type str
        response.set_content_type("application/pdf")
        response.headers[
            "Content-Disposition"
        ] = "inline; filename=" + ensure_str(  # pylint: disable= six-ensure-str-bin-call
            sendas
        )
        response.set_data(pdf_source)

    # Methods dealing with manipulating the graphics state (font size, etc.)

    def save_state(self):
        self._gfx_state_stack.append(self._gfx_state.copy())
        self._canvas.saveState()  # needed for clip rect

    def restore_state(self):
        # Problem here: After a page break the internal state stack
        # of the canvas object is cleared. But page breaks can happen
        # at many places implicitely! Calling restoreState() with a
        # cleared state stack will first write a state pop command into
        # the PDF and *then* raise an exception. So even if we catch
        # the exception the PDF will be inconsistent.
        if self._canvas.state_stack:
            self._canvas.restoreState()  # needed for clip rect
        self._gfx_state = self._gfx_state_stack.pop()
        self.set_gfx_state()

    # Private function for making all graphics settings active. We could
    # optimizie this by only changing the attributes actually being modified,
    # but the use of that is probably neglectable.
    def set_gfx_state(self):
        s = self._gfx_state
        self._canvas.setFillColorRGB(*s["fill_color"])
        self._canvas.setStrokeColorRGB(*s["line_color"])
        self._canvas.setLineWidth(s["line_width"])
        if s["dashes"]:
            self._canvas.setDash(*s["dashes"])
        else:
            self._canvas.setDash([])
        if s["tt"]:
            family = "Courier"
        else:
            family = s["font_family"]
        if s["bold"]:
            family += "-Bold"
        if family == "Times":
            family += "-Roman"
        self._canvas.setFont(family, s["font_size"] * s["font_zoom_factor"])

    def set_font_bold(self, b=True):
        self._gfx_state["bold"] = b
        self.set_gfx_state()

    def set_font_tt(self, tt=True):
        self._gfx_state["tt"] = tt
        self.set_gfx_state()

    def set_font_zoom(self, zoom):
        self._gfx_state["font_zoom_factor"] = zoom
        self.set_gfx_state()

    def set_font_size(self, s):
        self._gfx_state["font_size"] = s
        self.set_gfx_state()

    def get_font_size(self):
        return self._gfx_state["font_size"]

    def set_line_width(self, w):
        self._gfx_state["line_width"] = w * mm
        self.set_gfx_state()

    def set_dashes(self, dashes):
        self._gfx_state["dashes"] = [d * mm for d in dashes]
        self.set_gfx_state()

    def set_fill_color(self, color):
        self._gfx_state["fill_color"] = color
        self.set_gfx_state()

    def set_line_color(self, color):
        self._gfx_state["line_color"] = color
        self.set_gfx_state()

    def set_font_color(self, color):
        self._gfx_state["fill_color"] = color
        self._gfx_state["line_color"] = color
        self.set_gfx_state()

    def get_heading_level(self):
        return self._heading_level

    def set_heading_level_offset(self, level):
        self._gfx_state["heading_offset"] = level
        self.set_gfx_state()

    # Page handling
    def page_number(self):
        return self._page_number

    def next_page(self):
        self._canvas.showPage()
        self._linepos = self._top
        self._page_number += 1
        if self._mirror_margins:
            self._margin_left, self._margin_right = self._margin_right, self._margin_left
            self._left = self._margin_left
            self._right = self._width - self._margin_right

    def need_pagebreak(self, needed_space=0.0):
        """Whether or not a page break would help to make the element be rendered as a whole
        on the next page. In case the break would not solve the situation (e.g. when the
        element is higher than the available space on a single page, then let it be."""
        if not self.fits_on_empty_page(needed_space):
            return False

        return not self.fits_on_remaining_page(needed_space)

    def fits_on_remaining_page(self, needed_space: float) -> bool:
        """Is the needed_space left free on the current page?"""
        return self._linepos - needed_space * mm > self._bottom

    def fits_on_empty_page(self, needed_space: float) -> bool:
        """Is the needed_space sufficient on an empty page?"""
        return needed_space * mm <= self._inner_height

    def check_pagebreak(self, needed_space=0.0):
        if self.need_pagebreak(needed_space):
            self.do_pagebreak()

    def do_pagebreak(self):
        self.next_page()
        if self._pagebreak_function:
            self._pagebreak_function(*self._pagebreak_arguments)

    # Functions for direct rendering at absolut places of the page. All positions
    # are specified in a top level way and consider page borders:

    # Examples for positions:
    # ( "w", 10.0 )     10 mm from left,   vertically centered
    # ( "s", 10.0 )     10 mm from bottom, horizontally centered
    # ( "ne", (5, 7) )  5 mm from top, 7 mm from right
    # "c"               At the center
    # Returns the choords of the top left corner of the element (left, top)
    def convert_position(self, position, el_width, el_height):
        h_center = self._left + (self._right - self._left) / 2.0 - el_width / 2.0
        v_center = self._bottom + (self._top - self._bottom) / 2.0 - el_height / 2.0

        if position == "c":
            return h_center, v_center
        anchor = position[0]
        if len(anchor) == 1:  # s, n, w, e
            offset = position[1] * mm
            if anchor == "n":
                return h_center, self._top - offset
            if anchor == "s":
                return h_center, self._bottom + offset + el_height
            if anchor == "w":
                return self._left + offset, v_center
            if anchor == "e":
                return self._right - offset - el_width, v_center

        else:  # nw, sw, ne, se
            h_offset = position[1][0] * mm
            v_offset = position[1][1] * mm
            if anchor[0] == "n":
                y = self._top - v_offset - el_height
            else:
                y = self._bottom + v_offset
            if anchor[1] == "w":
                x = self._left + h_offset
            else:
                x = self._right - h_offset - el_width
            return x, y

    def place_hrule(self, position, width=0.05, color=None):
        el_width = self._right - self._left
        el_height = width * mm
        l, t = self.convert_position(position, el_width, el_height)
        self.save_state()
        if color:
            self.set_fill_color(color)
        self._canvas.rect(l, t, el_width, el_height, fill=1, stroke=0)
        self.restore_state()

    def place_text(self, position, text):
        el_height = self._gfx_state["font_size"] * self._gfx_state["font_zoom_factor"]
        el_width = self._canvas.stringWidth(text)
        l, t = self.convert_position(position, el_width, el_height)
        self._canvas.drawString(l, t + el_height * 0.22, text)  # Try to move to correct Y position
        # Debug the text bounding box
        # self._canvas.rect(l, t, el_width, el_height, fill=0)

    def place_text_lines(self, position, lines):
        el_height = self._gfx_state["font_size"] * self._gfx_state["font_zoom_factor"] * len(lines)
        el_width = max(self._canvas.stringWidth(l) for l in lines) if lines else 0

        l, t = self.convert_position(position, el_width, el_height)

        for num, line in enumerate(lines):
            # Try to move to correct Y position
            self._canvas.drawString(l, (t + el_height * 0.66) - (el_height * 0.5 * num), line)
            # Debug the text bounding box
            # self._canvas.rect(l, t - el_height * 0.5 * num, el_width, el_height, fill=0)

    def place_page_box(self):
        self.save_state()
        self.set_line_width(0.1)
        self.set_line_color(black)
        self._canvas.rect(self._left, self._bottom, self._inner_width, self._inner_height, fill=0)
        self.restore_state()

    def place_pil_image(self, position, pil, width_mm, height_mm, resolution):
        width, height = self.get_image_dimensions(pil, width_mm, height_mm, resolution)
        x, y = self.convert_position(position, width, height)
        ir = ImageReader(pil)
        self._canvas.drawImage(ir, x, y - height, width, height, mask="auto")

    # Functions for adding floating text

    def add_paragraph(self, txt):
        lines = self.wrap_text(txt, width=(self._right - self._left))
        for line in lines:
            self.add_text_line(line)

    def debug(self, *args):
        for arg in args:
            self.add_paragraph(repr(arg))

    def add_heading(self, level, text, numbers):
        level = self._gfx_state["heading_offset"] + level

        next_number = self._heading_numbers.get(level, 0) + 1
        self._heading_numbers[level] = next_number
        self._heading_level = level

        for lev in self._heading_numbers:
            if lev > level:
                self._heading_numbers[lev] = 0

        if numbers:
            numparts = [self._heading_numbers.get(l, 1) for l in range(1, level + 1)]
            heading = ".".join(map(str, numparts))
            if level == 1:
                heading += "."
            heading += " " + text
        else:
            heading = text

        self.add_margin(7)
        if level == 1:
            self.add_margin(5)

        zoom = {
            1: 1.8,
            2: 1.5,
            3: 1.2,
        }.get(level, 1.0)

        self.save_state()
        self.set_font_zoom(zoom)
        self.set_font_bold()
        self.advance(self.lineskip())
        self._canvas.drawString(self._left, self._linepos, heading)
        self._heading_entries.append((heading, self.page_number()))
        self.advance(self.lineskip() / 2.0)
        self.restore_state()

    # Add vertical white space, skip. If that does not fit onto the current
    # page, then make a page break and *do not* skip!
    def add_margin(self, height=None, force=False):
        if height is not None:
            marg = height * mm
        else:
            marg = self.lineskip()

        if self.need_pagebreak(marg):
            self.do_pagebreak()
        else:
            self.margin(marg, force)

    def add_hrule(self, margin=0.1, width=0.05, color=None):
        self._linepos -= margin * mm
        self.save_state()
        self.set_line_width(width)
        if color:
            self.set_line_color(color)
        else:
            self.set_line_color(black)
        self._canvas.line(self._left, self._linepos, self._right, self._linepos)
        self._linepos -= margin * mm
        self.restore_state()

    def add_pil_image(self, pil, width, height, resolution=None, border=True):
        width, height = self.get_image_dimensions(pil, width, height, resolution)

        self.advance(height)
        x = self._left + (self._inner_width - width) / 2.0  # center
        y = self._linepos
        ir = ImageReader(pil)
        self._canvas.drawImage(ir, x, y, width, height, mask="auto")
        if border:
            self._canvas.rect(x, y, width, height, fill=0)

    # Add space for a rectangular drawing area where the user can draw
    # himself using render_...() functions. Makes sure that this area
    # is completely contained on one page. Skips to the next page if
    # the current page is too full. Returns left, top, width and height
    # of the actually allocated canvas in mm.
    def add_canvas(self, width_mm, height_mm, border_width=0, left_mm=None):
        self.advance(height_mm * mm)

        if left_mm is None:
            left = self._margin_left
        else:
            left = left_mm * mm

        right = left + width_mm * mm
        bottom = self._linepos
        top = bottom + height_mm * mm

        if border_width:
            self.save_state()
            self.set_line_width(border_width * mm)
            self._canvas.rect(left, bottom, right - left, top - bottom, fill=0, stroke=1)
            self.restore_state()

        return left / mm, top / mm, (right - left) / mm, (top - bottom) / mm  # fixed: true-division

    # Add one line of text. This line may include horizontal tabulators ('\t').
    # You can set the width of the tabulators with set_tabstops()
    def add_text_line(self, l, bold=False):
        self.check_pagebreak()

        def aligned_string(x, y, t, alignment):
            if alignment == "l":
                self._canvas.drawString(x, y, t)
            elif alignment == "r":
                self._canvas.drawRightString(x, y, t)
            else:
                self._canvas.drawCentredString(x, y, t)

        l = l.strip(" ")
        self._linepos -= self.lineskip()
        tab = -1

        for part in l.split("\t"):
            self.save_state()

            if tab >= 0:
                format_chars, x_position = self._tabstops[tab]  # added extra tab stop every 20 mm
                if "b" in format_chars:
                    self.set_font_bold(True)
                if "t" in format_chars:
                    self.set_font_tt(True)
                if "g" in format_chars:
                    self.set_font_color(gray)
                if "r" in format_chars:
                    alignment = "r"
                elif "c" in format_chars:
                    alignment = "c"
                else:
                    alignment = "l"

                # Negative values are interpreted as offset from the right border
                if x_position < 0:
                    x_position = self._right - x_position
            else:
                x_position = 0
                alignment = "l"
            tab += 1
            abs_x = self._left + x_position
            abs_y = (
                self._linepos
                + (self._gfx_state["font_size"] * self._gfx_state["font_zoom_factor"]) * 0.2
            )
            aligned_string(abs_x, abs_y, part, alignment)
            self.restore_state()

    def set_tabstops(self, tabstops: List[Union[int, float, str]]) -> None:
        # t is a list of tab stops. Each entry is either an int
        # or float -> tabstop in mm. Or it is a string that has
        # prefix of characters followed by a number (mm). The
        # characters specify alignment and font style. We convert
        # all this here to a pair ( "bc", 17.2 ) of the alignment
        # characters and the tabstop in *internal* dimensions.
        def convert_tabstop(t):
            if isinstance(t, (int, float)):
                return "", float(t) * mm
            if isinstance(t, str):
                formatchars = ""
                while not t[0].isdigit():
                    formatchars += t[0]
                    t = t[1:]
                return formatchars, float(t) * mm
            raise ValueError("invalid tab stop %r" % t)

        self._tabstops = list(map(convert_tabstop, tabstops))

    def clear_tabstops(self):
        self._tabstops = []

    def wrap_text(self, text, width, wrap_long_words=True):  # width in internal dimension
        # The Python STL wrapper works on characters, in pdf we have fonts
        # of different size and they are not monospaced. We take the
        # character length average to normalize to font size
        if text.strip() == "":
            return ""
        char_avg = self._canvas.stringWidth(text) / len(text)
        return wrap(text, max(1, int(width / char_avg)), break_long_words=wrap_long_words)

    def add_table(
        self,
        header_texts: Any,
        raw_rows: Any,
        font_size: RawTableRows,
        show_headings: Any,
        padding: Any,
        spacing: Any,
        hrules: Any,
        vrules: Any,
        rule_width: Any,
        row_shading: Any,
        respect_narrow_columns: bool = True,
    ) -> None:
        TableRenderer(self).add_table(
            header_texts,
            raw_rows,
            font_size,
            show_headings,
            padding,
            spacing,
            hrules,
            vrules,
            rule_width,
            row_shading,
            respect_narrow_columns,
        )

    # Lowlevel functions for direct rendering into the page. Dimensions are in
    # mm. Positions are from the top left of the physical page. These functions
    # are e.g. being used in the render functions of Perf-O-Meters.

    def render_text(self, left_mm, top_mm, text, align="left", bold=False, color=black):
        self.save_state()
        self.set_font_bold(bold)
        self.set_font_color(color)
        if align == "left":
            self._canvas.drawString(left_mm * mm, top_mm * mm, text)
        elif align == "right":
            self._canvas.drawRightString(left_mm * mm, top_mm * mm, text)
        else:
            self._canvas.drawCentredString(left_mm * mm, top_mm * mm, text)
        self.restore_state()

    def render_image(self, left_mm, top_mm, width_mm, height_mm, path):
        pil = PngImagePlugin.PngImageFile(fp=path)
        ir = ImageReader(pil)
        try:
            self._canvas.drawImage(
                ir, left_mm * mm, top_mm * mm, width_mm * mm, height_mm * mm, mask="auto"
            )
        except Exception as e:
            raise Exception("Cannot render image %s: %s" % (path, e))

    def get_line_skip(self):
        return self.lineskip() / mm  # fixed: true-division

    def text_width(self, text):
        return self._canvas.stringWidth(text) / mm  # fixed: true-division

    # TODO: unify with render_text()
    def render_aligned_text(
        self,
        left_mm,
        top_mm,
        width_mm,
        height_mm,
        text,
        align="center",
        valign="bottom",
        bold=False,
        color=None,
    ):
        if color or bold:
            self.save_state()

        if color:
            self.set_font_color(color)

        if bold:
            self.set_font_bold()

        ex_height = self.font_height_ex()
        top = top_mm * mm + (height_mm * mm - ex_height) / 2.0
        if valign == "middle":
            top -= ex_height * 0.5  # estimate
        if align == "center":
            self._canvas.drawCentredString((left_mm + width_mm / 2.0) * mm, top, text)
        elif align == "left":
            self._canvas.drawString(left_mm * mm, top, text)
        elif align == "right":
            self._canvas.drawRightString((left_mm + width_mm) * mm, top, text)

        if color or bold:
            self.restore_state()

    def render_rect(
        self,
        left_mm,
        top_mm,
        width_mm,
        height_mm,
        line_width=None,
        line_color=None,
        fill_color=None,
    ):
        self.save_state()

        # Default to unfilled rect with fine black outline
        if line_color is None and fill_color is None and line_width is None:
            line_width = 0.05

        if line_width is not None and line_color is None:
            line_color = black

        if line_width:
            self.set_line_width(line_width)
        if line_color:
            self.set_line_color(line_color)
        if fill_color:
            self.set_fill_color(fill_color)

        self._canvas.rect(
            left_mm * mm,
            top_mm * mm,
            width_mm * mm,
            height_mm * mm,
            fill=fill_color and 1 or 0,
            stroke=(line_color or line_width) and 1 or 0,
        )

        self.restore_state()

    def render_line(
        self, left1_mm, top1_mm, left2_mm, top2_mm, width=0.05, color=black, dashes=None
    ):
        self.save_state()
        self.set_line_width(width)
        self.set_line_color(color)
        if dashes:
            self.set_dashes(dashes)
        self._canvas.line(left1_mm * mm, top1_mm * mm, left2_mm * mm, top2_mm * mm)
        self.restore_state()

    # Access to paths
    def begin_path(self):
        self._path = self._canvas.beginPath()

    def move_to(self, left, top):
        self._path.moveTo(left * mm, top * mm)

    def line_to(self, left, top):
        self._path.lineTo(left * mm, top * mm)

    def close_path(self):
        self._path.close()

    def fill_path(self, color, gradient=None):
        self.save_state()

        # The gradient is dramatically increasing the size of the PDFs. For example a PDF with
        # 10 graphs has a size of 6 MB with gradients compared to 260 KB without gradients!
        # It may look better, but that's not worth it.
        #
        # Older versions of reportlab do not support gradients
        # try:
        #    self._canvas.linearGradient
        # except:
        #    gradient = None

        # if gradient:
        #    grad_left, grad_top, grad_width, grad_height, color_range, switch_points = gradient
        #    self._canvas.saveState()
        #    self._canvas.clipPath(self._path, stroke=0)
        #    self._canvas.linearGradient(grad_left * mm, grad_top * mm, grad_width * mm, grad_height * mm,
        #                                color_range, switch_points, extend=False)
        #    self._canvas.restoreState()
        # else:
        self.set_fill_color(color)
        self._canvas.drawPath(self._path, stroke=0, fill=1)

        self.restore_state()

    def stroke_path(self, color=black, width=0.05):
        self.save_state()
        self.set_line_color(color)
        self.set_line_width(width * mm)
        self._canvas.drawPath(self._path, stroke=1, fill=0)
        self.restore_state()

    def add_clip_rect(self, left, top, width, height):
        clip_path = self._canvas.beginPath()
        clip_path.moveTo(left * mm, top * mm)
        clip_path.lineTo(left * mm + width * mm, top * mm)
        clip_path.lineTo(left * mm + width * mm, top * mm + height * mm)
        clip_path.lineTo(left * mm, top * mm + height * mm)
        clip_path.lineTo(left * mm, top * mm)
        clip_path.close()
        self._canvas.clipPath(clip_path, stroke=0)

    # Internal functions

    # Compute the absolute distance between two lines
    def lineskip(self):
        return (
            self._gfx_state["line_height"]
            * self._gfx_state["font_zoom_factor"]
            * self._gfx_state["font_size"]
        )

    # Estimate the height of a one-line text
    def font_height_ex(self):
        return self._canvas.stringWidth("M") * 1

    def font_height(self):
        return self.font_height_ex() / mm  # fixed: true-division

    def advance(self, l):
        if self._linepos - l < self._bottom:
            self.do_pagebreak()
            self._linepos = max(self._bottom, self._linepos - l)
        else:
            self._linepos -= l

    # Current vertical position of cursor
    def line_pos(self):
        return self._linepos / mm  # fixed: true-division

    def left(self):
        return self._left / mm  # fixed: true-division

    def right(self):
        return self._right / mm  # fixed: true-division

    def width(self):
        return self.right() - self.left()

    # Insert a vertical margin of m. If this leads to a page
    # break then do *not* insert that margin at the top of the new
    # page. Also do not insert that margin if we are already at the
    # top of the page. But: you can force the margin
    def margin(self, m, force=False):
        if self._linepos != self._top or force:
            self._linepos -= m
            if self._linepos < self._bottom:
                self.do_pagebreak()

    def rect(self, x, y, width, height, color):
        self.save_state()
        self.set_fill_color(color)
        self._canvas.rect(x, y, width, height, fill=1, stroke=0)
        self.restore_state()

    # Get and compute image dimensions, convert from mm. If resolution
    # is set, then width and height are being ignored.
    def get_image_dimensions(self, pil, width_mm, height_mm, resolution_dpi=None):
        # Get bounding box of image in order to get aspect (width / height)
        bbox = pil.getbbox()
        pix_width, pix_height = bbox[2], bbox[3]
        if resolution_dpi is not None:
            resolution_mm = resolution_dpi / 2.45
            resolution_pt = resolution_mm / mm  # now we have pixels / pt # fixed: true-division
            width = pix_width / resolution_pt  # fixed: true-division
            height = pix_height / resolution_pt  # fixed: true-division
        else:
            aspect = float(pix_width) / float(pix_height)
            # Both are unset, and no resolution: scale to inner width
            if width_mm is None and height_mm is None:
                width = self._right - self._left
                height = width / aspect  # fixed: true-division
            else:  # At least one known
                if width_mm is not None:
                    width = width_mm * mm
                if height_mm is not None:
                    height = height_mm * mm
                if width_mm is None:
                    width = height * aspect
                elif height_mm is None:
                    height = width / aspect  # fixed: true-division
        return width, height


class TableRenderer:
    """Intelligent table rendering with word wrapping and pagination"""

    def __init__(self, pdf: Document) -> None:
        super().__init__()
        self.pdf = pdf

    def add_table(
        self,
        header_texts: Any,
        raw_rows: Any,
        font_size: RawTableRows,
        show_headings: Any,
        padding: Any,
        spacing: Any,
        hrules: Any,
        vrules: Any,
        rule_width: Any,
        row_shading: Any,
        respect_narrow_columns: bool,
    ) -> None:
        self.pdf.save_state()
        self.pdf.set_font_size(font_size)

        rule_width *= mm
        x_padding, y_padding = from_mm(padding)
        x_spacing, y_spacing = from_mm(spacing)
        if not show_headings:
            header_texts = []

        # The implementation of x_spacing and y_spacing was totally broken. Dropping this feature
        # for the moment.
        # TODO: Clarify the reason why it is here.
        x_spacing = 0
        y_spacing = 0

        if header_texts:
            num_cols = len(header_texts)
        elif raw_rows:
            num_cols = len(raw_rows[0])
        else:
            return  # No headers, empty table. Nothing to show

        # Convert the header and the rows into special renderable objects. Such
        # an object defines functions for handling size and rendering itself.
        # Currently there are three types of entries allowed:
        # 1. ( "icon", "/omd/.../path/to/icon.png" ) --> an image
        # 2. ( "object", ObjectThing               ) --> aleady render object
        # 3. "Some text"
        # Note: Regardless of the type, everything is embedded in a pair of
        # css and the thing, e.g.
        # ( "number", "0.75" ), or ("", ("icon", "/bar/foo.png") )
        # The headers come *without* the css field and are always texts.
        headers: List[Union[TextCell, IconCell]] = [
            TitleCell("heading", header_text) for header_text in header_texts  #
        ]

        rows: List[List[Union[TextCell, IconCell]]] = []
        for raw_row in raw_rows:
            row: List[Union[TextCell, IconCell]] = []
            rows.append(row)
            for css, entry in raw_row:
                if isinstance(entry, tuple):
                    if entry[0] == "icon":
                        row.append(IconCell(entry[1]))
                    elif entry[0] == "object":
                        row.append(entry[1])
                    else:
                        raise Exception("Invalid table entry %r in add_table()" % entry)
                elif css == "leftheading":
                    row.append(TitleCell(css, entry))
                else:
                    row.append(TextCell(css, entry))

        # Now we balance the widths of the columns. Each render object has an
        # absolute minimum width (e.g. the width of the longest word) and
        # a maximum width (e.g. the length of the unwrapped text). All dimensions
        # are in internal units (not mm).
        # TODO: Abusing a heterogeneous list as a product type is horrible!
        stats = [[0, 0.0, 0.0, 0.0, None, True] for _c in range(num_cols)]

        # Ease the typing pain a tiny bit... :-P
        def _get_number(s, idx):
            c = s[idx]
            if c is None:
                raise ValueError("something went wrong in add_table...")
            return c

        hurz: List[List[Union[TextCell, IconCell]]] = [headers] if headers else []
        for row in hurz + rows:
            for col, render_object in enumerate(row):
                max_width = render_object.maximal_width(self.pdf) * mm
                min_width = render_object.minimal_width(self.pdf) * mm

                if respect_narrow_columns:
                    is_dynamic = render_object.can_add_dynamic_width()
                else:
                    is_dynamic = True

                # TODO: indexes 0 (row count), 1 (total width)
                #       -> drop them?
                stats[col][0] = _get_number(stats[col], 0) + 1
                stats[col][1] = _get_number(stats[col], 1) + max_width
                stats[col][2] = max(min_width, stats[col][2])
                stats[col][3] = max(max_width, stats[col][3])

                if not is_dynamic:
                    stats[col][5] = False

        # Compute required total width
        sum_min = sum([s[2] for s in stats if s[2] is not None])

        # Now compute the available width, i.e. take the usable page width
        # and substract spacing and padding.
        available_width = (
            self.pdf._inner_width - ((num_cols - 1) * x_spacing) - (num_cols * 2 * x_padding)
        )

        # If there is space enough for not breaking single words, then
        # we begin with giving each column the width of their maximal
        # word. The rest is then distributed such that each column gets
        # the space from the rest that is related to its non-wrapping-width.
        # Columns with can_add_dynamic_width() == False will not take
        # part in the remaining-space-distribution

        if sum_min <= available_width:
            remaining = available_width - sum_min
            sum_weight = 0
            for s in stats:
                _row_count, _total_width, min_width, max_width, _weight, is_dynamic = s
                if is_dynamic:
                    weight = (
                        max_width - min_width + 1 * mm
                    )  # add 1mm in order to avoid zero weights
                    s[4] = weight
                    sum_weight += weight
                else:
                    s[4] = 0

            column_widths = []
            for _row_count, _total_width, min_width, max_width, weight, is_dynamic in stats:
                if sum_weight > 0:
                    width = min_width + (weight / sum_weight * remaining)  # fixed: true-division
                else:
                    width = min_width
                column_widths.append(width)

        # Not enough space for even printing the table without breaking
        # words in half. Divide space according to sum_max.
        else:
            sum_weight = 0
            for s in stats:
                if s[0]:
                    weight = _get_number(s, 1) / _get_number(s, 0)  # fixed: true-division
                else:
                    weight = 0
                sum_weight += weight
                s[4] = weight

            column_widths = []
            for s in stats:
                width = available_width * s[4] / sum_weight  # fixed: true-division
                column_widths.append(width)

        row_oddeven = "even"
        for row_index, row in enumerate(rows):
            row_oddeven = "odd" if row_oddeven == "even" else "even"

            if self._paint_graph_row(
                row,
                column_widths,
                y_padding,
                x_padding,
                y_spacing,
                x_spacing,
                headers,
                hrules,
                vrules,
                rule_width,
                row_shading,
                paint_header=row_index == 0,
                row_oddeven=row_oddeven,
            ):
                continue

            self._paint_row(
                row,
                column_widths,
                y_padding,
                x_padding,
                y_spacing,
                x_spacing,
                headers,
                hrules,
                vrules,
                rule_width,
                row_shading,
                paint_header=row_index == 0,
                is_header=False,
                row_oddeven=row_oddeven,
            )

        self.pdf.restore_state()

    def _paint_headers(
        self,
        headers,
        column_widths,
        y_padding,
        x_padding,
        y_spacing,
        x_spacing,
        hrules,
        vrules,
        rule_width,
        row_shading,
    ):
        self._paint_hrule(hrules, rule_width)
        if headers:
            self._paint_row(
                headers,
                column_widths,
                y_padding,
                x_padding,
                y_spacing,
                x_spacing,
                headers,
                hrules,
                vrules,
                rule_width,
                row_shading,
                paint_header=False,
                is_header=True,
                row_oddeven="heading",
            )

    def _paint_row(
        self,
        row,
        column_widths,
        y_padding,
        x_padding,
        y_spacing,
        x_spacing,
        headers,
        hrules,
        vrules,
        rule_width,
        row_shading,
        paint_header: bool,
        is_header: bool,
        row_oddeven: str,
    ):
        # Give each cell information about its final width so it can reorganize internally.
        # This is used for text cells that do the wrapping.
        for column_width, render_object in zip(column_widths, row):
            render_object.set_width(self.pdf, column_width)

        # Now - after the text-wrapping - we know the maximum height of all cells
        # a in row and can decide whether it fits on the current page.
        if row:
            row_height = max([render_object.height(self.pdf) * mm for render_object in row])
        else:
            row_height = self.pdf.lineskip()

        needed_vspace = row_height + 2 * y_padding + y_spacing

        if not self.pdf.fits_on_remaining_page(needed_vspace / mm) and self.pdf.fits_on_empty_page(
            needed_vspace / mm
        ):
            self.pdf.do_pagebreak()
            paint_header = True

        if not is_header and paint_header:
            self._paint_headers(
                headers,
                column_widths,
                y_padding,
                x_padding,
                y_spacing,
                x_spacing,
                hrules,
                vrules,
                rule_width,
                row_shading,
            )

        # Apply row shading
        if row_shading["enabled"]:
            h = (row_height + 2 * y_padding) / mm  # fixed: true-division
            self.pdf.render_rect(
                self.pdf._left / mm,  # fixed: true-division
                self.pdf._linepos / mm - h,  # fixed: true-divisioin
                self.pdf._inner_width / mm,  # fixed: true-division
                h,
                fill_color=row_shading[row_oddeven],
            )

        # Finally paint
        left = self.pdf._left
        for column_width, render_object in zip(column_widths, row):
            old_linepos = self.pdf._linepos
            render_object.render(
                self.pdf,
                left / mm,
                self.pdf._linepos / mm,  # fixed: true-division
                column_width / mm + 2 * x_padding / mm,  # fixed: true-division
                (row_height + 2 * y_padding) / mm,
                x_padding / mm,  # fixed: true-division
                y_padding / mm,  # fixed: true-division
                row_oddeven if row_shading["enabled"] else None,
            )

            self.pdf._linepos = old_linepos

            self._paint_vrule(rule_width, y_padding, row_height, vrules, left)
            left += column_width + 2 * x_padding + x_spacing
        self._paint_vrule(rule_width, y_padding, row_height, vrules, left)
        self.pdf.advance(needed_vspace - y_spacing / 2.0)
        self._paint_hrule(hrules, rule_width)
        self.pdf.advance(y_spacing / 2.0)

    def _paint_hrule(self, hrules, rule_width):
        if hrules:
            self.pdf.add_hrule(width=rule_width / mm, margin=0)  # fixed: true-division

    def _paint_vrule(self, rule_width, y_padding, row_height, vrules, left):
        if vrules:
            self.pdf._canvas.setLineWidth(rule_width)
            self.pdf._canvas.setStrokeColorRGB(*black)
            self.pdf._canvas.line(
                left, self.pdf._linepos, left, self.pdf._linepos - row_height - 2 * y_padding
            )

    def _paint_graph_row(
        self,
        row,
        column_widths,
        y_padding,
        x_padding,
        y_spacing,
        x_spacing,
        headers,
        hrules,
        vrules,
        rule_width,
        row_shading,
        paint_header: bool,
        row_oddeven: str,
    ) -> bool:
        """Paint special form of graph rows

        Special hack for single dataset views displaying a graph columns which need more than 1 page
        in total. Even if this may affect also other column types, these are the columns which are
        most likely to span over multiple pages even in standard situations.

        We explicitly only care about single dataset views (1st column: header, 2nd: data) or the
        views that show only a single data column with the headers above. However, for a generic
        solution we should drop the approach of trying to build our own table rendering solution and
        find something more battle tested.
        """
        if cmk_version.is_raw_edition():
            return False

        # This import hack is needed because this module is part of the raw edition while
        # the PainterPrinterTimeGraph class is not (also we don't have a base class
        # available in CRE to use instead).
        # pylint: disable=no-name-in-module
        from cmk.gui.cee.plugins.reporting.pnp_graphs import PainterPrinterTimeGraph

        is_single_dataset = (
            len(row) == 2
            and isinstance(row[0], TitleCell)
            and isinstance(row[1], PainterPrinterTimeGraph)
        )
        is_single_column = len(row) == 1 and isinstance(row[0], PainterPrinterTimeGraph)

        if not is_single_dataset and not is_single_column:
            return False

        graph_column = row[-1]
        assert isinstance(graph_column, PainterPrinterTimeGraph)

        if self.pdf.fits_on_remaining_page(graph_column.height(self) * mm):
            return False

        if self.pdf.fits_on_empty_page(graph_column.height(self) * mm):
            return False

        for index, step in enumerate(graph_column.get_render_steps(self.pdf, headers, y_padding)):
            if is_single_dataset:
                step_row = [row[0] if index == 0 else TitleCell("lefheading", ""), step]
            else:
                step_row = [step]

            self._paint_row(
                step_row,
                column_widths,
                y_padding,
                x_padding,
                y_spacing,
                x_spacing,
                headers,
                hrules,
                vrules,
                rule_width,
                row_shading,
                paint_header=paint_header and index == 0,
                is_header=False,
                row_oddeven=row_oddeven,
            )
        return True


# Note: all dimensions this objects handles with are in mm! This is due
# to the fact that this API is also available externally
class TextCell:
    def __init__(self, csses, text):
        self._text = text
        self._bold = False
        self._color = black
        self._bg_color = white
        self._alignment = "left"

        if csses is None:
            csses = ""

        # TODO: Sollte das nicht lieber raus aus dem allgemeinen pdf.py? Ist eigentlich
        # Spezifisch für Views, etc.
        if "heading" in csses or "state" in csses:
            self._bold = True

        if "number" in csses:
            self._alignment = "right"

        if "unused" in csses:
            self._color = (0.6, 0.6, 0.6)

        elif "leftheading" in csses:
            self._bg_color = lightgray

        for css, color in css_class_colors.items():
            if css in csses:
                self._bg_color = color
                self._alignment = "center"

        self._narrow = "narrow" in csses or "state" in csses

    def minimal_width(self, pdfdoc):  # without padding
        # TODO: consider bold here!
        return max([pdfdoc.text_width(word) for word in self._text.split()] + [0])

    def maximal_width(self, pdfdoc):  # without padding
        return pdfdoc.text_width(self._text)

    def can_add_dynamic_width(self):
        return not self._narrow

    def width(self, pdfdoc):
        return self._width

    # Do wrapping of text to actual width. width() and height()
    # can be called only after this has run.
    def set_width(self, pdfdoc, width):
        self._width = width
        self._lines = pdfdoc.wrap_text(self._text, width, wrap_long_words=not self._narrow)

    def height(self, pdfdoc):
        return max(1, len(self._lines)) * pdfdoc.get_line_skip()

    # Render itself at left/top into direction right/down by width/height
    def render(self, pdfdoc, left, top, width, height, x_padding, y_padding, row_oddeven):
        if self._bg_color != white:
            color = self._bg_color
            if row_oddeven == "odd":
                color = lighten_color(color, 0.2)
            pdfdoc.render_rect(left, top - height, width, height, fill_color=color)

        for line in self._lines:
            top -= pdfdoc.get_line_skip()
            y = (
                top - y_padding + ((pdfdoc.get_line_skip() - pdfdoc.font_height()) / 2.0)
            )  # fixed: true-division
            if self._alignment == "right":
                x = left + width - x_padding
            elif self._alignment == "left":
                x = left + x_padding
            else:
                x = left + (width / 2.0)
            pdfdoc.render_text(
                x, y, line, align=self._alignment, bold=self._bold, color=self._color
            )


class TitleCell(TextCell):
    pass


# Rendering *one* Multisite-Icon
class IconCell:
    def __init__(self, path):
        self._image_path = path

    def minimal_width(self, pdfdoc):
        return self.height(pdfdoc)

    def maximal_width(self, pdfdoc):
        return self.height(pdfdoc)

    def can_add_dynamic_width(self):
        return False

    def set_width(self, pdfdoc, width):
        pass

    def width(self, pdfdoc):
        return self.height(pdfdoc)

    def height(self, pdfdoc):
        return pdfdoc.get_line_skip()

    def render(self, pdfdoc, left, top, width, height, x_padding, y_padding, row_oddeven):
        w = self.width(pdfdoc)
        pdfdoc.render_image(left + x_padding, top - w - y_padding, w, w, self._image_path)


# .
#   .--PDF2PNG-------------------------------------------------------------.
#   |              ____  ____  _____ ____  ____  _   _  ____               |
#   |             |  _ \|  _ \|  ___|___ \|  _ \| \ | |/ ___|              |
#   |             | |_) | | | | |_    __) | |_) |  \| | |  _               |
#   |             |  __/| |_| |  _|  / __/|  __/| |\  | |_| |              |
#   |             |_|   |____/|_|   |_____|_|   |_| \_|\____|              |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Generic functions to perform PDF to PNG conversion, e.g. for report  |
#   | thumbnail creation.                                                  |
#   '----------------------------------------------------------------------'


# On RedHat 5 the tool that we need is not available.
# Better check this and do not break the layout
def is_pdf2png_possible():
    return os.path.exists("/usr/bin/pdftoppm")


def pdf2png(pdf_source):
    # Older version of pdftoppm cannot read pipes. The need to seek around
    # in the file. Therefore we need to save the PDF source into a temporary file.
    with tempfile.NamedTemporaryFile(
        dir=cmk.utils.paths.tmp_dir,
        delete=False,
    ) as temp_file:
        temp_file.write(pdf_source)

    completed_process = subprocess.run(
        ["pdftoppm", "-png", "-f", "1", "-l", "1", "-scale-to", "1000", temp_file.name],
        close_fds=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    if completed_process.returncode:
        raise MKInternalError(
            _(
                "Cannot create PNG from PDF: %s, Exit code is %d, "
                'command was "%s", PDF source code was "%s..."'
            )
            % (
                completed_process.stderr,
                completed_process.returncode,
                " ".join(completed_process.args),
                pdf_source[:500],
            )
        )

    return completed_process.stdout
