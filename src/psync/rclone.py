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
            loc = 'Remote: '
        else: 
            destpath = self.remote_path + dirpath.removeprefix(self.local_path)
            command = f'rclone copy {self.verbose}"{dirpath}/{filename}" "{destpath}/{filename}"'
            loc = 'Local: '

        output = loc + f'Copy "{dirpath}/{filename}" to "{destpath}/{filename}"'
        self.logger.log(output, 'green')
        os.system(command)

    def copy(self, dirpath, filename, local=False):
        if local: 
            destpath = self.local_path + dirpath.removeprefix(self.remote_path)
            command = f'rclone copy {self.verbose}"{dirpath}/{filename}" "{destpath}"'
            loc = 'Remote: '
        else: 
            destpath = self.remote_path + dirpath.removeprefix(self.local_path)
            command = f'rclone copy {self.verbose}"{dirpath}/{filename}" "{destpath}"'
            loc = 'Local: '

        output = loc + f'Copy "{dirpath}/{filename}" to "{destpath}"'
        self.logger.log(output, 'green')
        os.system(command)

    def purge(self, dirpath, foldername, local=False):
        if local: 
            destpath = self.local_path + dirpath.removeprefix(self.remote_path)
            command = f'trash-put "{destpath}/{foldername}"'
            loc = 'Remote: '
        else: 
            destpath = self.remote_path + dirpath.removeprefix(self.local_path)
            command = f'rclone purge {self.verbose}"{destpath}/{foldername}"'
            loc = 'Local: '

        output = loc + f'Delete "{destpath}/{foldername}"'
        self.logger.log(output, 'green')
        os.system(command)

    def delete(self, dirpath, filename, local=False):
        if local: 
            destpath = self.local_path + dirpath.removeprefix(self.remote_path)
            command = f'trash-put "{destpath}/{filename}"'
            loc = 'Remote: '
        else: 
            destpath = self.remote_path + dirpath.removeprefix(self.local_path)
            command = f'rclone delete {self.verbose}"{destpath}/{filename}"'
            loc = 'Local: '

        output = loc + f'Delete "{destpath}/{filename}"'
        self.logger.log(output, 'green')
        os.system(command)

    def rename(self, dirpath, filename, oldname, local=False):
        if local:
            destpath = self.local_path + dirpath.removeprefix(self.remote_path)
            command = f'mv "{destpath}/{oldname}" "{destpath}/{filename}"'
            loc = 'Remote: '
        else:
            destpath = self.remote_path + dirpath.removeprefix(self.local_path)
            command = f'rclone moveto {self.verbose}"{destpath}/{oldname}" "{destpath}/{filename}"'
            loc = 'Local: '
        
        output = loc + f'Rename "{destpath}/{oldname}" to "{destpath}/{filename}"'
        self.logger.log(output, 'green')
        os.system(command)

    def move(self, dirpath, filename, oldpath, local=False):
        if local:
            destpath = self.local_path + dirpath.removeprefix(self.remote_path)
            olddestpath = self.local_path + oldpath.removeprefix(self.remote_path)
            if not os.path.exists(destpath): os.makedirs(destpath)
            command = f'mv "{olddestpath}/{filename}" "{destpath}/{filename}"'
            loc = 'Remote: '
        else:
            destpath = self.remote_path + dirpath.removeprefix(self.local_path)
            olddestpath = self.remote_path + oldpath.removeprefix(self.local_path)
            command = f'rclone moveto {self.verbose}"{olddestpath}/{filename}" "{destpath}/{filename}"'
            loc = 'Local: '

        output = loc + f'Move "{olddestpath}/{filename}" to "{destpath}/{filename}"'
        self.logger.log(output, 'green')
        os.system(command)

    def restore(self, dirpath, filename, local=False):
        if local:
            destpath = self.local_path + dirpath.removeprefix(self.remote_path)
            output = subprocess.getoutput(f'echo -1 | trash-restore "{destpath}/{filename}"')
            index = output.rfind('What file to restore [0..')+25
            command = f'echo {output[index]} | trash-restore "{destpath}/{filename}"'
            loc = 'Remote: '
        
        output = loc + f'Restore "{destpath}/{filename}"'
        self.logger.log(output, 'green')
        subprocess.getoutput(command)

    def backsync(self):
        command = f'rclone sync {self.verbose}--delete-before "{self.remote_path}" "{self.local_path}"'
        self.logger.log(command, 'green')
        output = subprocess.getoutput(f'rclone sync -v --delete-before "{self.remote_path}" "{self.local_path}"')
        self.logger.log(output)
        return output  

    def init(self):
        command = f'rclone sync {self.verbose}--delete-before --exclude ".*" --delete-excluded "{self.local_path}" "{self.remote_path}"'
        self.logger.log(command, 'green')
        os.system(command)

    def bisync(self):
        command = f'rclone bisync {self.verbose}--resync "{self.local_path}" "{self.remote_path}"'
        self.logger.log(command, 'green')
        os.system(command)