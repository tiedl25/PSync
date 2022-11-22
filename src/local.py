from importlib.resources import path
import os
from os.path import basename
import inotify.adapters
import pathlib
import threading
import queue
import time

class Local:
    lock = False

    def __init__(self, local_path, remote_path, logger):
        self.local_path = local_path
        self.remote_path = remote_path
        self.intfy = inotify.adapters.InotifyTree(self.local_path, mask=(inotify.constants.IN_MOVE | 
                                                                    inotify.constants.IN_DELETE | 
                                                                    inotify.constants.IN_CREATE | 
                                                                    inotify.constants.IN_MODIFY | 
                                                                    inotify.constants.IN_ATTRIB))                                              
        self.extensions = ['.part']
        self.logger = logger

    def options(self, type_names, dir_path, filename, q):
        '''
        Determines rclone command from the inotify mask
        '''
        extension = pathlib.Path(filename).suffix

        if extension in self.extensions: 
            logger.log(f'Skipping {filename} because of extension')
            return '', False

        if filename[0] in ['.', '#']:
            logger.log(f'Skipping {filename} because it is a hidden file')
            return '', False

        # defines remote path in rclone
        dest = self.remote_path + dir_path.split(self.local_path)[1]

        # boolean value -> determines if file/folder has to be copied
        copy = type_names[0] == 'IN_MOVED_TO' or type_names[0] ==  'IN_CREATE' or type_names[0] ==  'IN_MODIFY' or type_names[0] ==  'IN_ATTRIB'

        if (type_names[0] == 'IN_MOVED_FROM' and len(type_names) == 1) or (type_names[0] == 'IN_DELETE' and len(type_names) == 1):
            return """rclone delete \"{}/{}\"""".format(dest, filename), False

        elif copy and len(type_names) == 1:
            return """rclone copy \"{}/{}\" \"{}\"""".format(dir_path, filename, dest), False

        elif (type_names[0] == 'IN_MOVED_FROM' and type_names[1] == 'IN_ISDIR') or (type_names[0] == 'IN_DELETE' and type_names[1] == 'IN_ISDIR'):
            return """rclone purge \"{}/{}\"""".format(dest, filename), False

        elif copy and type_names[1] == 'IN_ISDIR':
            return """rclone sync -v \"{}/{}\" \"{}/{}\"""".format(dir_path, filename, dest, filename), True

    def check_if_child(self, child, parent):
        return child.startswith(parent)

    def check_if_trueChange(self, dir_path, filename, q):
        rel_dirpath = (dir_path.split(self.local_path)[1])[1:]
        rel_path = f'{rel_dirpath}/{filename}' if rel_dirpath != '' else filename
        try:
            lol = q.get(timeout=2)
        except:
            lol = ''
        if rel_path == lol: return False
        else: return True

    def change_listener(self, remote_changes, local_changes):
        for event in self.intfy.event_gen(yield_nones=False):
            (_, type_names, dirpath, filename) = event
            if self.check_if_trueChange(dirpath, filename, remote_changes):
                local_changes.put([type_names, dirpath, filename])
                Local.lock = True
                loger.debug(local_changes.qsize())

    def sync_service(self, remote_changes, local_changes):
        com = ''
        is_child = False

        while(True):
            try: 
                event = local_changes.get(timeout=1)
            except: event = []

            if event != []:
                com, is_child = self.options(event[0], event[1], event[2], remote_changes)
                if is_child:
                    while local_changes.empty() == False:
                        tmp = local_changes.queue[0]
                        if self.check_if_child(f'{tmp[1]}/{tmp[2]}', f'{event[1]}/{event[2]}'):
                            local_changes.get()

                    is_child = False

            if com!='': 
                self.logger.run(com)
                com = ''
            Local.lock = True if local_changes.qsize() > 0 else False

    def run(self, remote_changes):
        local_changes = queue.Queue()

        ch = threading.Thread(target=self.change_listener, args=(remote_changes, local_changes,))
        ss = threading.Thread(target=self.sync_service, args=(remote_changes, local_changes,))

        ch.start()
        ss.start()
