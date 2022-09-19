import re
import os
import numpy as np
import argparse
import io

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

    def check_params(self):
        '''
        Check if console arguments are provided. The arguments are handled by the ArgumentParser class.
        Parameters:
        Returns:

        '''
        parser = argparse.ArgumentParser()
        parser.add_argument(dest='local_path', type=self.path_exists, help='')
        parser.add_argument(dest='remote_path', type=self.remote_path_exists, help='')
        parser.add_argument('-r', '--resync', dest='resync', action='store_true', help='Resync both local and remote with the rclone bisync --resync command')
        parser.add_argument('-i', '--init', dest='init', action='store_true', help='Perform initial sync by creating specified directories and run rclone sync')
        parser.add_argument('-b', '--backsync', dest='backsync', action='store_true', help='Run rclone sync but with remote to local order')
        parser.add_argument('-e', '--every_minutes', dest='every_minutes', type=float, help='Schedule remote-local sync every x minutes', nargs=1)

        args = parser.parse_args()

        self.local_path = args.local_path
        self.remote_path = args.remote_path
        self.flags = {'resync' : args.resync, 'init' : args.init, 'backsync' : args.backsync}
        self.every_minutes = args.every_minutes[0] if args.every_minutes else 5

    def path_exists(self, s):
        if os.path.exists(s):
            return s
        else:
            raise argparse.ArgumentTypeError(f"readable_dir:{s} is not a valid path")

    def remote_path_exists(self, s):
        re_path = "(/[a-zA-Z0-9_\s]+){1}" # e.g. /home/user/Documents
        re_rem = "([a-zA-Z0-9]+:)" # e.g. GoogleDrive:

        if re.fullmatch('{}{}'.format(re_rem, re_path), s) == None:
            raise argparse.ArgumentTypeError(f'{s} is not a valid remote path')

        remote = s.split(':')[0]

        output = os.popen("rclone listremotes --long")
        remote_list = output.read().split()
        if remote + ":" in remote_list[::2]:
            pos = remote_list.index(remote + ":")
            self.remote_type = remote_list[pos+1]
            if self.remote_type != "drive":
                raise argparse.ArgumentError(f"The type of the given remote {remote} is not 'drive', and therefore currently not supported")
        else: raise argparse.ArgumentTypeError(f'{remote} is not a valid remote')
        return s


    def get_arguments(self):
        return self.local_path, self.remote_path, self.remote_type, self.flags, self.every_minutes