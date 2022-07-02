import os
import schedule
import time

class Remote:
    def __init__(this):
        this._path = ""

    def sync(this):
        print("rclone sync GoogleDrive:Bidir /home/tiedl25/Bidir")
        #os.system("rclone sync GoogleDrive:Bidir /home/tiedl25/Bidir")

    def run(this):
        schedule.every(5).minutes.do(this.sync)

        while True:
            schedule.run_pending()
            time.sleep(1)

class GoogleDrive(Remote):
    def __init__(this):
        this._path = ""