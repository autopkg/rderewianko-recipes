#!/usr/local/autopkg/python
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

import os
import subprocess
from autopkglib import Processor, ProcessorError


__all__ = ["Unquarantine"]


class Unquarantine(Processor):
    """Recursively strips the com.apple.quarantine extended attribute from a path.

    Used for un-notarized binaries extracted from downloaded archives, so the
    quarantine xattr inherited from the archive doesn't end up baked into the
    pkg payload."""

    input_variables = {
        "path": {
            "description": "File or directory to strip com.apple.quarantine from.",
            "required": True,
        },
    }
    output_variables = {}

    description = __doc__

    def main(self):
        path = self.env["path"]
        if not os.path.exists(path):
            raise ProcessorError("Path does not exist: %s" % path)

        try:
            subprocess.run(
                ["/usr/bin/xattr", "-dr", "com.apple.quarantine", path],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise ProcessorError("xattr failed: %s" % e)

        self.output("Stripped com.apple.quarantine from %s" % path)


if __name__ == "__main__":
    processor = Unquarantine()
    processor.execute_shell()
