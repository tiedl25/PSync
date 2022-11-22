import schedule
import time
import subprocess
from local import Local

class Remote:
    def __init__(self, path, remote_path, logger, every_minutes=5):
        self.local_path = path
        self.remote_path = remote_path
        self.every_minutes = every_minutes
        self.logger = logger

    def sync(self, q):
        print("rclone sync --delete-before {} {}".format(self.remote_path, self.local_path))
        output = subprocess.getoutput(f'rclone sync --delete-before -v {self.remote_path} {self.local_path}')
        li = []
        for line in output.split('\n'):
            s = line.split('INFO  : ')
            if len(s) > 1: 
                t = s[1].split(':')[0]
                if t not in ['', 'There was nothing to transfer']: 
                    q.put(t)

    def run(self, q):
        schedule.every(self.every_minutes).minutes.do(lambda: self.sync(q))

        while True:
            if not Local.lock: schedule.run_pending()
            time.sleep(1)