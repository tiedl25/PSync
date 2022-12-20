from importlib.resources import path
import os
from os.path import basename
import remote
import inotify.adapters
import pathlib
import threading
import queue
import time

class Local:
    lock = False

    def __init__(self, local_path, remote_path, logger, rclone):
        self.local_path = local_path
        self.remote_path = remote_path
        self.intfy = inotify.adapters.InotifyTree(self.local_path, mask=(inotify.constants.IN_MOVE | 
                                                                    inotify.constants.IN_DELETE | 
                                                                    inotify.constants.IN_CREATE | 
                                                                    inotify.constants.IN_MODIFY | 
                                                                    inotify.constants.IN_ATTRIB))                                              
        self.extensions = ['.part']
        self.logger = logger
        self.rclone = rclone

    def check_if_child(self, child, parent):
        return child.startswith(parent)

    def check_if_trueChange(self, dir_path, filename, q, tmp):
        ''' 
        Check if the path also exists in the remote changes, and if so delete it.
        '''
        rel_dirpath = (dir_path.split(self.local_path)[1])[1:]
        rel_path = f'{rel_dirpath}/{filename}' if rel_dirpath != '' else filename

        for i in tmp:
            if rel_path == i: 
                q.get(timeout=2)
                tmp.remove(i)
                return False

        return True

    def check_if_necessary(self, dir_path, filename, q):
        ''' 
        Ceck if multiple paths with the same name exist in the local changes, and if so delete the first one.
        '''
        rel_dirpath = (dir_path.split(self.local_path)[1])[1:]
        rel_path = f'{rel_dirpath}/{filename}' if rel_dirpath != '' else filename

        lol = f'{dir_path}/{filename}'

        tmp = list(q.queue)

        for i in tmp:
            lol2 = f'{i[1]}/{i[2]}'
            if lol == lol2: 
                
                q.get(timeout=2)
                return False

        return True

    def options(self, type_names, dir_path, filename, remote_changes, remote_changes_tmp, local_changes):
        '''
        Determines rclone command from the inotify mask
        '''

        extension = pathlib.Path(filename).suffix

        if extension in self.extensions: 
            self.logger.log(f'Skipping {filename} because of extension')
            return False

        if filename == '':
            self.logger.log(f'Skipping {dir_path} with {type_names} because there is no filename')
            return False

        if filename[0] in ['.', '#']:
            self.logger.log(f'Skipping {filename} because it is a hidden file')
            return False

        if not self.check_if_trueChange(dir_path, filename, remote_changes, remote_changes_tmp):
            self.logger.log(f'Skipping {filename} because the change is caused by backsync')
            return False    

        #if not self.check_if_necessary(dir_path, filename, local_changes):
        #    self.logger.log(f"Skipping {filename} because it isn't necessary")
        #    return False

        # boolean value -> determines if file/folder has to be copied
        copy = type_names[0] == 'IN_MOVED_TO' or type_names[0] ==  'IN_CREATE' or type_names[0] ==  'IN_MODIFY' or type_names[0] ==  'IN_ATTRIB'

        if (type_names[0] == 'IN_MOVED_FROM' and len(type_names) == 1) or (type_names[0] == 'IN_DELETE' and len(type_names) == 1):
            self.rclone.delete(filename)
            return False

        elif copy and len(type_names) == 1:
            self.rclone.copy(dir_path, filename)
            return False

        elif (type_names[0] == 'IN_MOVED_FROM' and type_names[1] == 'IN_ISDIR') or (type_names[0] == 'IN_DELETE' and type_names[1] == 'IN_ISDIR'):
            self.rclone.purge(filename)
            return False

        elif copy and type_names[1] == 'IN_ISDIR':
            self.rclone.sync(dir_path, filename)
            return True

    def change_listener(self, remote_changes, local_changes):
        for event in self.intfy.event_gen(yield_nones=False):
            (_, type_names, dirpath, filename) = event

            local_changes.put([type_names, dirpath, filename])
            Local.lock = True

    def sync_service(self, remote_changes, local_changes):
        com = ''
        is_child = False

        locked = False
        remote_changes_tmp = []

        parent = ''

        while(True):
            # wait until backsync is finished
            while remote.Remote.lock == True:
                time.sleep(1)
                locked = True

            # after backsync is finished get remote_changes and store in list for efficient access
            if locked:
                remote_changes_tmp = list(remote_changes.queue)
                locked = False

            try: 
                event = local_changes.get(timeout=1)
            except: event = []

            if event != []:
                is_child = self.options(event[0], event[1], event[2], remote_changes, remote_changes_tmp, local_changes)

            if is_child:
                local_changes_tmp = list(local_changes.queue)
                for tmp in local_changes_tmp:
                    if self.check_if_child(f'{tmp[1]}/{tmp[2]}', f'{event[1]}/{event[2]}'):
                        local_changes.get()

                is_child = False
            Local.lock = True if local_changes.qsize() > 0 else False

    def run(self, remote_changes):
        local_changes = queue.Queue()

        ch = threading.Thread(target=self.change_listener, args=(remote_changes, local_changes,))
        ss = threading.Thread(target=self.sync_service, args=(remote_changes, local_changes,))

        ch.start()
        ss.start()
