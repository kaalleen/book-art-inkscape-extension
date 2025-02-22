# coding=utf-8
"""
Test the bookart extension
"""

from inkex.tester import ComparisonMixin, TestCase

from bookart import Bookart


class BookartTest(ComparisonMixin, TestCase):
    """Test bookart extension with comparisons"""

    effect_class = Bookart
    comparisons = [
        (),
        (
            "--id=woodpecker",
            "--first_page=-6",
            "--last_page=100",
            "--pages_before=0",
            "--pages_after=0",
            "--book_height=160",
        ),
        (
            "--id=woodpecker",
            "--first_page=0",
            "--last_page=250",
            "--pages_before=5",
            "--pages_after=5",
            "--book_height=8",
            "--line_distance=0.1",
            "--stroke_width=0.02",
            "--units=in",
            "--font_size=0.1",
            "--document_format=letter",
            "--page_margins=0.5",
            "--margin_unit=in",
        ),
        (
            "--id=woodpecker",
            "--first_page=6",
            "--last_page=300",
            "--pages_before=10",
            "--pages_after=10",
            "--book_height=270",
            "--line_distance=5",
            "--vertical_adjustment=50",
            "--font_size=2",
            "--stroke_width=0.3",
            "--page_margins=2",
        ),
        (
            "--id=woodpecker",
            "--first_page=12",
            "--last_page=350",
            "--pages_before=4",
            "--pages_after=4",
            "--line_distance=3",
            "--page_margins=20",
            "--margin_unit=mm",
            "--color_pattern=#ff0000",
            "--color_highlight1=#00bc12",
            "--color_highlight2=#ebf400",
            "--color_background=#66ff88",
        ),
    ]
    compare_file = "svg/bookart.svg"
