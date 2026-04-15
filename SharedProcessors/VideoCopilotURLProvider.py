#!/usr/local/autopkg/python
# VideoCopilotURLProvider.py
#
# Finds a Video Copilot product's Mac download URL from the products/m1 page
# and returns the final download URL and version number.
#
# Two URL patterns are handled automatically:
#
#   Short-code URLs  (free products)
#     https://www.videocopilot.net/dl/<slug>
#     → followed via curl HEAD to resolve the final S3 URL
#
#   Signed CloudFront URLs  (paid/licensed products)
#     https://files.videocopilot.net/<path>/Product_version_Mac.zip?Expires=...
#     → used directly; the signature is regenerated on every page load so it is
#       always fresh when AutoPkg fetches the page

import re
import subprocess

from autopkglib import Processor, ProcessorError

__all__ = ["VideoCopilotURLProvider"]

PRODUCTS_URL = "https://www.videocopilot.net/products/m1/"
SHORTLINK_HOST = "www.videocopilot.net/dl/"


def _curl(args, timeout=30):
    """Run curl and return stdout, raising ProcessorError on failure."""
    try:
        result = subprocess.run(
            ["curl"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as err:
        raise ProcessorError(f"curl timed out: {err}")
    except Exception as err:
        raise ProcessorError(f"curl failed: {err}")
    if result.returncode != 0:
        raise ProcessorError(f"curl exited {result.returncode}: {result.stderr.strip()}")
    return result.stdout


def _resolve_shortlink(short_url):
    """Follow a videocopilot.net/dl/ shortlink and return the final URL."""
    final_url = _curl(
        ["-sIL", "--write-out", "%{url_effective}", "-o", "/dev/null", short_url]
    ).strip()
    if not final_url or final_url == short_url:
        raise ProcessorError(
            f"Could not resolve shortlink {short_url!r} (got: {final_url!r})"
        )
    return final_url


def _version_from_url(url):
    """Extract a version string from a Video Copilot download filename."""
    # Strip query string, then take the last path component
    filename = url.split("?")[0].split("/")[-1]
    match = re.search(r"_([\d]+\.[\d.]+)_", filename)
    if not match:
        raise ProcessorError(
            f"Could not extract version from filename {filename!r}"
        )
    return match.group(1)


class VideoCopilotURLProvider(Processor):
    """Finds a Video Copilot product's Mac download URL and version from the
    products/m1 page. Works for all products listed there, including free
    plugins (FX Console, Saber, Orb, Color Vibrance, VC Reflect) and
    licensed products (Element 3D, Optical Flares, Heat Distortion)."""

    description = __doc__
    input_variables = {
        "product_name": {
            "required": True,
            "description": (
                "Product name as it appears on the Video Copilot m1 products page, "
                "e.g. 'FX Console', 'Optical Flares', 'Saber', 'Element 3D', 'Orb', "
                "'Heat Distortion', 'Color Vibrance', 'VC Reflect'."
            ),
        },
        "products_url": {
            "required": False,
            "description": "Video Copilot products page to scrape.",
            "default": PRODUCTS_URL,
        },
    }
    output_variables = {
        "url": {
            "description": "Final Mac download URL for the product.",
        },
        "version": {
            "description": "Version number extracted from the download filename.",
        },
    }

    def main(self):
        product_name = self.env["product_name"]
        products_url = self.env.get("products_url", PRODUCTS_URL)

        # Fetch the products page
        page_html = _curl(["-sL", products_url])

        # Find the product's Mac download URL.
        # Anchor to the 'recent-item-title' card class to avoid false matches
        # from navigation menus that also list product names earlier in the page.
        pattern = re.compile(
            r"recent-item-title[^>]*>\s*"
            + re.escape(product_name)
            + r".*?href=(['\"])(https?://[^'\"]+)\1[^>]*>\s*<i\s+class=['\"]fa vc-icon-apple['\"]",
            re.DOTALL | re.IGNORECASE,
        )
        match = pattern.search(page_html)
        if not match:
            raise ProcessorError(
                f"Could not find a Mac download URL for {product_name!r} "
                f"on {products_url}"
            )

        raw_url = match.group(2)
        self.output(f"Found URL on page: {raw_url[:80]}")

        # Resolve shortlinks; use signed CloudFront URLs directly
        if SHORTLINK_HOST in raw_url:
            final_url = _resolve_shortlink(raw_url)
        else:
            final_url = raw_url

        version = _version_from_url(final_url)

        self.env["url"] = final_url
        self.env["version"] = version
        self.output(f"URL: {final_url[:80]}")
        self.output(f"Version: {version}")


if __name__ == "__main__":
    PROCESSOR = VideoCopilotURLProvider()
    PROCESSOR.execute_shell()
