#!/usr/bin/env python3

# SchoolConnect Server-Manager - env file parser (rewritten to use the comments above a key-value pair)
# © 2021 Johannes Kreutz.

# Class definition
class envParser:
    def __init__(self, path):
        self.__path = path

    # Return the environment object for the given file
    def getEnvironment(self):
        env = []
        with open(self.__path, "r") as f:
            lastComment = ""
            for line in f.readlines():
                if line.startswith("#"):
                    lastComment = line
                else:
                    if "=" in line:
                        l = line.split("=")
                        mutable = True if lastComment.endswith(" M") or lastComment.endswith(" MU") or lastComment.endswith(" UM") else False
                        useValue = True if lastComment.endswith(" U") or lastComment.endswith(" MU") or lastComment.endswith(" UM") else False
                        if lastComment.endswith(" U") or lastComment.endswith(" M"):
                            lastComment = lastComment[:2]
                        if lastComment.endswith(" MU") or lastComment.endswith(" UM"):
                            lastComment = lastComment[:3]
                        env = {
                            "name": l[0],
                            "description": lastComment,
                            "mutable": mutable,
                        }
                        if useValue:
                            env["value"] = l[1]
                        env.append(env)
                        lastComment = ""
                    else:
                        return None
        return env
