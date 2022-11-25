#!/usr/bin/env python
import queue
from local import Local
from path import Path
from remote import Remote
from logger import Logger
import threading
import queue

class Psync:
    def check_flags(self):   
        '''
        
        '''
        if self.flags["backsync"]:
            self.logger.run("rclone sync -v {} {}".format(self.remote_path, self.local_path))
        if self.flags["resync"]:
            self.logger.run("rclone bisync -v --resync {} {}".format(self.local_path, self.remote_path))           
        if self.flags["init"]:
            self.logger.run("rclone sync -v --delete-before --exclude '.*' --delete-excluded {} {}".format(self.local_path, self.remote_path))

    def __init__(self):
        p = Path()
        self.local_path, self.remote_path, self.remote_type, self.flags, self.every_minutes = p.get_arguments()

        self.logger = Logger(self.flags['verbose'], self.flags['log'])

        self.check_flags()

        self.local = Local(self.local_path, self.remote_path, self.logger)
        self.remote = Remote(self.local_path, self.remote_path, self.logger, self.every_minutes)

        self.remote_changes = queue.Queue()        

    def run(self):
        thread1 = threading.Thread(target=self.local.run, args=(self.remote_changes,))
        thread2 = threading.Thread(target=self.remote.run, args=(self.remote_changes,))

        thread1.start()
        thread2.start()   



if __name__ == '__main__':
    psync = Psync()
    psync.run()
