from remote import Remote
import os
import schedule
import time
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

import queue
import threading

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
                    change_element = {'removed': change['file']['trashed'], 
                        'name': change['file']['name'], 
                        'id': change['fileId'], 
                        'parent' : change['file']['parents'][0], 
                        'folder' : True if change['file']['mimeType'] == 'application/vnd.google-apps.folder' else False}
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

    def check_if_trueChange(self):
        pass

    def run(self, remote_changes):
        change_queue = queue.Queue()

        self.create_service()
        rc = threading.Thread(target=self.retrieve_changes, args=(change_queue,))
        sc = threading.Thread(target=self.sync_changes, args=(change_queue,))

        rc.start()
        sc.start()
