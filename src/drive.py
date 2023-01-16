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

    def check_if_localChange(self, change_item, local_history):
        ''' 
        Check if the change was made by the local drive
        '''
        path = change_item['path'].removeprefix(self.remote_path)
        path = self.local_path + path + '/' + change_item['name']
        for tmp in list(local_history.queue):
            if path == tmp: 
                local_history.get()
                self.logger.log(f'Skipping {change_item["name"]} because the change is caused by the local drive')
                return False

        return True

    def check_change(self, change_item, last_change_item, local_history, activity, last_folder):
        # check if the second upload provides only thumbnail information
        if (last_change_item != None and change_item['id'] == last_change_item['id'] and 
            ((change_item['thumbnail'] == True and last_change_item['thumbnail'] == False))): 
            return False

        # check if the change is caused by a view on the file or a real change such as a rename/move/creation
        if (change_item['timestamps']['file_view'] != change_item['timestamps']['file_create'] and
            change_item['timestamps']['file_view'] > change_item['timestamps']['file_modify'] and
            change_item['timestamps']['file_view'] > (change_item['timestamps']['change_time'] - timedelta(0,2))):
            return False

        # check if the change is caused by a real file activity
        if activity['timestamp'] < (change_item['timestamps']['change_time'] - timedelta(0,2)):
            return False  

        if not self.folder_check(change_item, last_folder):
            return False

        return True   

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

    def classify(self, change_item, last_change_item, local_history, activity, last_folder):
        if not self.check_change(change_item, last_change_item, local_history, activity, last_folder):
            return False

        change_item['action'] = list(activity['primaryActionDetail'].keys())[0]
        change_item['old_path'] = ''
        change_item['old_name'] = ''
        
        if change_item['action'] in ['create', 'modify', 'restore']:
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

        # check if the change comes from the right folder
        if not change_item['path'].startswith(self.remote_path) and not change_item['old_path'].startswith(self.remote_path):
            print('No Change')
            return False

        return True        

    def get_activity(self, change_item):
        '''
        Request activity for a given change id. If the change happened before the activity, loop through the activity list until you get a desired one.
        '''
        i = 0
        activity = self.activity_service.activity().query(body={'itemName' : f'items/{change_item["id"]}'}).execute()['activities'][i]
        activity['timestamp'] = self.str_to_date(activity['timestamp'])
        while activity['timestamp'] > change_item['timestamps']['change_time']:
            i+=1
            activity = self.activity_service.activity().query(body={'itemName' : f'items/{change_item["id"]}'}).execute()['activities'][i]
            activity['timestamp'] = self.str_to_date(activity['timestamp'])
        
        return activity

    def retrieve_changes(self, changes, remote_history, local_history, start_change_id=None):
        result = []
        response = self.service.changes().getStartPageToken().execute()
        page_token = response["startPageToken"]
        next_page_token = page_token

        last_change_item = None
        last_folder = None
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
                    try: v = self.str_to_date(change['file']['viewedByMeTime']) 
                    except: v = self.str_to_date(change['file']['createdTime'])

                    timestamps = {
                        'change_time' : self.str_to_date(change['time']),
                        'file_create' : self.str_to_date(change['file']['createdTime']),
                        'file_modify' : self.str_to_date(change['file']['modifiedTime']),
                        'file_view' : v
                    }
                    
                    change_item = {'name' : change['file']['name'], 
                        'id' : change['fileId'], 
                        'path' : self.get_path(change['file']['parents'][0]),
                        'folder' : True if change['file']['mimeType'] == 'application/vnd.google-apps.folder' else False,
                        'timestamps' : timestamps,
                        'thumbnail' : change['file']['hasThumbnail'],
                        'thumbnailLink' : change['file']['thumbnailLink'] if 'thumbnailLink' in change['file'] else ''}

                    activity = self.get_activity(change_item)

                    if self.classify(change_item, last_change_item, local_history, activity, last_folder):
                        if self.check_if_localChange(change_item, local_history):
                            last_folder = None
                            
                            changes.put(change_item)

                            # local filesystem interprets rename/move as delete and create operation -> add also old filename/filepath
                            if change_item['action'] == 'rename': 
                                p = change_item['path'].removeprefix(self.remote_path)
                                p = p.removeprefix('/')
                                remote_history.put(p + ('/' if p not in ['', '/'] else '') + change_item['old_name'])
                            elif change_item['action'] == 'move': 
                                p = change_item['old_path'].removeprefix(self.remote_path)
                                p = p.removeprefix('/')
                                remote_history.put(p + ('/' if p not in ['', '/'] else '') + change_item['name'])

                            p = change_item['path'].removeprefix(self.remote_path)
                            p = p.removeprefix('/')
                            remote_history.put(p + ('/' if p not in ['', '/'] else '') + change_item['name'])
                            
                            
                        if change_item['folder']: last_folder = change_item    
                    last_change_item = change_item

            page_token = next_page_token

            next_page_token = self.service.changes().getStartPageToken().execute()['startPageToken']
            while next_page_token == page_token:
                time.sleep(0.5)
                next_page_token = self.service.changes().getStartPageToken().execute()['startPageToken']

    def folder_check(self, change_item, last_folder):
        '''
        Check if an activity is just caused by a change to a parent folder.
        '''
        if last_folder == None:
            return True
        if (change_item['path'].startswith(last_folder['path'] + '/' + last_folder['name']) and 
            last_folder['timestamps']['change_time'] > (change_item['timestamps']['change_time'] - timedelta(0,2))):
            return False
        return True

    def sync_changes(self, changes):
        while(True):
            change = changes.get()

            if change['action'] == 'delete' and change['folder'] == True:
                self.rclone.purge(change['path'], change['name'], True)

            elif change['action'] == 'delete' and change['folder'] == False:
                self.rclone.delete(change['path'], change['name'], True)

            elif change['action'] == 'sync' and change['folder'] == True:
                self.rclone.sync(change['path'], change['name'], True)

            elif change['action'] == 'sync' and change['folder'] == False:
                self.rclone.copy(change['path'], change['name'], True)

            elif change['action'] == 'rename' and change['folder'] == True:
                self.rclone.rename(change['path'], change['name'], change['old_name'], True)

            elif change['action'] == 'rename' and change['folder'] == False:
                self.rclone.rename(change['path'], change['name'], change['old_name'], True)

            elif change['action'] == 'move' and change['folder'] == True:
                self.rclone.move(change['path'], change['name'], change['old_path'], True)

            elif change['action'] == 'move' and change['folder'] == False:
                self.rclone.move(change['path'], change['name'], change['old_path'], True)
                
            


    def run(self, remote_history, local_history):
        changes = queue.Queue()

        self.create_service()
        rc = threading.Thread(target=self.retrieve_changes, args=(changes, remote_history, local_history))
        sc = threading.Thread(target=self.sync_changes, args=(changes,))
        
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
