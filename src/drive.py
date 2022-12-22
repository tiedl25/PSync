from remote import Remote
import os
import schedule
import time
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

import queue
import threading
from datetime import datetime, timedelta

class GoogleDrive:
    CLIENT_SECRET_FILE = 'client_secret_PSync.json'
    API_NAME = 'drive'
    API_VERSION = 'v3'
    SCOPE = 'https://www.googleapis.com/auth/drive'

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

    def check_if_change(self, change_element):
        '''
            With the change information of the google drive api one can not tell if a file/folder was only viewed or if there appeared a real change. 
            To obtain this information we can have a look at the different time stamps the api provides. The timestamps however are not modified when 
            a file is trashed, untrashed or moved. It is only modified when the file/folder, when it is viewed or, when the file is renamed. so to obtain
            if there was a real change we first check if the modify timestamp is more recent than the view timestamp. If so we can be sure, that the change
            is caused by a rename or creation. If not the we also need to check if change is caused by a file view. For that we check if the file view
            happened within a period to seconds before the file change until the file change was recorded, so we can be sure about it. If it is outside 
            this range it will be also treated as a real change and if not than nothing happens.
        '''
        # check if the last change was a view on the file or a real change such as a rename
        if change_element['file_view'] > change_element['file_modify']:
            # check if the change is caused by the file view or another operation such as a file move
            if change_element['file_view'] > change_element['change_time'] - timedelta(0,2): 
                return False
        return True

    def retrieve_changes(self, change_queue, start_change_id=None):
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

            changes = self.service.changes().list(**param).execute()
            changes = changes['changes']

            if changes != []:
                
                
                for change in changes:
                    #self.separate(change)
                    change_element = {'removed': change['file']['trashed'], 
                        'name': change['file']['name'], 
                        'id': change['fileId'], 
                        'parent' : change['file']['parents'][0], 
                        'folder' : True if change['file']['mimeType'] == 'application/vnd.google-apps.folder' else False,
                        'change_time' : self.str_to_date(change['time']),
                        'file_create' : self.str_to_date(change['file']['createdTime']),
                        'file_modify' : self.str_to_date(change['file']['modifiedTime']),
                        'file_view' : self.str_to_date(change['file']['viewedByMeTime'])}

                    if self.check_if_change(change_element):
                        self.get_path(change_element)
                        change_queue.put(change_element)

            page_token = next_page_token

            next_page_token = self.service.changes().getStartPageToken().execute()['startPageToken']
            while next_page_token == page_token:
                time.sleep(1)
                next_page_token = self.service.changes().getStartPageToken().execute()['startPageToken']

    def get_path(self, change_element):
        file_id = change_element['id']
        file = self.service.files().get(fileId=file_id, fields='*').execute()

        path = '/' + change_element['name']

        parent_id = change_element['parent']
        parent = {'name' : ''}

        while parent_id:
            parent = self.service.files().get(fileId=parent_id, fields='*').execute()
            path = '/' + parent['name'] + path
            parent_id = parent['parents'][0] if 'parents' in parent else None

        path = path.removeprefix('/Meine Ablage')
        path = self.remote_path.split(':')[0] + ':' + path
        change_element['path'] = path

    def sync_changes(self, change_queue):
        while(True):
            change = change_queue.get()

            if change['removed'] == True and change['folder'] == True:
                print('Remove folder')
            elif change['removed'] == True and change['folder'] == False:
                print('Remove file')
            elif change['removed'] == False and change['folder'] == True:
                print('Copy folder')
            elif change['removed'] == False and change['folder'] == False:
                print('Copy file')

    def run(self, remote_changes):
        change_queue = queue.Queue()

        self.create_service()
        rc = threading.Thread(target=self.retrieve_changes, args=(change_queue,))
        sc = threading.Thread(target=self.sync_changes, args=(change_queue,))

        rc.start()
        sc.start()
