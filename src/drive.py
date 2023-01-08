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
    API_NAME = 'drive'
    API_VERSION = 'v3'
    SCOPE = ['https://www.googleapis.com/auth/drive.activity', 'https://www.googleapis.com/auth/drive']

    def __init__(self, local_path, remote_path, logger, rclone):
        self.local_path = local_path
        self.remote_path = remote_path
        self.logger = logger
        self.rclone = rclone

    def create_service(self):
        print(self.CLIENT_SECRET_FILE, self.API_NAME, self.API_VERSION, self.SCOPE, sep='-')

        cred = None

        pickle_file = f'token_{self.API_NAME}_{self.API_VERSION}.pickle'

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
            self.service = build(self.API_NAME, self.API_VERSION, credentials=cred)
            print(self.API_NAME, 'service created successfully')
        except Exception as e:
            print('Unable to connect.')
            print(e)
        
        try:
            self.activity_service = build('driveactivity', 'v2', credentials=cred)
            print('activity', 'service created successfully')
        except Exception as e:
            print('Unable to connect.')
            print(e)

    def separate(self, e, tabs=0):
        t = ''
        for n in range(0, tabs):
            t = t + '\t'

        for i in zip(e.keys(), e.values()):
            if type(i[1]) in [str, int, bool, float]: 
                print(f'{t}{i[0]} : {i[1]}')
            elif type(i[1]) == dict: 
                print(f'{t}{i[0]} : ')
                self.separate(i[1], tabs=tabs+1)
            else:
                print(f'{t}{i[0]} : ')
                self.separate2(i[1], tabs=tabs+1)
    
    def separate2(self, e, tabs=0):
        t = ''
        for n in range(0, tabs):
            t = t + '\t'

        for i in e:
            if type(i) in [str, int, bool, float]: 
                print(f'{t}{i}')
            elif type(i) == dict:
                self.separate(i, tabs=tabs+1)
            else:
                self.separate2(i, tabs=tabs+1)

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

    def check_change(self, change_element, last_change_element, local_history):
        # check if the change comes from the right folder
        if not change_element['path'].startswith(self.remote_path):
            return False

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

    def classify(self, change_element, activity):
        change_element['action'] = list(activity['primaryActionDetail'].keys())[0]
        
        if change_element['action'] == 'move':
            old_parent = activity['primaryActionDetail']['move']['removedParents'][0]['driveItem']['name'].removeprefix('items/')
            change_element['old_path'] = self.get_path(old_parent)
        elif change_element['action'] == 'rename':
            change_element['old_name'] = activity['primaryActionDetail']['rename']['oldTitle']

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
                    #self.separate(change)
                    try: v = self.str_to_date(change['file']['viewedByMeTime']) 
                    except: v = self.str_to_date(change['file']['createdTime'])

                    timestamps = {
                        'change_time' : self.str_to_date(change['time']),
                        'file_create' : self.str_to_date(change['file']['createdTime']),
                        'file_modify' : self.str_to_date(change['file']['modifiedTime']),
                        'file_view' : v
                    }
                    
                    change_element = {'removed': change['file']['trashed'], 
                        'name' : change['file']['name'], 
                        'id' : change['fileId'], 
                        'path' : self.get_path(change['file']['parents'][0]),
                        'folder' : True if change['file']['mimeType'] == 'application/vnd.google-apps.folder' else False,
                        'timestamps' : timestamps,
                        'thumbnail' : change['file']['hasThumbnail']}
                    
                    if self.check_change(change_element, last_change_element, local_history):
                        activity = self.activity_service.activity().query(body={'itemName' : f'items/{change_element["id"]}'}).execute()['activities'][0]
                        self.separate(activity)
                        self.classify(change_element, activity)

                        changes.put(change_element)
                        remote_history.put(change_element)

                    last_change_element = change_element

            page_token = next_page_token

            next_page_token = self.service.changes().getStartPageToken().execute()['startPageToken']
            while next_page_token == page_token:
                time.sleep(1)
                next_page_token = self.service.changes().getStartPageToken().execute()['startPageToken']

    def get_time_filter(self, last_checked = (datetime.now(timezone.utc) - timedelta(0,10)).isoformat()):
        time_end = (datetime.now(timezone.utc) - timedelta(0,5)).isoformat()
        time_filter = f'time >= \"{last_checked}\"'
        time_filter = time_filter[0:28] + '+00:00"'
        time_filter += f' AND time <= \"{time_end}\"'
        time_filter = time_filter[0:-14] + '+00:00"'
        return (time_filter, time_end)

    def get_activity(self):
        time_filter, last_checked = self.get_time_filter()
        
        while True:
            print(time_filter)
            activity = self.activity_service.activity().query(body={'filter' : time_filter}).execute()

            time_filter, last_checked = self.get_time_filter(last_checked)

            if activity != {}: self.separate(activity)
            else: print('Nothing to do')
            time.sleep(5)
        # Iterate through the list of activities
        #for event in activity['events']:
        #    # Print the activity details
        #    print(f'Activity {event["id"]} of type {event["activityType"]} occurred on {event["eventTime"]}')

    def sync_changes(self, changes):
        while(True):
            change = changes.get()

            if change['removed'] == True and change['folder'] == True:
                print('Remove folder')
            elif change['removed'] == True and change['folder'] == False:
                print('Remove file')
            elif change['removed'] == False and change['folder'] == True:
                print('Copy folder')
            elif change['removed'] == False and change['folder'] == False:
                print('Copy file')

    def run(self, remote_history, local_history):
        changes = queue.Queue()

        self.create_service()
        rc = threading.Thread(target=self.retrieve_changes, args=(changes, remote_history, local_history))
        sc = threading.Thread(target=self.sync_changes, args=(changes,))
        #self.get_activity()
        rc.start()
        sc.start()
