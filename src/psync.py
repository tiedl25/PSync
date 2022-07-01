import os
from os.path import basename
import inotify.adapters
import sys
import re

class Psync:
    _flags = {"resync" : False, "bidirsync" : False}
    _path = ""
    _remote = ""
    _remote_path = ""

    def __init__(this, args):
        this._norm_arguments(args)
        this._intfy = inotify.adapters.InotifyTree(this._path, mask=(inotify.constants.IN_MOVE | 
                                                                    inotify.constants.IN_DELETE | 
                                                                    inotify.constants.IN_CREATE | 
                                                                    inotify.constants.IN_MODIFY | 
                                                                    inotify.constants.IN_ATTRIB))

    def _options(this, type_names, filename, dir_path):
        # defines remote path in rclone
        if this._remote_path == "": dest = this._remote + ":/" + basename(this._path) + dir_path.split(this._path)[1]
        else: dest = this._remote + ":/" + dir_path.split(this._path)[1]

        # boolean value -> determines if file/folder has to be copied
        copy = type_names[0] == 'IN_MOVED_TO' or type_names[0] ==  'IN_CREATE' or type_names[0] ==  'IN_MODIFY' or type_names[0] ==  'IN_ATTRIB'

        if (type_names[0] == 'IN_MOVED_FROM' and len(type_names) == 1) or (type_names[0] == 'IN_DELETE' and len(type_names) == 1):
            str = """rclone delete {}/{}""".format(dest, filename)
        elif copy and len(type_names) == 1:
            str = """rclone copy {}/{} {}""".format(dir_path, filename, dest)
        elif (type_names[0] == 'IN_MOVED_FROM' and type_names[1] == 'IN_ISDIR') or (type_names[0] == 'IN_DELETE' and type_names[1] == 'IN_ISDIR'):
            str = """rclone purge {}/{}""".format(dest, filename)
        elif copy and type_names[1] == 'IN_ISDIR':
            str = """rclone copy {}/{} {}/{}""".format(dir_path, filename, dest, filename)

        return str
    
    def _norm_arguments(this, args):
        re_arg = "(--[a-z]*[\s])" # e.g. --resync
        re_path = "(/[a-zA-Z0-9_\s]+)" # e.g. /home/user/Documents
        re_rem = "[a-zA-Z0-9]+:?" # e.g. GoogleDrive:

        if re.fullmatch("{}*{}+[\s]{}(:{{1}}{})?".format(re_arg, re_path, re_rem, re_path), " ".join(args)) == None:
            print("Format of request isn't correct")
            print("Type psync -h odr psync --help for examples")
            quit()

        this._path = args[len(args)-2]

        sp = re.split(":", args[len(args)-1])
        this._remote = sp[0]
        this._remote_path = sp[1]
        

        for i in (0, len(args)-3):
            this._flags[re.sub("--", "", args[i])] = True

    def run(this):
        for event in this._intfy.event_gen(yield_nones=False):
            (_, type_names, dirpath, filename) = event

            str = this._options(type_names, filename, dirpath)
            print(str)
            #os.system(str)



def main():
    p = Psync(["--resync", "/home/tiedl25/Bidir", "GoogleDrive:"])
    #p = Psync(sys.argv)

    p.run()


if __name__ == '__main__':
    main()