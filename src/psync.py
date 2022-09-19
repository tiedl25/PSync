#!/usr/bin/env python
import queue
from local import Local
from path import Path
from remote import Remote
import threading
import queue

def main():
    p = Path()
    local_path, remote_path, remote_type, flags, every_minutes = p.get_arguments()
    l = Local(local_path, remote_path, flags)
    r = Remote(local_path, remote_path, every_minutes)

    q = queue.Queue()

    thread1 = threading.Thread(target=l.run, args=(q,))
    thread1.start()
    thread2 = threading.Thread(target=r.run, args=(q,))
    thread2.start()

if __name__ == '__main__':
    main()