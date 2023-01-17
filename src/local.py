import sys
import time
import logging
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
from watchdog.events import FileSystemEventHandler

from importlib.resources import path
import os
from os.path import basename
import remote
import inotify.adapters
import pathlib
import threading
import queue
from logger import Logger
from rclone import Rclone
from datetime import datetime

class Handler(FileSystemEventHandler):
    def __init__(self, changes):
        self.changes = changes
        super().__init__()

    def on_any_event(self, event):
        
        path = event.src_path.rsplit('/', 1)

        format = ("%Y-%m-%d%H:%M:%S.%f")
        swap = {
            'deleted' : 'delete', 
            'modified' : 'modify',
            'created' : 'create',
            'moved' : 'move',
            'closed' : 'close'
        }

        change_item = {'name' : path[1], 
                        'path' : path[0], 
                        'action' : swap[event.event_type], 
                        'folder' : event.is_directory, 
                        'timestamp' : datetime.now().strftime(format)}

        # distinguish between rename and move
        if change_item['action'] == 'move': 
            new_path = event.dest_path.rsplit('/', 1)
            if path[0] == new_path[0]:
                change_item['name'] = new_path[1]
                change_item['old_name'] = path[1]
                change_item['action'] = 'rename'
            else:
                change_item['path'] = new_path[0]
                change_item['old_path'] = path[0]
        
        if not (change_item['folder'] and change_item['action'] == 'modify'):
            self.changes.put(change_item)         

class Local:
    lock = False

    def __init__(self, local_path, remote_path, logger, rclone):
        self.local_path = local_path
        self.remote_path = remote_path
                                            
        self.extensions = ['.part']
        self.logger = logger
        self.rclone = rclone

    def perform_operation(self, change_item):
        if change_item['folder']:
            if change_item['action'] == 'delete' : 
                self.rclone.purge(change_item['path'], change_item['name']),

            elif change_item['action'] == 'create' : 
                self.rclone.sync(change_item['path'], change_item['name']),

            elif change_item['action'] == 'modify' : 
                self.rclone.sync(change_item['path'], change_item['name']),

            elif change_item['action'] == 'close' : 
                self.rclone.sync(change_item['path'], change_item['name']),

            elif change_item['action'] == 'move' : 
                self.rclone.move(change_item['path'], change_item['name'], change_item['old_path']),
                
            elif change_item['action'] == 'rename' : 
                self.rclone.rename(change_item['path'], change_item['name'], change_item['old_name']),

        else:       
            if change_item['action'] == 'delete' : 
                self.rclone.delete(change_item['path'], change_item['name']),

            elif change_item['action'] == 'create' : 
                self.rclone.copy(change_item['path'], change_item['name']),

            elif change_item['action'] == 'modify' : 
                self.rclone.copy(change_item['path'], change_item['name']),

            elif change_item['action'] == 'close' : 
                self.rclone.copy(change_item['path'], change_item['name']),

            elif change_item['action'] == 'move' : 
                self.rclone.move(change_item['path'], change_item['name'], change_item['old_path']),
                
            elif change_item['action'] == 'rename' : 
                self.rclone.rename(change_item['path'], change_item['name'], change_item['old_name']),



    def check_change(self, change_item, remote_history, local_history, changes):
        # check if the files with specific extensions should be excluded
        extension = pathlib.Path(change_item['name']).suffix
        if extension in self.extensions: 
            self.logger.log(f'Skipping {change_item["name"]} because of extension')
            return False

        # Needs to be done when also files with the .part extensions are ignored
        if change_item['action'] == 'rename' and change_item['old_name'].endswith('.part'):
            change_item['action'] = 'create'

        # check if it's a hidden file
        if change_item['name'][0] in ['.', '#']:
            self.logger.log(f'Skipping {change_item["name"]} because it is a hidden file')
            return False

        if not self.remove_duplicates(change_item, changes):
            self.logger.log(f'Skipping {change_item["name"]} because it shows a create/delete action pair, which makes both operations obsolete')
            return False
            
        # check if the change was made by the remote drive 
        path = change_item['path'].removeprefix(self.local_path).removeprefix('/')
        path = f'{path}/{change_item["name"]}' if path != '' else change_item['name']
        for tmp in list(remote_history.queue):
            if path == tmp: 
                remote_history.get()
                self.logger.log(f'Skipping {change_item["name"]} because the change is caused by the remote drive')
                return False

        local_history.put(change_item['path'] + '/' + change_item['name'])
        return True

    def remove_children(self, change, changes):
        for tmp in list(changes.queue):
            child = f'{tmp["path"]}/{tmp["name"]}'
            parent = f'{change["path"]}/{change["name"]}'
            if child != parent and child.startswith(parent):
                changes.get()

    def remove_duplicates(self, change, changes):
        new_changes = queue.Queue()
        keep_change = True
        for tmp in list(changes.queue):
            if (f'{change["path"]}/{change["name"]}' == f'{tmp["path"]}/{tmp["name"]}'):
                changes.get()
                if ((change['action'] in ['create', 'modify', 'close'] and tmp['action'] == 'delete') or
                    (tmp['action'] in ['create', 'modify', 'close'] and change['action'] == 'delete')):
                    keep_change = False
                elif (tmp['action'] and change['action']) in ['create', 'modify', 'close'] or (tmp['action'] and change['action']) == 'delete':
                    keep_change = True
                    self.logger.log(f'Skipping {tmp["name"]} because it is a duplicate')
                else:
                    changes.put(tmp)        
        return keep_change

    def change_listener(self, changes):
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')

        event_handler = Handler(changes)
        observer = Observer()
        observer.schedule(event_handler, self.local_path, recursive=True)
        observer.start()
        try:
            while True:
                time.sleep(1)
        finally:
            observer.stop()
            observer.join()

    def sync_service(self, changes, remote_history, local_history):
        locked = False

        while(True):
            # wait until backsync is finished
            while remote.Remote.lock == True:
                time.sleep(1)
                locked = True

            # after backsync is finished get remote_changes and store in list for efficient access
            if locked:
                locked = False
            
            change_item = changes.get()
            #print(change_item)
            if self.check_change(change_item, remote_history, local_history, changes):
                self.perform_operation(change_item)
                self.remove_children(change_item, changes)

            Local.lock = True if changes.qsize() > 0 else False

    def run(self, remote_history, local_history):
        changes = queue.Queue()

        ch = threading.Thread(target=self.change_listener, args=(changes,))
        ss = threading.Thread(target=self.sync_service, args=(changes, remote_history, local_history,))

        ch.start()
        #time.sleep(10)
        ss.start()
