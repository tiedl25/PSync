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
            destpath = self.local_path + dirpath.removeprefix(self.remote_path)
            command = f'rclone copy {self.verbose}"{dirpath}/{filename}" "{destpath}/{filename}"'
        else: 
            destpath = self.remote_path + dirpath.removeprefix(self.local_path)
            command = f'rclone sync {self.verbose}"{dirpath}/{filename}" "{destpath}/{filename}"'
        self.logger.log(command)
        os.system(command)

    def copy(self, dirpath, filename, local=False):
        if local: 
            destpath = self.local_path + dirpath.removeprefix(self.remote_path)
            command = f'rclone copy {self.verbose}"{dirpath}/{filename}" "{destpath}"'
        else: 
            destpath = self.remote_path + dirpath.removeprefix(self.local_path)
            command = f'rclone copy {self.verbose}"{dirpath}/{filename}" "{destpath}"'

        self.logger.log(command)
        os.system(command)

    def purge(self, dirpath, foldername, local=False):
        if local: 
            destpath = self.local_path + dirpath.removeprefix(self.remote_path)
            command = f'rm -R "{destpath}/{foldername}"'
        else: 
            destpath = self.remote_path + dirpath.removeprefix(self.local_path)
            command = f'rclone purge {self.verbose}"{destpath}/{foldername}"'
        
        self.logger.log(command)
        os.system(command)

    def delete(self, dirpath, filename, local=False):
        if local: 
            destpath = self.local_path + dirpath.removeprefix(self.remote_path)
            command = f'rm -R "{destpath}/{filename}"'
        else: 
            destpath = self.remote_path + dirpath.removeprefix(self.local_path)
            command = f'rclone delete {self.verbose}"{destpath}/{filename}"'

        self.logger.log(command)
        os.system(command)

    def rename(self, dirpath, filename, oldname, local=False):
        if local:
            destpath = self.local_path + dirpath.removeprefix(self.remote_path)
            command = f'mv "{destpath}/{oldname}" "{destpath}/{filename}"'
        else:
            destpath = self.remote_path + dirpath.removeprefix(self.local_path)
            command = f'rclone moveto {self.verbose}"{destpath}/{oldname}" "{destpath}/{filename}"'
        
        self.logger.log(command)
        os.system(command)

    def move(self, dirpath, filename, oldpath, local=False):
        if local:
            destpath = self.local_path + dirpath.removeprefix(self.remote_path)
            olddestpath = self.local_path + oldpath.removeprefix(self.remote_path)
            command = f'mv "{olddestpath}/{filename}" "{destpath}/{filename}"'
        else:
            destpath = self.remote_path + dirpath.removeprefix(self.local_path)
            olddestpath = self.remote_path + oldpath.removeprefix(self.local_path)
            command = f'rclone moveto {self.verbose}"{olddestpath}/{filename}" "{destpath}/{filename}"'

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