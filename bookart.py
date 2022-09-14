#!/usr/bin/env python
# coding=utf-8
#
# Copyright (C) 2022 Kaalleen
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
Technically it simply creates vertical lines and uses the pattern as a clip.
"""

from math import ceil

from inkex import (ClipPath, EffectExtension, Group, Path, PathElement,
                   TextElement, Transform, Tspan, colors, errormsg)
from inkex.localization import inkex_gettext as _


class Bookart(EffectExtension):
    """EffectExtension to generate and colorize parallel vertical lines"""
    def __init__(self, *args, **kwargs):
        EffectExtension.__init__(self, *args, **kwargs)

        self.total_pages = None
        self.book_height = None
        self.line_distance = None
        self.vertical_adjustment = None
        self.stroke_width = None
        self.combined_shape = None

    def add_arguments(self, pars):
        # tabs
        self.arg_parser.add_argument("--tabs", type=str, default=None, dest="tabs")
        self.arg_parser.add_argument("--settings-tab", type=str, default=None, dest="content_tab")
        self.arg_parser.add_argument("--colors-tab", type=str, default=None, dest="layout_tab")
        # general settings
        pars.add_argument("--first_page", type=int, default=250, help="First even page number")
        pars.add_argument("--last_page", type=int, default=250, help="Last even page number")
        pars.add_argument("--pages_before", type=int, default=0, help="Pages before design")
        pars.add_argument("--pages_after", type=int, default=0, help="Pages after design")
        pars.add_argument("--book_height", type=float, default=15, help="Book height")
        pars.add_argument("--line_distance", type=float, default=0,
                          help="Distance between lines")
        pars.add_argument("--vertical_adjustment", type=float, default=0.0,
                          help="Vertical adjustment")
        pars.add_argument("--font_size", type=float, default=10, help="Font size")
        pars.add_argument("--stroke_width", type=float, default=1, help="Stroke width")
        pars.add_argument("--split_group", type=float, default=0,
                          help="Split design after this length to fit on page")
        pars.add_argument("--units", type=str, default="mm", help="Units")
        # colors
        pars.add_argument("--color_pattern", type=colors.Color, default=colors.Color('#000000ff'))
        pars.add_argument("--color_highlight1", type=colors.Color,
                          default=colors.Color('#ed333bff'))
        pars.add_argument("--color_highlight2", type=colors.Color,
                          default=colors.Color('#ffbe6fff'))
        pars.add_argument("--color_background", type=colors.Color,
                          default=colors.Color('#f9f06bff'))

    def effect(self):
        if not self.svg.selection:
            errormsg(_("Please select one object."))
            return

        self.total_pages = (self.options.last_page - self.options.first_page) / 2
        # convert units to px
        self.book_height = str(self.options.book_height) + self.options.units
        self.book_height = self.svg.viewport_to_unit(self.book_height)
        self.line_distance = str(self.options.line_distance) + self.options.units
        self.line_distance = self.svg.viewport_to_unit(self.line_distance)
        self.vertical_adjustment = str(self.options.vertical_adjustment) + self.options.units
        self.vertical_adjustment = self.svg.viewport_to_unit(self.vertical_adjustment)
        self.stroke_width = str(self.options.stroke_width) + self.options.units
        self.stroke_width = self.svg.viewport_to_unit(self.stroke_width)
        split_group = str(self.options.split_group) + self.options.units
        split_group = self.svg.viewport_to_unit(split_group)

        # prepare shape
        self._get_shape()
        self.line_distance = self._scale_element()

        # combine selected paths
        clip = ClipPath(self.combined_shape)
        self.svg.defs.add(clip)

        if split_group == 0:
            num_segments = 1
            lines_per_seg = self.total_pages
        else:
            # add a little to line distance to adjust for rounding errors
            num_segments = ceil((self.line_distance * self.total_pages) / split_group)
            lines_per_seg = ceil(self.total_pages / num_segments)

        for segment in range(num_segments):
            lines = self._generate_line_elements()
            line_paths, page_num_element = self._get_line_paths_and_numbers(segment, lines_per_seg)

            # insert into document
            self._insert_elements(line_paths, page_num_element, lines, segment)
            lines[0].clip = clip

    def _insert_elements(self, line_paths, page_num_element, lines, segment):
        # insert lines into the svg
        group = Group(id=f"bookart_group_{segment}")
        self.svg.get_current_layer().insert(0, group)
        for i, line in enumerate(lines):
            line.path = Path(line_paths[i])
            group.insert(0, line)
        group.insert(0, page_num_element)

    def _get_shape(self):
        selected_path = str()
        for selection in self.svg.selection:
            transform = selection.composed_transform()
            selected_path += str(Path(selection.get_path()).transform(transform))
            selection.getparent().remove(selection)
        # make a path element and set path
        self.combined_shape = PathElement(d=selected_path)

    def _get_line_paths_and_numbers(self, segment, lines_per_seg):
        top, bottom, left, right = self._get_line_positions()
        left += (segment * lines_per_seg * self.line_distance)
        right = min((left + lines_per_seg * self.line_distance), right)

        # create the line paths and page numbers
        font_size = str(self.options.font_size) + self.options.units
        style = f"text-anchor:middle;font-size:{self.options.font_size}{self.options.units}"
        page_num_element = TextElement(y=str(bottom + self.svg.viewport_to_unit(font_size) + 2),
                                       style=style)

        page_count = self.options.first_page + (segment * lines_per_seg * 2)
        start = left
        if not page_count % 2 == 0:
            page_count += 1
        line_paths = [str() for _i in range(4)]
        while left <= right + 0.1:
            path = f'M {left} {top} L {left} {bottom} '
            if page_count % 20 == 0:
                line_paths[1] += path
                page_num_element.insert(0, Tspan(str(int(page_count)), x=str(left)))
            elif page_count % 10 == 0:
                line_paths[2] += path
            elif ((start == left or left + self.line_distance > right) and
                  self.options.split_group != 0):
                small_number_style = f"font-size:{self.options.font_size / 2}{self.options.units};\
                                       fill:lightgrey;"
                page_num_element.insert(0, Tspan(str(int(page_count)),
                                                 x=str(left),
                                                 style=small_number_style))
            line_paths[0] += path
            line_paths[3] += path
            page_count += 2
            left += self.line_distance
        return line_paths, page_num_element

    def _get_line_positions(self):
        bbox = self.combined_shape.bounding_box()
        # position of the first line at the left side of the bounding box
        left, top = bbox.minimum
        right, bottom = bbox.maximum

        left -= self.options.pages_before * self.line_distance
        right += self.options.pages_after * self.line_distance

        spacing = (self.book_height - bbox.height) / 2
        top = top - spacing - self.vertical_adjustment
        bottom = bottom + spacing - self.vertical_adjustment

        return top, bottom, left, right

    def _set_clip(self, clip, line):
        line.clip = clip

    def _generate_line_elements(self):
        lines = []
        line_colors = [self.options.color_pattern,
                       self.options.color_highlight1,
                       self.options.color_highlight2,
                       self.options.color_background]
        # stroke width
        if self.stroke_width == 0:
            stroke_width = "stroke-width:1px;vector-effect:non-scaling-stroke;\
                                 -inkscape-stroke:hairline;"
        else:
            stroke_width = f'stroke-width:{self.stroke_width}'

        for i in range(4):
            style = f"fill:none;stroke:{line_colors[i]};{stroke_width}"
            lines.append(PathElement(style=style))
        return lines

    def _scale_element(self):
        num_pages = self.total_pages - self.options.pages_before - self.options.pages_after
        if num_pages == 0:
            return self.line_distance
        bbox = self.combined_shape.bounding_box()
        width = bbox.width
        line_dist = width / num_pages
        if self.options.line_distance == 0:
            return line_dist
        if line_dist == 0:
            return self.line_distance
        transform = f'scale({self.line_distance / line_dist}, 1)'
        self.combined_shape.transform = Transform(transform)
        return self.line_distance


if __name__ == '__main__':
    Bookart().run()
