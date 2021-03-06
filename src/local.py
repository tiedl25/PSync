import os
from os.path import basename
import inotify.adapters
import sys
import re

class Local:
    def __init__(this, path, remote, remote_path, flags):
        this._path = path
        this._remote = remote
        this._remote_path = remote_path
        this._flags = flags
        this._intfy = inotify.adapters.InotifyTree(this._path, mask=(inotify.constants.IN_MOVE | 
                                                                    inotify.constants.IN_DELETE | 
                                                                    inotify.constants.IN_CREATE | 
                                                                    inotify.constants.IN_MODIFY | 
                                                                    inotify.constants.IN_ATTRIB))

    def _options(this, type_names, filename, dir_path):
        # defines remote path in rclone
        dest = this._remote + ":" + this._remote_path + dir_path.split(this._path)[1]

        # boolean value -> determines if file/folder has to be copied
        copy = type_names[0] == 'IN_MOVED_TO' or type_names[0] ==  'IN_CREATE' or type_names[0] ==  'IN_MODIFY' or type_names[0] ==  'IN_ATTRIB'

        str = ""

        if (type_names[0] == 'IN_MOVED_FROM' and len(type_names) == 1) or (type_names[0] == 'IN_DELETE' and len(type_names) == 1):
            str = """rclone delete \"{}/{}\"""".format(dest, filename)
        elif copy and len(type_names) == 1:
            str = """rclone copy \"{}/{}\" \"{}\"""".format(dir_path, filename, dest)
        elif (type_names[0] == 'IN_MOVED_FROM' and type_names[1] == 'IN_ISDIR') or (type_names[0] == 'IN_DELETE' and type_names[1] == 'IN_ISDIR'):
            str = """rclone purge \"{}/{}\"""".format(dest, filename)
        elif copy and type_names[1] == 'IN_ISDIR':
            str = """rclone copy \"{}/{}\" \"{}/{}\"""".format(dir_path, filename, dest, filename)

        return str

    def _check_flags(this):
        if this._flags["help"] or this._flags["h"]:
            print("Currently not available")  
            os._exit(0)      
        if this._flags["backsync"]:
            print("rclone sync {}:{} {}".format(this._remote, this._remote_path, this._path))
            #os.system("rclone sync {}:{} {}".format(this._remote, this._remote_path, this._path))
        if this._flags["resync"]:
            print("rclone bisync {} {}:{}".format(this._path, this._remote, this._remote_path))
            #os.system("rclone sync {}:{} {}".format(this._remote, this._remote_path, this._path))            
        if this._flags["init"]:
            print("rclone bisync --resync {} {}:{}".format(this._path, this._remote, this._remote_path))
            #os.system("rclone sync {}:{} {}".format(this._remote, this._remote_path, this._path))

    def run(this):
        this._check_flags()
        for event in this._intfy.event_gen(yield_nones=False):
            (_, type_names, dirpath, filename) = event

            str = this._options(type_names, filename, dirpath)
            print(str)
            if str!="": os.system(str) 