from local import Local
from path import Path
from remote import Remote
from remote import GoogleDrive
import threading

def main():
    p = Path(["--resync", "/home/tiedl25/Bidir", "GoogleDrive:"])
    path, remote, remote_path, flags = p.get_arguments()
    l = Local(path, remote, remote_path, flags)
    r = Remote()

    thread1 = threading.Thread(target=l.run)
    thread1.start()
    thread2 = threading.Thread(target=r.run)
    thread2.start()


if __name__ == '__main__':
    main()