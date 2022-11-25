import os
import datetime

class Logger:
    def __init__(self, verbose=False, logged=False):
        self.verbose = verbose
        self.logged = logged
        with open('log.txt', 'w+') as file:
            file.write('Logfile\n')
        
    def run(self, command):
        if self.verbose: print(command)
        os.system(command)

    def log(self, text):
        if(type(text) != str):
            text = str(text)
        with open('log.txt', 'a') as file:
            file.write(str(datetime.datetime.now()) + ': ')
            file.write(text)
            file.write('\n')
        if self.verbose == True:
            print(text)
        

    def debug(self, text):
        print(f'Debug: {text}')