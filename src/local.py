from importlib.resources import path
import os
from os.path import basename
import inotify.adapters
import pathlib

class Local:
    def __init__(self, local_path, remote_path, flags):
        self.local_path = local_path
        self.remote_path = remote_path
        self.flags = flags
        self.intfy = inotify.adapters.InotifyTree(self.local_path, mask=(inotify.constants.IN_MOVE | 
                                                                    inotify.constants.IN_DELETE | 
                                                                    inotify.constants.IN_CREATE | 
                                                                    inotify.constants.IN_MODIFY | 
                                                                    inotify.constants.IN_ATTRIB))                                              
        self.extensions = ['.part']

    def options(self, type_names, filename, dir_path, q):
        extension = pathlib.Path(filename).suffix
        if extension in self.extensions: 
            print(f'Skipping {filename} because of extension')
            return ''

        if filename[0] in ['.', '#']:
            print(f'Skipping {filename} because it is a hidden file')
            return ''

        rel_dirpath = (dir_path.split(self.local_path)[1])[1:]
        rel_path = f'{rel_dirpath}/{filename}' if rel_dirpath != '' else filename
        try:
            lol = q.get(timeout=1)
        except:
            lol = ''
        if rel_path == lol: return ''

        # defines remote path in rclone
        dest = self.remote_path + dir_path.split(self.local_path)[1]

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

    def check_flags(self):   
        if self.flags["backsync"]:
            print("rclone sync {} {}".format(self.remote_path, self.local_path))
            os.system("rclone sync {} {}".format(self.remote_path, self.local_path))
        if self.flags["resync"]:
            print("rclone bisync --resync {} {}".format(self.local_path, self.remote_path))
            os.system("rclone bisync --resync {} {}".format(self.local_path, self.remote_path))            
        if self.flags["init"]:
            print("rclone sync  --delete-before --exclude '.*' --delete-excluded {} {}".format(self.local_path, self.remote_path))
            os.system("rclone sync  --delete-before --exclude '.*' --delete-excluded {} {}".format(self.local_path, self.remote_path))

    def run(self, q):
        self.check_flags()
        q.get()

        for event in self.intfy.event_gen(yield_nones=False):
            (_, type_names, dirpath, filename) = event
            com = self.options(type_names, filename, dirpath, q)
            
            if com!="": 
                print(com)
                os.system(com) 