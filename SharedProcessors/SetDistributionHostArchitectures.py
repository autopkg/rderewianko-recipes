#!/usr/local/autopkg/python
# SetDistributionHostArchitectures.py
#
# Sets the `hostArchitectures` attribute on the <options> element of a flat
# pkg's Distribution file.
#
# Why this exists: macOS Installer.app reads `hostArchitectures` from the
# Distribution to decide which CPU architectures the installer is allowed to
# run on. When the attribute is missing, it defaults to x86_64-only — which
# means installing on Apple Silicon prompts for Rosetta 2, even if every
# binary in the payload is already universal. Adding `arm64` (or
# `arm64,x86_64`) suppresses the prompt.
#
# Usage in a .pkg.recipe:
#
#     FlatPkgUnpacker          → expand the vendor pkg
#     SetDistributionHostArchitectures  ← this processor
#     FlatPkgPacker            → re-flatten the patched pkg
#
# Modeled on the Distribution-editing pattern in
# autopkg/recipes/AdobeReader/AdobeReaderRepackager.py.

import os
import xml.etree.ElementTree as ET

from autopkglib import Processor, ProcessorError

__all__ = ["SetDistributionHostArchitectures"]

DEFAULT_ARCHES = "arm64,x86_64"


class SetDistributionHostArchitectures(Processor):
    """Sets the hostArchitectures attribute on the <options> element of an
    expanded flat pkg's Distribution file, suppressing the Rosetta 2 install
    prompt on Apple Silicon for pkgs whose vendor forgot to set it."""

    description = __doc__
    input_variables = {
        "expanded_pkg_path": {
            "required": True,
            "description": (
                "Path to an expanded flat pkg directory (the output of "
                "FlatPkgUnpacker). Must contain a Distribution file at the "
                "top level."
            ),
        },
        "host_architectures": {
            "required": False,
            "description": (
                "Comma-separated list of architectures to allow the installer "
                "to run on. Defaults to 'arm64,x86_64'."
            ),
            "default": DEFAULT_ARCHES,
        },
    }
    output_variables = {
        "distribution_modified": {
            "description": (
                "True if the Distribution file was changed, False if the "
                "attribute was already set to the requested value."
            ),
        },
    }

    def main(self):
        expanded_pkg_path = self.env["expanded_pkg_path"]
        arches = self.env.get("host_architectures", DEFAULT_ARCHES)

        distribution_path = os.path.join(expanded_pkg_path, "Distribution")
        if not os.path.isfile(distribution_path):
            raise ProcessorError(
                f"No Distribution file found at {distribution_path}. "
                "This processor only works on distribution-style flat pkgs."
            )

        try:
            tree = ET.parse(distribution_path)
        except ET.ParseError as err:
            raise ProcessorError(
                f"Failed to parse {distribution_path}: {err}"
            )

        root = tree.getroot()
        # The root is <installer-gui-script> (or, rarely, <installer-script>).
        # <options> is a direct child; create it if missing.
        options = root.find("options")
        if options is None:
            self.output("No <options> element found; creating one.")
            options = ET.SubElement(root, "options")

        current = options.get("hostArchitectures")
        if current == arches:
            self.output(
                f"hostArchitectures already set to {arches!r}; no change."
            )
            self.env["distribution_modified"] = False
            return

        if current:
            self.output(
                f"Updating hostArchitectures: {current!r} → {arches!r}"
            )
        else:
            self.output(f"Setting hostArchitectures to {arches!r}")
        options.set("hostArchitectures", arches)

        tree.write(distribution_path, encoding="utf-8", xml_declaration=True)
        self.env["distribution_modified"] = True


if __name__ == "__main__":
    PROCESSOR = SetDistributionHostArchitectures()
    PROCESSOR.execute_shell()
