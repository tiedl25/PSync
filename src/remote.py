import os
import schedule
import time


class Remote:
    def __init__(this, path, remote, remote_path):
        this._path = path
        this._remote = remote
        this._remote_path = remote_path

    def sync(this):
        print("rclone sync {}:{} {}".format(this._remote, this._remote_path, this._path))
        #os.system("rclone sync {}:{} {}".format(this._remote, this._remote_path, this._path))

    def run(this):
        schedule.every(0.1).minutes.do(this.sync)

        while True:
            schedule.run_pending()
            time.sleep(1)