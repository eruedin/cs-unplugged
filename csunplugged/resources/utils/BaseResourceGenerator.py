"""Class for generator for a resource."""

from abc import ABC, abstractmethod
from resources.utils.resize_encode_resource_images import resize_encode_resource_images
from utils.str_to_bool import str_to_bool
from utils.errors.QueryParameterMissingError import QueryParameterMissingError
from utils.errors.QueryParameterInvalidError import QueryParameterInvalidError
from utils.errors.ThumbnailPageNotFoundError import ThumbnailPageNotFoundError
from utils.errors.MoreThanOneThumbnailPageFoundError import MoreThanOneThumbnailPageFoundError
from copy import deepcopy
from django.conf import settings
from django.template.loader import render_to_string
from django.contrib.staticfiles import finders

from resources.utils.resource_parameters import (
    EnumResourceParameter,
    TextResourceParameter,
    IntegerResourceParameter,
)

from lxml import etree
from django.utils.translation import ugettext as _
from django.urls import reverse

PAPER_SIZE_VALUES = {
    "a4": _("A4"),
    "letter": _("US Letter")
}

class BaseResourceGenerator(ABC):
    """Class for generator for a resource."""
    copies = False  # Default

    def __init__(self, requested_options=None):
        """Construct BaseResourceGenerator instance.

        Args:
            requested_options: QueryDict of requested_options (QueryDict).
        """
        self.options = self.get_options()
        self.options.update(self.get_local_options())
        if requested_options:
            self.process_requested_options(requested_options)

    def get_options(self):
        options = self.get_additional_options()
        options.update({
            "paper_size": EnumResourceParameter(
                name="paper_size",
                description=_("Paper Size"),
                values=PAPER_SIZE_VALUES,
                default="a4"
            ),
        })
        return options

    def get_local_options(self):
        local_options = {
            "header_text": TextResourceParameter(
                name="header_text",
                description=_("Header Text"),
                placeholder=_("Example School: Room Four")
            ),
        }
        if self.copies:
            local_options.update({
                "copies":  IntegerResourceParameter(
                    name="copies",
                    description=_("Number of Copies"),
                    min_val=1,
                    max_val=50,
                    default=1
                ),
            })
        return local_options

    def get_additional_options(self):
        return {}

    def get_options_html(self, slug):
        html_elements = []
        for parameter in self.get_options().values():
            html_elements.append(parameter.html_element())
        if settings.DEBUG:
            html_elements.append(etree.Element("hr"))
            h3 = etree.Element("h3")
            h3.text = _("Local Generation Only")
            html_elements.append(h3)
            for parameter in self.get_local_options().values():
                html_elements.append(parameter.html_element())

        html_string = ""
        for html_elem in html_elements:
            html_string += etree.tostring(html_elem, encoding='utf-8').decode('utf-8')
        return html_string

    @abstractmethod
    def data(self):
        """Abstract method to be implemented by subclasses."""
        raise NotImplementedError  # pragma: no cover

    @property
    def subtitle(self):
        """Return the subtitle string of the resource.

        Used after the resource name in the filename, and
        also on the resource image.

        Returns:
            Text for subtitle (str).
        """
        return self.options["paper_size"].value

    def process_requested_options(self, requested_options):
        """Convert requested options to usable types.

        Args:
            requested_options: QueryDict of requested_options (QueryDict).

        Method does the following:
        - Update all values through str_to_bool utility function.
        - Raises 404 error is requested option cannot be found.
        - Raises 404 is option given with invalid value.

        Returns:
            QueryDict of converted requested options (QueryDict).
        """
        # requested_options = requested_options.copy()
        for option_name, option in self.options.items():
            values = requested_options.getlist(option_name)
            option.process_requested_values(values)

    def pdf(self, resource_name):
        """Return PDF for resource request.

        The PDF is returned (compared to the thumbnail which is directly saved)
        as the PDF may be either saved to the disk, or returned in a HTTP
        response.

        Args:
            resource_name: Name of the resource (str).

        Return:
            PDF file of resource.
        """
        # Only import weasyprint when required as production environment
        # does not have it installed.
        from weasyprint import HTML, CSS
        context = dict()
        context["resource"] = resource_name
        context["header_text"] = self.options["header_text"].value
        context["paper_size"] = self.options["paper_size"].value

        num_copies = range(0, int(self.options["copies"].value))
        context["all_data"] = []
        for copy in num_copies:
            copy_data = self.data()
            if not isinstance(copy_data, list):
                copy_data = [copy_data]
            copy_data = resize_encode_resource_images(
                self.options["paper_size"].value,
                copy_data
            )
            context["all_data"].append(copy_data)

        filename = "{} ({})".format(resource_name, self.subtitle)
        context["filename"] = filename

        pdf_html = render_to_string("resources/base-resource-pdf.html", context)
        html = HTML(string=pdf_html, base_url=settings.BUILD_ROOT)
        css_file = finders.find("css/print-resource-pdf.css")
        css_string = open(css_file, encoding="UTF-8").read()
        base_css = CSS(string=css_string)
        return (html.write_pdf(stylesheets=[base_css]), filename)

    def save_thumbnail(self, resource_name, path):
        """Create thumbnail for resource request.

        Args:
            resource_name: Name of the resource (str).
            path: The path to write the thumbnail to (str).
        """
        thumbnail_data = self.generate_thumbnail()
        self.write_thumbnail(thumbnail_data, resource_name, path)

    def generate_thumbnail(self):
        """Create thumbnail for resource request.

        Raises:
            ThumbnailPageNotFoundError: If resource with more than one page does
                                   not provide a thumbnail page.
            MoreThanOneThumbnailPageFoundError: If resource provides more than
                                           one page as the thumbnail.

        Returns:
            Dictionary of thumbnail data.
        """
        thumbnail_data = self.data()
        if not isinstance(thumbnail_data, list):
            thumbnail_data = [thumbnail_data]

        if len(thumbnail_data) > 1:
            thumbnail_data = list(filter(lambda thumbnail_data: thumbnail_data.get("thumbnail"), thumbnail_data))

            if len(thumbnail_data) == 0:
                raise ThumbnailPageNotFoundError(self)
            elif len(thumbnail_data) > 1:
                raise MoreThanOneThumbnailPageFoundError(self)

        thumbnail_data = resize_encode_resource_images(
            self.options["paper_size"].value,
            thumbnail_data
        )
        return thumbnail_data[0]

    def write_thumbnail(self, thumbnail_data, resource_name, path):
        """Save generatered thumbnail.

        Args:
            thumbnail_data: Data of generated thumbnail.
            resource_name: Name of the resource (str).
            path: The path to write the thumbnail to (str).
        """
        # Only import weasyprint when required as production environment
        # does not have it installed.
        from weasyprint import HTML, CSS
        context = dict()
        context["resource"] = resource_name
        context["paper_size"] = self.options["paper_size"].value
        context["all_data"] = [[thumbnail_data]]
        pdf_html = render_to_string("resources/base-resource-pdf.html", context)
        html = HTML(string=pdf_html, base_url=settings.BUILD_ROOT)
        css_file = finders.find("css/print-resource-pdf.css")
        css_string = open(css_file, encoding="UTF-8").read()
        base_css = CSS(string=css_string)
        thumbnail = html.write_png(stylesheets=[base_css], resolution=72)
        thumbnail_file = open(path, "wb")
        thumbnail_file.write(thumbnail)
        thumbnail_file.close()
