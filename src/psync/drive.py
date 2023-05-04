from remote import Remote
import os
import schedule
import time
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

import queue
import threading
from datetime import datetime, timedelta, timezone

class GoogleDriveHandler:
    CLIENT_SECRET_FILE = os.path.expanduser('~/.client_secret_PSync.json')
    SCOPE = ['https://www.googleapis.com/auth/drive.activity', 'https://www.googleapis.com/auth/drive']

    def __init__(self, remote_path):
        self.remote_path = remote_path

    def create_service(self):
        print(self.CLIENT_SECRET_FILE, self.SCOPE, sep='-')

        cred = None

        pickle_file = os.path.expanduser('~/.token_drive_api.pickle')

        if os.path.exists(pickle_file):
            with open(pickle_file, 'rb') as token:
                cred = pickle.load(token)
        
        if not cred or not cred.valid:
            flow = InstalledAppFlow.from_client_secrets_file(self.CLIENT_SECRET_FILE, self.SCOPE)
            cred = flow.run_local_server()
                
            with open(pickle_file, 'wb') as token:
                pickle.dump(cred, token)

        print(cred.client_id)
        print(cred.valid)

        try:
            self.service = build('drive', 'v3', credentials=cred)
            print('drive', 'service created successfully')
        except Exception as e:
            print('Unable to connect to Drive Api.')
            print(e)
        
        try:
            self.activity_service = build('driveactivity', 'v2', credentials=cred)
            print('activity', 'service created successfully')
        except Exception as e:
            print('Unable to connect to Drive Activity Api.')
            print(e)

    def str_to_date(self, s):
        date = s.replace('T', '', 1).replace('Z', '', 1)
        format = ("%Y-%m-%d%H:%M:%S.%f")
        return datetime.strptime(date, format)  

    def get_path(self, parent_id):
        path = ''

        parent = {'name' : ''}

        while parent_id:
            parent = self.service.files().get(fileId=parent_id, fields='*').execute()
            path = '/' + parent['name'] + path
            parent_id = parent['parents'][0] if 'parents' in parent else None

        path = path.removeprefix('/Meine Ablage')
        path = self.remote_path.split(':')[0] + ':' + path

        return path

    def classify_item_action(self, change_item, activity):
        change_item['action'] = list(activity['primaryActionDetail'].keys())[0]
        change_item['old_path'] = ''
        change_item['old_name'] = ''
        
        if change_item['action'] in ['create', 'modify']:
            change_item['action'] = 'sync'
        elif change_item['action'] == 'move':
            old_parent = activity['primaryActionDetail']['move']['removedParents'][0]['driveItem']['name'].removeprefix('items/')
            change_item['old_path'] = self.get_path(old_parent)

            if change_item['path'].startswith(self.remote_path) and not change_item['old_path'].startswith(self.remote_path):
                change_item['action'] = 'sync'
                change_item['old_path'] = ''
            elif not change_item['path'].startswith(self.remote_path) and change_item['old_path'].startswith(self.remote_path):
                change_item['action'] = 'delete'
                change_item['path'] = change_item['old_path']
                change_item['old_path'] = ''
        elif change_item['action'] == 'rename':
            change_item['old_name'] = activity['primaryActionDetail']['rename']['oldTitle']

        return change_item

    def get_activity(self, change_item):
        i = 0
        activity = self.activity_service.activity().query(body={'itemName' : f'items/{change_item["id"]}'}).execute()['activities'][i]
        activity['timestamp'] = self.str_to_date(activity['timestamp'])
        while activity['timestamp'] > change_item['timestamps']['change_time']:
            i+=1
            activity = self.activity_service.activity().query(body={'itemName' : f'items/{change_item["id"]}'}).execute()['activities'][i]
            activity['timestamp'] = self.str_to_date(activity['timestamp'])
        
        return activity

    def manage_change(self, drive_change):
        if 'file' not in drive_change:
            return
        
        try: v = self.str_to_date(drive_change['file']['viewedByMeTime']) 
        except: v = self.str_to_date(drive_change['file']['createdTime'])

        # different timestamps required for the change_item
        timestamps = {
            'change_time' : self.str_to_date(drive_change['time']),
            'file_create' : self.str_to_date(drive_change['file']['createdTime']),
            'file_modify' : self.str_to_date(drive_change['file']['modifiedTime']),
            'file_view' : v}

        # all the necessary fields for further processing
        change_item = {'name' : drive_change['file']['name'], 
            'id' : drive_change['fileId'], 
            'path' : self.get_path(drive_change['file']['parents'][0]),
            'folder' : True if drive_change['file']['mimeType'] == 'application/vnd.google-apps.folder' else False,
            'timestamps' : timestamps}
        
        # get more information about the exact change from the drive activity api
        activity = self.get_activity(change_item)

        change_item['timestamps'].update({'activity_timestamp' : activity['timestamp']})

        # classify item based on the the activity
        change_item = self.classify_item_action(change_item, activity)

        return change_item

    def retrieve_changes(self, change_items, start_change_id=None):
        result = []
        response = self.service.changes().getStartPageToken().execute()
        page_token = response["startPageToken"]
        next_page_token = page_token

        while True:
            param = {}
            if start_change_id:
                param['startChangeId'] = start_change_id
            if page_token:
                param['pageToken'] = page_token
                
            param['fields'] = '*'

            drive_changes = (self.service.changes().list(**param).execute())['changes']

            for drive_change in drive_changes:
                change_item = self.manage_change(drive_change)
                change_items.put(change_item)

            page_token = next_page_token
            next_page_token = self.service.changes().getStartPageToken().execute()['startPageToken']
            while next_page_token == page_token:
                time.sleep(0.5)
                next_page_token = self.service.changes().getStartPageToken().execute()['startPageToken']
            

class GoogleDrive:
    def __init__(self, local_path, remote_path, logger, rclone, lock):
        self.local_path = local_path
        self.remote_path = remote_path
        self.logger = logger
        self.rclone = rclone
        self.lock = lock

    def perform_operation(self, change_item):
        # wait if local is performing an operation
        while self.lock.lock == True:
            time.sleep(0.1)

        # while locked local cannot perform any operation
        self.lock.lock = True

        if change_item['folder'] == True:
            if change_item['action'] == 'delete':
                self.rclone.purge(change_item['path'], change_item['name'], True)

            elif change_item['action'] == 'sync':
                self.rclone.sync(change_item['path'], change_item['name'], True)

            elif change_item['action'] == 'rename':
                self.rclone.rename(change_item['path'], change_item['name'], change_item['old_name'], True)

            elif change_item['action'] == 'move':
                self.rclone.move(change_item['path'], change_item['name'], change_item['old_path'], True)

            elif change_item['action'] == 'restore':
                self.rclone.restore(change_item['path'], change_item['name'], True)

        else: 
            if change_item['action'] == 'delete':
                self.rclone.delete(change_item['path'], change_item['name'], True)

            elif change_item['action'] == 'sync':
                self.rclone.copy(change_item['path'], change_item['name'], True)

            elif change_item['action'] == 'rename':
                self.rclone.rename(change_item['path'], change_item['name'], change_item['old_name'], True)

            elif change_item['action'] == 'move':
                self.rclone.move(change_item['path'], change_item['name'], change_item['old_path'], True)

            elif change_item['action'] == 'restore':
                self.rclone.restore(change_item['path'], change_item['name'], True)

        self.lock.lock = False

    def check_change_item(self, change_item, last_change_item, last_folder):
        # check if a file triggers multiple changes but only shows one action
        if (last_change_item != None and change_item['id'] == last_change_item['id'] and 
            change_item['timestamps']['activity_timestamp'] == last_change_item['timestamps']['activity_timestamp']):
            self.logger.log(f'Drive: Skipping {change_item["name"]} because the previous change complied with it already', 'red')
            return False

        # check if the change is caused by a view on the file or a real change such as a rename/move/creation
        if (change_item['timestamps']['file_view'] != change_item['timestamps']['file_create'] and
            change_item['timestamps']['file_view'] > change_item['timestamps']['file_modify'] and
            change_item['timestamps']['file_view'] > (change_item['timestamps']['change_time'] - timedelta(0,2))):
            #self.logger.log(f'Drive: Skipping {change_item["name"]} because it\'s only a view on the file/folder', 'red')
            return False

        # check if the change is caused by a real file activity
        if change_item['timestamps']['activity_timestamp'] < (change_item['timestamps']['change_time'] - timedelta(0,2)):
            return False  

        # check if the change is already captured within a change of the parent folder
        if not self.folder_check(change_item, last_folder):
            return False

        return True  

    def check_local_changes(self, change_item, local_history):
        ''' 
        Check if the change was made by the local drive
        '''
        path = self.local_path + change_item['path'].removeprefix(self.remote_path) + '/' + change_item['name']

        for tmp in list(local_history.queue):
            if path == tmp: 
                local_history.get()
                self.logger.log(f'Drive: Skipping {change_item["name"]} because the change is caused by the local drive', 'red')
                return False

        return True

    def folder_check(self, change_item, last_folder):
        '''
        Check if a change is just caused by a change to a parent folder.
        '''
        if last_folder == None:
            return True
        if (change_item['path'].startswith(last_folder['path'] + '/' + last_folder['name']) and 
            last_folder['timestamps']['change_time'] > (change_item['timestamps']['change_time'] - timedelta(0,2))):
            return False
        return True 

    # deprecated
    def add_to_history_move(self, change_item, remote_history):
        '''
        Local filesystem interprets rename/move as delete and create operation -> add old filename/filepath also to the remote history
        '''
        
        if change_item['action'] == 'rename': 
            p = change_item['path'].removeprefix(self.remote_path)
            p = p.removeprefix('/')
            remote_history.put(p + ('/' if p not in ['', '/'] else '') + change_item['old_name'])
        elif change_item['action'] == 'move': 
            p = change_item['old_path'].removeprefix(self.remote_path)
            p = p.removeprefix('/')
            remote_history.put(p + ('/' if p not in ['', '/'] else '') + change_item['name'])

    def add_to_history(self, change_item, remote_history):
        #self.add_to_history(change_item, remote_history)

        # add filename to the remote history
        p = change_item['path'].removeprefix(self.remote_path)
        p = p.removeprefix('/')
        remote_history.put(p + ('/' if p not in ['', '/'] else '') + change_item['name'])

    def sync_service(self, change_items, local_history, remote_history):
        last_change_item = None
        last_folder = None

        while(True):
            change_item = change_items.get()

            # check if the change_item should be considered depending on it's location
            if not change_item['path'].startswith(self.remote_path) and not change_item['old_path'].startswith(self.remote_path):
                continue
            
            if not self.check_change_item(change_item, last_change_item, last_folder):
                last_change_item = change_item
                continue

            # Check if the retrieved change is just a local file system event and therefore can be skipped
            if self.check_local_changes(change_item, local_history):
                last_folder = None
                self.add_to_history(change_item, remote_history)
                self.perform_operation(change_item)
            
            # Update last_folder
            if change_item['folder'] and self.folder_check(change_item, last_folder):
                last_folder = change_item    

            # Update last_change_item
            last_change_item = change_item

    # remote_history and local_history are globally available queues to append all the changes from remote and local
    def run(self, remote_history, local_history):
        # All changes are stored in a queue written by the rc thread and read by the sc thread
        change_items = queue.Queue()

        drive = GoogleDriveHandler(self.remote_path)
        # Retrieve credentials for Google Drive
        drive.create_service()

        # Separate threads for retrieving changes and syncing changes
        rc = threading.Thread(target=drive.retrieve_changes, args=(change_items,))
        sc = threading.Thread(target=self.sync_service, args=(change_items, local_history, remote_history))
        
        rc.start()
        sc.start()



def separate(e, tabs=0):
    t = ''
    for n in range(0, tabs):
        t = t + '\t'
    if type(e) == dict:
        for i in zip(e.keys(), e.values()):
            if type(i[1]) in [str, int, bool, float, datetime]: 
                print(f'{t}{i[0]} : {i[1]}')
            else:
                print(f'{t}{i[0]} : ')
                separate(i[1], tabs=tabs+1)
    elif type(e) == list:
        for i in e:
            if type(i) in [str, int, bool, float, datetime]: 
                print(f'{t}{i}')
            else:
                separate(i, tabs=tabs+1)
