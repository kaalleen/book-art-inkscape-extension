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
Technically it simply creates vertical lines and clips the pattern.
"""

from math import ceil

from inkex import (ClipPath, EffectExtension, Group, Layer, Path, PathElement,
                   TextElement, Transform, Tspan, colors, units)


class Bookart(EffectExtension):
    """EffectExtension to generate and colorize parallel vertical lines"""
    def __init__(self, *args, **kwargs):
        EffectExtension.__init__(self, *args, **kwargs)

        self.total_pages = None
        self.book_height = None
        self.line_distance = None
        self.vertical_adjustment = None
        self.stroke_width = None
        self.design = None
        self.transform = None

    def add_arguments(self, pars):
        # tabs
        pars.add_argument("--tabs", type=str, default=None, dest="tabs")
        pars.add_argument("--settings-tab", type=str, default=None, dest="content_tab")
        pars.add_argument("--colors-tab", type=str, default=None, dest="layout_tab")
        # book settings
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
        pars.add_argument("--stroke_width", type=float, default=0.265, help="Stroke width")
        pars.add_argument("--units", type=str, default="mm", help="Units")
        # output settings
        pars.add_argument("--document_format", type=str, default="a4",
                          help="Sets output document format and splits design to fit pages.")
        pars.add_argument("--page_margins", type=float, default=1, help="Page margins")
        pars.add_argument("--margin_unit", type=str, default='mm', help="Page margin unit")
        pars.add_argument("--color_pattern", type=colors.Color, default=colors.Color('#000000ff'))
        pars.add_argument("--color_highlight1", type=colors.Color,
                          default=colors.Color('#ed333bff'))
        pars.add_argument("--color_highlight2", type=colors.Color,
                          default=colors.Color('#ffbe6fff'))
        pars.add_argument("--color_background", type=colors.Color,
                          default=colors.Color('#f9f06bff'))

    def effect(self):
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

        # page format
        margin = str(self.options.page_margins * 2) + self.options.margin_unit
        if self.options.document_format == "letter":
            # US Letter: 8.5 * 11 (in)
            margin = units.convert_unit(margin, 'in')
            split_group = str(8.5 - margin) + 'in'
            split_group = self.svg.viewport_to_unit(split_group)
        else:
            # A4: 210 x 297 (mm)
            margin = units.convert_unit(margin, 'mm')
            split_group = str(210 - margin) + 'mm'
            split_group = self.svg.viewport_to_unit(split_group)

        # prepare design
        self._generate_design_group()
        if len(self.design) == 0:
            return
        self._scale_element()

        # clip selected paths
        clip = ClipPath(self.design)
        self.svg.defs.add(clip)

        if split_group == 0:
            num_segments = 1
            lines_per_seg = self.total_pages
        else:
            # add a little to the line distance to adjust for rounding errors
            num_segments = ceil((self.line_distance * self.total_pages) / split_group)
            if num_segments == 0:
                return
            lines_per_seg = ceil(self.total_pages / num_segments)

        for segment in range(num_segments):
            lines = self._generate_line_elements()
            line_paths, page_num_element = self._get_line_paths_and_numbers(segment, lines_per_seg)

            # insert into document
            group = self._insert_elements_to_document(line_paths, page_num_element, lines, segment)
            lines[0].clip = clip

            # create page
            page = self._generate_page(segment)
            # fit on page
            self._fit_on_page(page, group)

    def _insert_elements_to_document(self, line_paths, page_num_element, lines, segment):
        # insert lines into the svg
        layer = Layer()
        layer.label = "Book Art"
        self.svg.insert(0, layer)
        group = Group(id=f"Page #{segment + 1}")
        layer.insert(0, group)
        for i, line in enumerate(lines):
            line.path = Path(line_paths[i])
            group.insert(0, line)
        group.insert(0, page_num_element)
        group.transform.add_matrix(self.transform)
        return group

    def _generate_page(self, segment):
        if self.options.document_format == "letter":
            # US Letter: 8.5 * 11 (in)
            width, height = [self.svg.viewport_to_unit('8.5in'), self.svg.viewport_to_unit('11in')]
        else:
            # A4: 210 x 297 (mm)
            width, height = [self.svg.viewport_to_unit('210mm'), self.svg.viewport_to_unit('297mm')]

        # set viewbox size to prevent bad sizing for the first page
        if segment == 0:
            self.svg.set('height', f'{height}{self.svg.unit}')
            self.svg.set('width', f'{width}{self.svg.unit}')
            self.svg.set('viewBox', f'0 0 {width} {height}')

        page = self.svg.namedview.new_page(str((width * segment) + 5 * segment),
                                           str(0),
                                           str(width),
                                           str(height))

        # this is the first page, let's clean up all previously existing pages
        if segment == 0:
            for ink_page in self.svg.namedview.get_pages():
                if ink_page != page:
                    self.svg.namedview.remove(ink_page)
        return page

    def _fit_on_page(self, page, group):
        # groups bounding box is somehow off, so lets use the bounding box of the lines element
        group_bbox = group.getchildren()[1].bounding_box()

        page_center_x = page.x + (page.width / 2)
        group_center_x = group_bbox.center_x
        transform_x = page_center_x - group_center_x

        page_center_y = page.height / 2
        group_center_y = group_bbox.center_y
        transform_y = page_center_y - group_center_y

        group.set('transform', f'translate({transform_x}, {transform_y})')

    def _get_line_paths_and_numbers(self, segment, lines_per_seg):
        top, bottom, left, right = self._get_line_positions()
        left += (segment * lines_per_seg * self.line_distance)
        right = min((left + lines_per_seg * self.line_distance), right)

        # create the line paths and page numbers
        font_size = self.svg.viewport_to_unit(str(self.options.font_size) + self.options.units)
        style = f"text-anchor:middle;font-size:{font_size}"
        small_font_style = f"font-size:{font_size / 2};fill:grey;"
        page_num_element = TextElement(y=str(bottom + font_size + 2), style=style)

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
            elif (start == left or left + self.line_distance > right):
                tspan = Tspan(str(int(page_count)), x=str(left), style=small_font_style)
                page_num_element.insert(0, tspan)
            line_paths[0] += path
            line_paths[3] += path
            page_count += 2
            left += self.line_distance
        return line_paths, page_num_element

    def _get_line_positions(self):
        bbox = self.design.bounding_box()
        # position of the first line at the left side of the bounding box
        left = bbox.left
        top = bbox.top
        right = bbox.right
        bottom = bbox.bottom

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

        for i in range(4):
            style = f"fill:none;stroke:{line_colors[i]};stroke-width:{self.stroke_width}"
            lines.append(PathElement(style=style))
        return lines

    def _generate_design_group(self):
        self.design = Group()
        # No selection -> Select all
        if not self.svg.selection:
            elements = self.svg.xpath('.//svg:rect|.//svg:circle|.//svg:ellipse|.//svg:path')
            for element in elements:
                self._insert_element_into_design_group(element)
            return
        for selection in self.svg.selection:
            if selection.tag_name == 'g':
                for element in selection.iterdescendants():
                    self._insert_element_into_design_group(element)
            else:
                self._insert_element_into_design_group(selection)

    def _insert_element_into_design_group(self, element):
        if element.tag_name in ['rect', 'circle', 'ellipse', 'path']:
            element.transform = element.composed_transform()
            self.design.insert(0, element)

    def _scale_element(self):
        num_pages = self.total_pages - self.options.pages_before - self.options.pages_after
        bbox = self.design.bounding_box()
        width = bbox.width
        if num_pages <= 0 or width == 0:
            return
        line_dist = width / num_pages
        if self.options.line_distance == 0:
            self.line_distance = line_dist
            return
        scale_x = self.line_distance / line_dist
        self.design.transform = Transform(f'scale({scale_x}, 1)')
        translate_x = bbox.left - self.design.bounding_box().left
        translate_y = bbox.bottom - self.design.bounding_box().bottom
        self.transform = f'translate({translate_x}, {translate_y})'


if __name__ == '__main__':
    Bookart().run()
