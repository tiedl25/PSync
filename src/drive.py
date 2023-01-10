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

class GoogleDrive:
    CLIENT_SECRET_FILE = 'client_secret_PSync.json'
    SCOPE = ['https://www.googleapis.com/auth/drive.activity', 'https://www.googleapis.com/auth/drive']

    def __init__(self, local_path, remote_path, logger, rclone):
        self.local_path = local_path
        self.remote_path = remote_path
        self.logger = logger
        self.rclone = rclone

    def create_service(self):
        print(self.CLIENT_SECRET_FILE, self.SCOPE, sep='-')

        cred = None

        pickle_file = f'token_drive_api.pickle'

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
            print('Unable to connect.')
            print(e)
        
        try:
            self.activity_service = build('driveactivity', 'v2', credentials=cred)
            print('activity', 'service created successfully')
        except Exception as e:
            print('Unable to connect.')
            print(e)

    def str_to_date(self, s):
        date = s.replace('T', '', 1).replace('Z', '', 1)
        format = ("%Y-%m-%d%H:%M:%S.%f")
        return datetime.strptime(date, format)    

    def check_if_localChange(self, change_element, local_history):
        ''' 
        Check if the path also exists in the local changes, and if so delete it.
        '''
        path = change_element['path'].removeprefix(self.remote_path)
        path = self.local_path + path

        for i in list(local_history.queue):
            loc_path = i[1] + '/' + i[2]
            if path == loc_path: 
                local_history.get(timeout=2)
                return False

        return True

    def check_change(self, change_element, last_change_element, local_history, activity):
        # check if the second upload provides only thumbnail information
        if (last_change_element != None and
            change_element['id'] == last_change_element['id'] and 
            change_element['thumbnail'] == True and 
            last_change_element['thumbnail'] == False): 
            return False

        # check if the change is caused by a view on the file or a real change such as a rename/move/creation
        if (change_element['timestamps']['file_view'] != change_element['timestamps']['file_create'] and
            change_element['timestamps']['file_view'] > change_element['timestamps']['file_modify'] and
            change_element['timestamps']['file_view'] > (change_element['timestamps']['change_time'] - timedelta(0,2))):
            return False

        # check if the is caused by a real file activity
        if activity['timestamp'] < (change_element['timestamps']['change_time'] - timedelta(0,2)):
            return False  

        return self.check_if_localChange(change_element, local_history)        

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

    def classify(self, change_element, last_change_element, local_history, activity):
        if not self.check_change(change_element, last_change_element, local_history, activity):
            return False

        change_element['action'] = list(activity['primaryActionDetail'].keys())[0]
        change_element['old_path'] = ''
        change_element['old_name'] = ''
        
        if change_element['action'] in ['create', 'modify', 'restore']:
            change_element['action'] = 'sync'
        elif change_element['action'] == 'move':
            old_parent = activity['primaryActionDetail']['move']['removedParents'][0]['driveItem']['name'].removeprefix('items/')
            change_element['old_path'] = self.get_path(old_parent)

            if change_element['path'].startswith(self.remote_path) and not change_element['old_path'].startswith(self.remote_path):
                change_element['action'] = 'sync'
                change_element['old_path'] = ''
            elif not change_element['path'].startswith(self.remote_path) and change_element['old_path'].startswith(self.remote_path):
                change_element['action'] = 'delete'
                change_element['path'] = change_element['old_path']
                change_element['old_path'] = ''

        elif change_element['action'] == 'rename':
            change_element['old_name'] = activity['primaryActionDetail']['rename']['oldTitle']

        # check if the change comes from the right folder
        if not change_element['path'].startswith(self.remote_path) and not change_element['old_path'].startswith(self.remote_path):
            print('No Change')
            return False

        return True         

    def retrieve_changes(self, changes, remote_history, local_history, start_change_id=None):
        result = []
        response = self.service.changes().getStartPageToken().execute()
        page_token = response["startPageToken"]
        next_page_token = page_token

        last_change_element = None
        while True:
            param = {}
            if start_change_id:
                param['startChangeId'] = start_change_id
            if page_token:
                param['pageToken'] = page_token
                
            param['fields'] = '*'

            drive_changes = self.service.changes().list(**param).execute()
            drive_changes = drive_changes['changes']

            if drive_changes != []:
                for change in drive_changes:
                    #separate_dict(change)
                    try: v = self.str_to_date(change['file']['viewedByMeTime']) 
                    except: v = self.str_to_date(change['file']['createdTime'])

                    timestamps = {
                        'change_time' : self.str_to_date(change['time']),
                        'file_create' : self.str_to_date(change['file']['createdTime']),
                        'file_modify' : self.str_to_date(change['file']['modifiedTime']),
                        'file_view' : v
                    }
                    
                    change_element = {'name' : change['file']['name'], 
                        'id' : change['fileId'], 
                        'path' : self.get_path(change['file']['parents'][0]),
                        'folder' : True if change['file']['mimeType'] == 'application/vnd.google-apps.folder' else False,
                        'timestamps' : timestamps,
                        'thumbnail' : change['file']['hasThumbnail']}

                    i = 0
                    activity = self.activity_service.activity().query(body={'itemName' : f'items/{change_element["id"]}'}).execute()['activities'][i]
                    activity['timestamp'] = self.str_to_date(activity['timestamp'])
                    while activity['timestamp'] > change_element['timestamps']['change_time']:
                        i+=1
                        activity = self.activity_service.activity().query(body={'itemName' : f'items/{change_element["id"]}'}).execute()['activities'][i]
                        activity['timestamp'] = self.str_to_date(activity['timestamp'])

                    if self.classify(change_element, last_change_element, local_history, activity):
                        changes.put(change_element)
                        remote_history.put(change_element)

                    last_change_element = change_element

            page_token = next_page_token

            next_page_token = self.service.changes().getStartPageToken().execute()['startPageToken']
            while next_page_token == page_token:
                time.sleep(1)
                next_page_token = self.service.changes().getStartPageToken().execute()['startPageToken']

    def sync_changes(self, changes):
        while(True):
            change = changes.get()

            if change['action'] == 'delete' and change['folder'] == True:
                print('Remove folder')
                print(f"\tName: {change['name']}")
                print(f"\tPath: {change['path']}")
            elif change['action'] == 'delete' and change['folder'] == False:
                print('Remove file')
                print(f"\tName: {change['name']}")
                print(f"\tPath: {change['path']}")
            elif change['action'] == 'sync' and change['folder'] == True:
                print('Copy folder')
                print(f"\tName: {change['name']}")
                print(f"\tPath: {change['path']}")
            elif change['action'] == 'sync' and change['folder'] == False:
                print('Copy file')
                print(f"\tName: {change['name']}")
                print(f"\tPath: {change['path']}")
            elif change['action'] == 'rename' and change['folder'] == True:
                print('Rename folder')
                print(f"\tName: {change['name']}")
                print(f"\tPath: {change['path']}")
                print(f"\tOldname: {change['old_name']}")
            elif change['action'] == 'rename' and change['folder'] == False:
                print('Rename file')
                print(f"\tName: {change['name']}")
                print(f"\tPath: {change['path']}")
                print(f"\tOldname: {change['old_name']}")
            elif change['action'] == 'move' and change['folder'] == True:
                print('Move folder')
                print(f"\tName: {change['name']}")
                print(f"\tPath: {change['path']}")
                print(f"\tOldpath: {change['old_path']}") 
            elif change['action'] == 'move' and change['folder'] == False:
                print('Move file')
                print(f"\tName: {change['name']}")
                print(f"\tPath: {change['path']}")
                print(f"\tOldpath: {change['old_path']}") 

    def run(self, remote_history, local_history):
        changes = queue.Queue()

        self.create_service()
        rc = threading.Thread(target=self.retrieve_changes, args=(changes, remote_history, local_history))
        sc = threading.Thread(target=self.sync_changes, args=(changes,))
        
        rc.start()
        sc.start()





def separate_dict(self, e, tabs=0):
    t = ''
    for n in range(0, tabs):
        t = t + '\t'

    for i in zip(e.keys(), e.values()):
        if type(i[1]) in [str, int, bool, float]: 
            print(f'{t}{i[0]} : {i[1]}')
        elif type(i[1]) == dict: 
            print(f'{t}{i[0]} : ')
            separate_dict(i[1], tabs=tabs+1)
        else:
            print(f'{t}{i[0]} : ')
            separate_list(i[1], tabs=tabs+1)

def separate_list(self, e, tabs=0):
    t = ''
    for n in range(0, tabs):
        t = t + '\t'

    for i in e:
        if type(i) in [str, int, bool, float]: 
            print(f'{t}{i}')
        elif type(i) == dict:
            separate_dict(i, tabs=tabs+1)
        else:
            separate_list(i, tabs=tabs+1)
