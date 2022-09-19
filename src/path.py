import re
import os
import numpy as np
import argparse

class Path:
    '''
    Arguments:
        local_path
        remote_path
        remote_type
        flags
    '''
    def __init__(self):
        self.check_params()
        self.check_remote()

    def check_params(self):
        '''
        Check if console arguments are provided. The arguments are handled by the ArgumentParser class.
        Parameters:
        Returns:

        '''
        parser = argparse.ArgumentParser()
        parser.add_argument(dest='local_path', type=str, help='')
        parser.add_argument(dest='remote_path', type=str, help='')
        parser.add_argument('-r', '--resync', dest='resync', action='store_true', help='Resync both local and remote with the rclone bisync --resync command')
        parser.add_argument('-i', '--init', dest='init', action='store_true', help='Perform initial sync by creating specified directories and run rclone sync')
        parser.add_argument('-b', '--backsync', dest='backsync', action='store_true', help='Run rclone sync but with remote to local order')
        parser.add_argument('-e', '--every_minutes', dest='every_minutes', type=float, help='Schedule remote-local sync every x minutes', nargs=1)

        args = parser.parse_args()

        self.local_path = args.local_path
        self.remote_path = args.remote_path
        self.flags = {'resync' : args.resync, 'init' : args.init, 'backsync' : args.backsync}
        self.every_minutes = args.every_minutes[0] if args.every_minutes else 5

    def dir_path(path):
        if os.path.isdir(path):
            return path
        else:
            raise argparse.ArgumentTypeError(f"readable_dir:{path} is not a valid path")

    def rem_path(path):
        pass

    def check_remote(self):
        re_path = "(/[a-zA-Z0-9_\s]+){1}" # e.g. /home/user/Documents
        re_rem = "([a-zA-Z0-9]+:)" # e.g. GoogleDrive:

        if re.fullmatch('{}{}'.format(re_rem, re_path), self.remote_path) == None:
            print('Not valid')
            os._exit(0)

        remote = self.remote_path.split(':')[0]

        output = os.popen("rclone listremotes --long")
        remote_list = output.read().split()
        if remote + ":" in remote_list[::2]:
            pos = remote_list.index(remote + ":")
            self.remote_type = remote_list[pos+1]
            if self.remote_type != "drive":
                print("The type of the given remote is not 'drive', and therefore currently not supported")
        else: print("The given remote is misspelled")


    def get_arguments(self):
        return self.local_path, self.remote_path, self.remote_type, self.flags, self.every_minutes