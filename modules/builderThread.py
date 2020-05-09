#!/usr/bin/env python3

# SchoolConnect Server-Manager - image builder thread class
# © 2019 Johannes Kreutz.

# Include dependencies
import threading

# Include modules
import modules.image as image
import modules.container as container

# Class definitions
class builderThread(threading.Thread):
    def __init__(self, threadId, queue, lock, containerArray):
        threading.Thread.__init__(self)
        self.__queue = queue
        self.__id = threadId
        self.__lock = lock
        self.__containers = containerArray

    # Thread main runner
    def run(self):
        self.__lock.acquire()
        containerObject = self.__queue.get()
        self.__lock.release()
        image = self.__buildImage(containerObject)
        container = self.__buildContainer(image, containerObject)
        returnObject = {"container":container,"image":image}
        self.__containers.append(returnObject)

    # Build or pull image for one container
    def __buildImage(self, object):
        imageObject = image.image(False, object["object"]["name"])
        return imageObject.create(object["object"], object["image"])

    # Build a container with given image and description
    def __buildContainer(self, image, object):
        containerObject = container.container(False, None)
        containerObject.create(image, object["object"], object["volumeSource"])
        return containerObject
