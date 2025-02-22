#!/usr/bin/env python3
#
# coding=utf-8
#
# Copyright (C) 2022-2023 Kaalleen
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
"""
Extension to create cut and fold book art pattern.
Technically it simply creates vertical lines and clips the pattern.
"""

from math import ceil

from inkex import (
    Boolean,
    Circle,
    ClipPath,
    EffectExtension,
    Ellipse,
    Group,
    Layer,
    PathElement,
    Rectangle,
    TextElement,
    Transform,
    Tspan,
)
from inkex.colors import Color


class Design:
    """Holds pattern group(s)"""

    def __init__(self, svg, settings):
        self.svg = svg
        self.settings = settings

        self.design_group = Group()
        self.pattern_groups = []

    def elements(self):
        """get element selection (no selection returns all elements)"""
        if not self.svg.selection:
            pattern_elements = self.svg.xpath(
                ".//svg:rect|.//svg:circle|.//svg:ellipse|.//svg:path"
            )
            pattern_elements = list(pattern_elements)
        else:
            pattern_elements = self.svg.selection.rendering_order()
            pattern_elements = list(
                pattern_elements.get((PathElement, Ellipse, Rectangle, Circle))
            )
        pattern_elements.reverse()
        return pattern_elements

    def elements_to_pattern_groups(self):
        """Generates pattern groups, one group for each color of the original pattern
        If keep_pattern_color is set to False, all elements are grouped together and use
        the pattern color setting.
        """
        elements = self.elements()
        if not self.settings["keep_pattern_color"]:
            pattern_group = self.new_pattern_group(self.settings["design_color"])
            pattern_group.add_elements(elements)
            return
        previous_color = None
        pattern_group = None
        for element in elements:
            color = element.style("fill", "black")
            if pattern_group and previous_color == color:
                pattern_group.add_element(element)
            else:
                pattern_group = self.new_pattern_group(color)
                pattern_group.add_element(element)

    def new_pattern_group(self, color):
        """adds a new pattern group"""
        pattern_group = PatternGroup(self.svg, color)
        self.pattern_groups.append(pattern_group)
        return pattern_group

    def design_to_group(self):
        """inserts the pattern groups into the design group"""
        for group in self.pattern_groups:
            self.design_group.insert(0, group.pattern)

    def bbox(self):
        """returns the bounding box of the entire design"""
        return self.design_group.bounding_box()

    @property
    def colors(self):
        """returns a list with the design colors"""
        colors = []
        for pattern in self.pattern_groups:
            colors.append(pattern.color)
        return colors

    def scale(self):
        """scale the design according to the line distance setting"""
        num_pages = self.settings["design_pages"]
        width = self.bbox().width
        if num_pages <= 0 or width == 0:
            return

        scale_factor = self.settings["line_distance"] / (width / num_pages)
        for pattern in self.pattern_groups:
            pattern.scale(scale_factor)

    def __len__(self):
        return len(self.pattern_groups)

    def __repr__(self):
        return f"Design({self.pattern_groups})"


class PatternGroup:
    """Holds design elements of the same color"""

    def __init__(self, svg=None, color=None):
        self.svg = svg
        self.color = color
        self.pattern = Group()

    def add_element(self, element):
        """apply transforms and adds an element to the pattern group"""
        element.transform = element.composed_transform()
        # exclude cliped paths (they won't work)
        if element.get("clip-path", None) is None:
            self.pattern.insert(0, element)

    def add_elements(self, elements):
        """adds multiple elements to the pattern group"""
        for element in elements:
            self.add_element(element)

    def scale(self, scale_factor):
        """scales the pattern in x direction to stretch it according to the line distance value
        the pattern group will not be distorted in y direction"""
        self.pattern.transform = Transform(f"scale({scale_factor}, 1)")

    def to_clip_path(self):
        """generates a clip path which contains the pattern group and inserts it into the svg
        returns the clip element"""
        clip = ClipPath()
        clip.insert(0, self.pattern)
        self.svg.defs.add(clip)
        return clip

    def __repr__(self):
        return f"PatternGroup({self.color}, {self.pattern})"


class Lines:  # pylint: disable=too-many-instance-attributes
    """Serves to generate the lines which are representing the book pages"""

    def __init__(
        self,
        design_colors,
        num_lines,
        num_pages,  # pylint: disable=too-many-arguments
        design_bbox,
        design_clips,
        settings,
    ):
        self.settings = settings
        self.colors = design_colors + settings["highlight_colors"]
        self.num_lines = num_lines
        self.num_pages = num_pages
        self.design_clips = design_clips
        self.first_page = ceil(settings["first_page"] / 2)
        self.last_page = ceil(settings["last_page"] / 2)
        self.design_bbox = design_bbox

        self.line_groups = []
        self.make_lines()

    def __repr__(self):
        return f"Lines({self.line_groups})"

    def _get_line_bbox(self):
        left = self.design_bbox.left
        top = self.design_bbox.top
        right = self.design_bbox.right
        bottom = self.design_bbox.bottom

        left -= self.settings["pages_before"] * self.settings["line_distance"]
        right += self.settings["pages_after"] * self.settings["line_distance"]

        spacing = (self.settings["book_height"] - self.design_bbox.height) / 2
        if self.settings["margin_bottom"] != 0:
            bottom = bottom + self.settings["margin_bottom"]
            top = bottom - self.settings["book_height"]
        else:
            top = top - spacing
            bottom = bottom + spacing

        return {"left": left, "top": top, "right": right, "bottom": bottom}

    def make_lines(self):
        """generates the lines and make sure we insert the text elements"""

        line_bbox = self._get_line_bbox()
        num_colors = len(self.colors)
        for i in range(self.num_pages):
            page_group = Group()
            text = Text(self.settings["font_size"], line_bbox["bottom"])
            for j in range(num_colors):
                line_number = self.first_page + (i * self.num_lines)
                left = line_bbox["left"] + (
                    i * self.num_lines * self.settings["line_distance"]
                )
                style = (
                    f"fill:none;stroke:{self.colors[j]};"
                    f"stroke-width:{self.settings['stroke_width']}"
                )
                lines = PathElement(style=style)
                path = ""
                for k in range(self.num_lines):
                    if line_number > self.last_page:
                        if not (line_number - 1) % 10 == 0:
                            left -= self.settings["line_distance"]
                            text.add_text(left, (line_number - 1) * 2, "small")
                        break
                    if line_number % 10 == 0:
                        text.add_text(left, line_number * 2)
                    elif k in (0, self.num_lines - 1):
                        text.add_text(left, line_number * 2, "small")

                    if j == num_colors - 1 and line_number % 10 != 0:
                        left += self.settings["line_distance"]
                        line_number += 1
                        continue
                    if j == num_colors - 2 and (
                        line_number % 10 == 0 or line_number % 5 != 0
                    ):
                        left += self.settings["line_distance"]
                        line_number += 1
                        continue
                    if j == num_colors - 3 and line_number % 5 == 0:
                        left += self.settings["line_distance"]
                        line_number += 1
                        continue
                    path += (
                        f"M {left} {line_bbox['top']} L {left} {line_bbox['bottom']} "
                    )
                    left += self.settings["line_distance"]
                    line_number += 1
                lines.set("d", path)
                if j < len(self.design_clips):
                    lines.clip = self.design_clips[j]
                page_group.insert(0, lines)
            page_group.insert(0, text.text_element)
            self.line_groups.append(page_group)

    def add_to_document(self, layer):
        """inserts the lines into the svg"""
        for lines in self.line_groups:
            layer.insert(0, lines)

    def add_bottom_lines(self):
        """Inserts a helper line at the bottom of the lines for aligning the book"""
        style = f"fill:none; stroke:black; stroke-width:{self.settings['stroke_width']}"
        for linegroup in self.line_groups:
            bbox = linegroup.getchildren()[-1].shape_box()
            line = PathElement(style=style)
            line.set("d", f"M {bbox.left}, {bbox.bottom} {bbox.right}, {bbox.bottom}")
            linegroup.append(line)


class Text:  # pylint: disable=too-few-public-methods
    """Holds the text for the page numbers"""

    def __init__(self, font_size, y_position):
        self.font_size = font_size
        self.style = f"text-anchor:middle;font-size:{font_size}"
        self.small_style = f"text-anchor:middle;font-size:{font_size / 2};fill:grey;"
        self.text_element = TextElement(
            y=str(y_position + self.font_size + 2), style=self.style
        )

    def add_text(self, x_position, text, size="normal"):
        """adds a new tspan element"""
        tspan = Tspan(str(int(text)), x=str(x_position))
        if size == "small":
            tspan.set("style", self.small_style)
        self.text_element.insert(0, tspan)


class Pages:
    """Holds information about the pages"""

    def __init__(self, svg, settings):
        self.svg = svg
        self.settings = settings

        self.width = self.height = None
        self.pages = []
        self.document_bbox(self.settings["document_format"])
        self.set_viewbox_size()

    def page_content_area(self):
        """returns the width of the page, excluding page margins"""
        margin = self.settings["page_margins"] * 2
        return self.width - margin

    @property
    def num_lines_per_page(self):
        """returns how many lines fit on one page"""
        return ceil(self.page_content_area() / self.settings["line_distance"])

    @property
    def num_pages(self):
        """returns number of necessary pages"""
        num_pages = (
            self.settings["line_distance"]
            * self.settings["total_pages"]
            / self.page_content_area()
        )
        return ceil(num_pages)

    def document_bbox(self, document_format):
        """returns width and height of one page"""
        if document_format == "letter":
            # US Letter: 8.5 * 11 (in)
            self.width, self.height = (
                self.svg.viewport_to_unit("8.5in"),
                self.svg.viewport_to_unit("11in"),
            )
        else:
            # A4: 210 x 297 (mm)
            self.width, self.height = (
                self.svg.viewport_to_unit("210mm"),
                self.svg.viewport_to_unit("297mm"),
            )

    def set_viewbox_size(self):
        """set viewbox size to page size, to avoid bad scaling"""
        self.svg.set("height", f"{self.height}{self.svg.unit}")
        self.svg.set("width", f"{self.width}{self.svg.unit}")
        self.svg.set("viewBox", f"0 0 {self.width} {self.height}")

    def add_page(self, page_num):
        """add a new page"""
        namedview = self.svg.namedview
        page = namedview.new_page(
            str((self.width * page_num) + 5 * page_num),
            str(0),
            str(self.width),
            str(self.height),
        )
        self.pages.append(page)
        return page

    def cleanup_pages(self):
        """remove previously existing pages"""
        document_pages = self.svg.namedview.get_pages()
        for page in document_pages:
            if page not in self.pages:
                self.svg.namedview.remove(page)

    def generate_pages_with_lines(self, line_groups):
        """add pages and center out line groups"""
        for i, line_group in enumerate(line_groups):
            page = self.add_page(i)
            self.fit_on_page(page, line_group)
        self.cleanup_pages()

    def fit_on_page(self, page, group):
        """center line groups on pages"""
        # the bounding box of the group is somehow off,
        # lets use the bounding box of the lines element
        group_bbox = group.getchildren()[3].bounding_box()

        page_center_x = page.x + (page.width / 2)
        group_center_x = group_bbox.center_x
        transform_x = page_center_x - group_center_x

        page_center_y = page.height / 2
        group_center_y = group_bbox.center_y
        transform_y = page_center_y - group_center_y

        group.set("transform", f"translate({transform_x}, {transform_y})")

    def __repr__(self):
        return f"Pages({self.width}, {self.height}, {self.pages})"


class Bookart(EffectExtension):
    """EffectExtension to generate and colorize parallel vertical lines"""

    def __init__(self, *args, **kwargs):
        EffectExtension.__init__(self, *args, **kwargs)

        self.settings = {}

    def add_arguments(self, pars):
        # tabs
        pars.add_argument("--tabs", type=str, default=None, dest="tabs")
        pars.add_argument("--settings-tab", type=str, default=None, dest="content_tab")
        pars.add_argument("--colors-tab", type=str, default=None, dest="layout_tab")
        # book settings
        pars.add_argument(
            "--first_page", type=int, default=0, help="First even page number"
        )
        pars.add_argument(
            "--last_page", type=int, default=250, help="Last even page number"
        )
        pars.add_argument(
            "--pages_before", type=int, default=0, help="Pages before design"
        )
        pars.add_argument(
            "--pages_after", type=int, default=0, help="Pages after design"
        )
        pars.add_argument("--book_height", type=float, default=250, help="Book height")
        pars.add_argument(
            "--line_distance", type=float, default=1.5, help="Distance between lines"
        )
        pars.add_argument(
            "--margin_bottom", type=float, default=0.0, help="Margin to bottom"
        )
        pars.add_argument("--font_size", type=float, default=4, help="Font size")
        pars.add_argument(
            "--stroke_width", type=float, default=0.265, help="Stroke width"
        )
        pars.add_argument("--units", type=str, default="mm", help="Units")
        # output settings
        pars.add_argument(
            "--document_format",
            type=str,
            default="a4",
            help="Sets output document format and splits design to fit pages.",
        )
        pars.add_argument("--page_margins", type=float, default=1, help="Page margins")
        pars.add_argument(
            "--margin_unit", type=str, default="mm", help="Page margin unit"
        )
        pars.add_argument("--color_pattern", type=Color, default=Color("#000000"))
        pars.add_argument("--color_highlight1", type=Color, default=Color("#ed333b"))
        pars.add_argument("--color_highlight2", type=Color, default=Color("#ffbe6f"))
        pars.add_argument("--color_background", type=Color, default=Color("#f9f06b"))
        pars.add_argument(
            "--keep_pattern_color",
            type=Boolean,
            default=False,
            help="Pattern: keep original color",
        )
        pars.add_argument(
            "--bottom_line",
            type=Boolean,
            default=False,
            help="Add bottom line for book aligning",
        )

    def effect(self):
        total_pages = (self.options.last_page - self.options.first_page) / 2
        design_pages = (
            total_pages - self.options.pages_before - self.options.pages_after
        )

        self.settings = {
            "first_page": self.options.first_page,
            "last_page": self.options.last_page,
            "pages_before": self.options.pages_before,
            "pages_after": self.options.pages_after,
            "total_pages": total_pages,
            "design_pages": design_pages,
            "document_format": self.options.document_format,
            "page_margins": self.convert_unit(
                self.options.page_margins, self.options.margin_unit
            ),
            "font_size": self.convert_unit(self.options.font_size),
            "book_height": self.convert_unit(self.options.book_height),
            "line_distance": max(0.1, self.convert_unit(self.options.line_distance)),
            "margin_bottom": self.convert_unit(self.options.margin_bottom),
            "stroke_width": self.convert_unit(self.options.stroke_width),
            "design_color": self.options.color_pattern,
            "highlight_colors": [
                self.options.color_background,
                self.options.color_highlight2,
                self.options.color_highlight1,
            ],
            "keep_pattern_color": self.options.keep_pattern_color,
        }

        # pages
        pages = Pages(self.svg, self.settings)

        # group, scale and clip design
        design = Design(self.svg, self.settings)
        design.elements_to_pattern_groups()
        design.design_to_group()
        design.scale()
        bbox = design.bbox()

        # generate design clips
        design_clips = []
        for pattern in design.pattern_groups:
            clip = pattern.to_clip_path()
            design_clips.append(clip)

        # get number of pages and lines per page
        lines_per_page = pages.num_lines_per_page
        num_pages = pages.num_pages

        # generate lines
        lines = Lines(
            design.colors, lines_per_page, num_pages, bbox, design_clips, self.settings
        )
        if self.options.bottom_line:
            lines.add_bottom_lines()

        # insert into document
        layer = Layer()
        layer.label = "Book Art"
        self.svg.insert(0, layer)
        lines.add_to_document(layer)
        pages.generate_pages_with_lines(lines.line_groups)

    def convert_unit(self, value, unit=None):
        """convert units (input values)"""
        if unit is None:
            unit = self.options.units
        return self.svg.viewport_to_unit(str(value) + unit)


if __name__ == "__main__":
    Bookart().run()
