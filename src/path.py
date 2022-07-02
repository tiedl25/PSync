import re
import os

class Path:
    _path = ""
    _remote = ""
    _remote_path = ""
    _remote_type = ""
    _flags = {"resync" : False, "bidirsync" : False}

    def __init__(this, args):
        this._check_path(args)
        this._norm_arguments(args)
        this._check_remote()
    
    def _check_path(this, args):
        re_arg = "(--[a-z]*[\s])" # e.g. --resync
        re_path = "(/[a-zA-Z0-9_\s]+)" # e.g. /home/user/Documents
        re_rem = "[a-zA-Z0-9]+:?" # e.g. GoogleDrive:

        if re.fullmatch("{}*{}+[\s]{}(:{{1}}{})?".format(re_arg, re_path, re_rem, re_path), " ".join(args)) == None:
            print("Format of request isn't correct")
            print("Type psync -h odr psync --help for examples")
            quit()

    def _norm_arguments(this, args):
        this._path = args[len(args)-2]

        sp = re.split(":", args[len(args)-1])
        this._remote = sp[0]
        this._remote_path = sp[1]

        for i in (0, len(args)-3):
            this._flags[re.sub("--", "", args[i])] = True

    def _check_remote(this):
        output = os.popen("rclone listremotes --long")
        remote_list = output.read().split()
        if this._remote + ":" in remote_list[::2]:
            pos = remote_list.index(this._remote + ":")
            if remote_list[pos+1] != "drive":
                print("The type of the given remote is not 'drive', and therefore currently not supported")
        else: print("The given remote is misspelled")


    def get_arguments(this):
        return this._path, this._remote, this._remote_path, this._flags