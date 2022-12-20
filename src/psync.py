#!/usr/bin/env python
import queue
from local import Local
from path import Path
from remote import Remote
from logger import Logger
from rclone import Rclone
from gdrive import GoogleDrive
import threading

class Psync:
    def check_flags(self):   
        '''
        
        '''
        if self.flags["backsync"]:
            self.rclone.backsync()
        if self.flags["resync"]:
            self.rclone.bisync()          
        if self.flags["init"]:
            self.rclone.init()

    def __init__(self):
        p = Path()
        self.local_path, self.remote_path, self.remote_type, self.flags, self.every_minutes = p.get_arguments()

        self.logger = Logger(self.flags['verbose'])
        self.rclone = Rclone(self.local_path, self.remote_path, self.flags['verbose'], self.logger)

        self.check_flags()

        self.local = Local(self.local_path, self.remote_path, self.logger, self.rclone)
        if self.remote_type == 'drive':
            self.remote = GoogleDrive(self.local_path, self.remote_path, self.logger, self.rclone)
        else:
            self.remote = Remote(self.local_path, self.remote_path, self.logger, self.rclone, self.every_minutes)

        self.remote_changes = queue.Queue()        

    def run(self):
        thread1 = threading.Thread(target=self.local.run, args=(self.remote_changes,))
        thread2 = threading.Thread(target=self.remote.run, args=(self.remote_changes,))

        thread1.start()
        thread2.start()   

def main():
    psync = Psync()
    psync.run()

if __name__ == '__main__':
    main()
