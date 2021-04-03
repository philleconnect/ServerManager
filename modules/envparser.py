#!/usr/bin/env python3

# SchoolConnect Server-Manager - env file parser (rewritten to use the comments above a key-value pair)
# © 2021 Johannes Kreutz.

# Class definition
class envParser:
    def __init__(self, path):
        self.__path = path

    # Return the environment object for the given file
    def getEnvironment(self):
        envList = []
        with open(self.__path, "r") as f:
            lastComment = ""
            for line in f.readlines():
                if line.startswith("#"):
                    lastComment = line.strip()
                else:
                    if "=" in line:
                        l = line.split("=")
                        mutable = True if lastComment.endswith(" MU") or lastComment.endswith(" UM") or lastComment.endswith(" M") else False
                        useValue = True if lastComment.endswith(" MU") or lastComment.endswith(" UM") or lastComment.endswith(" U") else False
                        private = False if lastComment.endswith(" S") else True
                        if lastComment.endswith(" MU") or lastComment.endswith(" UM"):
                            lastComment = lastComment[:-2]
                        if lastComment.endswith(" U") or lastComment.endswith(" M") or lastComment.endswith(" S"):
                            lastComment = lastComment[:-1]
                        if lastComment.startswith("#"):
                            lastComment = lastComment[1:]
                        lastComment = lastComment.strip()
                        env = {
                            "name": l[0].strip(),
                            "description": lastComment,
                            "mutable": mutable,
                            "private": private,
                        }
                        if useValue:
                            env["default"] = l[1].strip()
                        envList.append(env)
                        lastComment = ""
                    elif len(line) <= 1:
                        continue
                    else:
                        return None
        return envList
