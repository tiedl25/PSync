import os

class Logger:
    def __init__(self, verbose=False, logged=False):
        self.verbose = verbose
        self.logged = logged
        
    def run(self, command):
        if self.verbose: print(command)
        os.system(command)

    def log(self, text):
        print(text)

    def debug(self, text):
        print(f'Debug: {text}')