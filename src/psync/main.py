#!/usr/bin/env python
import queue
from local import Local
from path import Path
from remote import Remote
from logger import Logger
from rclone import Rclone
from drive import GoogleDrive
import threading

class Lock:
    lock = False

class Psync:
    def check_flags(self):   
        '''
        
        '''
        if self.flags["init"]:
            self.rclone.init()
        elif self.flags["resync"]:
            self.rclone.bisync()    
        elif self.flags["backsync"]:
            self.rclone.backsync()
                  
        

    def __init__(self):
        p = Path()
        self.local_path, self.remote_path, self.remote_type, self.flags, self.every_minutes = p.get_arguments()

        self.logger = Logger(self.flags['verbose'])
        self.rclone = Rclone(self.local_path, self.remote_path, self.flags['verbose'], self.logger)
        self.lock = Lock()

        self.check_flags()

        self.local = Local(self.local_path, self.remote_path, self.logger, self.rclone, self.lock)

        if self.remote_type == 'drive':
            self.remote = GoogleDrive(self.local_path, self.remote_path, self.logger, self.rclone, self.lock)
        else:
            self.remote = Remote(self.local_path, self.remote_path, self.logger, self.rclone, self.lock, self.every_minutes)

        self.remote_history = queue.Queue()        
        self.local_history = queue.Queue()

    def run(self):
        thread1 = threading.Thread(target=self.local.run, args=(self.remote_history, self.local_history,))
        thread2 = threading.Thread(target=self.remote.run, args=(self.remote_history, self.local_history,))

        thread1.start()
        thread2.start()   

def main():
    psync = Psync()
    psync.run()

if __name__ == '__main__':
    main()
