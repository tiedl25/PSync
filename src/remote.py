import os
import schedule
import time
import subprocess

class Remote:
    def __init__(self, path, remote_path):
        self.local_path = path
        self.remote_path = remote_path

    def sync(self, q):
        print("rclone sync {} {}".format(self.remote_path, self.local_path))
        lol = "rclone sync -v {} {}".format(self.remote_path, self.local_path)
        output = subprocess.getoutput(f'rclone sync -v {self.remote_path} {self.local_path}')
        li = []
        for line in output.split('\n'):
            s = line.split('INFO  : ')
            if len(s) > 1: 
                t = s[1].split(':')[0]
                if t not in ['', 'There was nothing to transfer']: 
                    q.put(t)

    def run(self, q):
        schedule.every().minute.do(lambda: self.sync(q))

        while True:
            schedule.run_pending()
            time.sleep(1)