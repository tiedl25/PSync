from src.path import Path
import unittest

class TestOptions(unittest.TestCase):
    def testCorrect(this):
        p = Path(["--resync", "/home/tiedl25/Bidir", "GoogleDrive:"])
        this.assertEqual(p._path, "/home/tiedl25/Bidir")
        this.assertEqual(p._remote, "GoogleDrive")
        this.assertEqual(p._remote_path, "")
        this.assertEqual(p._flags, {"resync" : True, "bidirsync" : False})

if __name__ == '__main__':
    unittest.main()