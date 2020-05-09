#!/usr/bin/env python3

# SchoolConnect Server-Manager - essentials class
# © 2019 Johannes Kreutz.

# Include dependencies
import random
import string

# Class definition
class essentials:
    # Returns a random string with the given length
    @staticmethod
    def randomString(length):
        chars = string.ascii_lowercase + string.ascii_uppercase + string.digits
        return "".join(random.choice(chars) for i in range(length))
