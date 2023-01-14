import os
import subprocess

class Rclone:
    def __init__(self, local_path, remote_path, verbose, logger): 
        self.local_path = local_path
        self.remote_path = remote_path
        self.verbose = '-v ' if verbose else ''
        self.logger = logger

    def sync(self, dirpath, filename, local=False):
        if local:
            destpath = self.local_path + dirpath.split(self.remote_path)[1]
            command = f'rclone copy {self.verbose}"{dirpath}/{filename}" "{destpath}/{filename}"'
        else: 
            destpath = self.remote_path + dirpath.split(self.local_path)[1]
            command = f'rclone sync {self.verbose}"{dirpath}/{filename}" "{destpath}/{filename}"'
        self.logger.log(command)
        os.system(command)

    def copy(self, dirpath, filename, local=False):
        if local: 
            destpath = self.local_path + dirpath.split(self.remote_path)[1]
            command = f'rclone copy {self.verbose}"{dirpath}/{filename}" "{destpath}"'
        else: 
            destpath = self.remote_path + dirpath.split(self.local_path)[1]
            command = f'rclone copy {self.verbose}"{dirpath}/{filename}" "{destpath}"'

        self.logger.log(command)
        os.system(command)

    def purge(self, dirpath, foldername, local=False):
        if local: 
            destpath = self.local_path + dirpath.split(self.remote_path)[1]
            command = f'rm -R "{destpath}/{foldername}"'
        else: 
            destpath = self.remote_path + dirpath.split(self.local_path)[1]
            command = f'rclone purge {self.verbose}"{destpath}/{foldername}"'
        
        self.logger.log(command)
        os.system(command)

    def delete(self, dirpath, filename, local=False):
        if local: 
            destpath = self.local_path + dirpath.split(self.remote_path)[1]
            command = f'rm -R "{destpath}/{filename}"'
        else: 
            destpath = self.remote_path + dirpath.split(self.local_path)[1]
            command = f'rclone delete {self.verbose}"{destpath}/{filename}"'

        self.logger.log(command)
        os.system(command)

    def rename(self, dirpath, filename, oldname, local=False):
        if local:
            destpath = self.local_path + dirpath.split(self.remote_path)[1]
            command = f'mv "{destpath}/{oldname}" "{destpath}/{filename}"'
        
        self.logger.log(command)
        os.system(command)

    def move(self, dirpath, filename, oldpath, local=False):
        if local:
            destpath = self.local_path + dirpath.split(self.remote_path)[1]
            olddestpath = self.local_path + oldpath.split(self.remote_path)[1]
            command = f'mv "{olddestpath}/{filename}" "{destpath}/{filename}"'

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