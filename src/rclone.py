import os
import subprocess

class Rclone:
    def __init__(self, local_path, remote_path, verbose, logger): 
        self.local_path = local_path
        self.remote_path = remote_path
        self.verbose = '-v ' if verbose else ''
        self.logger = logger

    def sync(self, dirpath, filename):
        destpath = self.remote_path + dirpath.split(self.local_path)[1]
        command = f'rclone sync {self.verbose}"{dirpath}/{filename}" "{destpath}/{filename}"'
        self.logger.log(command)
        os.system(command)

    def copy(self, dirpath, filename):
        destpath = self.remote_path + dirpath.split(self.local_path)[1]
        command = f'rclone copy {self.verbose}"{dirpath}/{filename}" "{destpath}"'
        self.logger.log(command)
        os.system(command)

    def purge(self, foldername):
        command = f'rclone purge {self.verbose}"{self.remote_path}/{foldername}"'
        self.logger.log(command)
        os.system(command)

    def delete(self, filename):
        command = f'rclone delete {self.verbose}"{self.remote_path}/{filename}"'
        self.logger.log(command)
        os.system(command)

    def backsync(self):
        command = f'rclone sync {self.verbose}--delete-before "{self.remote_path}" "{self.local_path}"'
        self.logger.log(command)
        output = subprocess.getoutput(f'rclone sync -v --delete-before "{self.remote_path}" "{self.local_path}"')
        self.logger.log(output)
        return output  

    def init(self):
        command = f'rclone sync {self.verbose}--delete-before --exclude ".*" --delete-excluded "{self.local_path}" "{self.remote_path}"'
        self.logger.log(command)
        os.system(command)

    def bisync(self):
        command = f'rclone bisync {self.verbose}--resync "{self.local_path}" "{self.remote_path}"'
        self.logger.log(command)
        os.system(command)