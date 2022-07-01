import main
import unittest

class TestOptions(unittest.TestCase):
    @classmethod
    def setUpClass(this):
        this.p = main.Psync(["--resync", "/home/tiedl25/Bidir", "GoogleDrive:"])

    def testFileCreate(this):
        this.assertEqual(this.p._options(['IN_CREATE'], 'test', '/home/tiedl25/Bidir/Luxor'), 
        'rclone copy /home/tiedl25/Bidir/Luxor/test GoogleDrive:/Bidir/Luxor')

    def testFileMovedTo(this):
        this.assertEqual(this.p._options(['IN_MOVED_TO'], 'test', '/home/tiedl25/Bidir/Luxor'), 
        'rclone copy /home/tiedl25/Bidir/Luxor/test GoogleDrive:/Bidir/Luxor')

    def testFileModify(this):
        this.assertEqual(this.p._options(['IN_MODIFY'], 'test', '/home/tiedl25/Bidir/Luxor'), 
        'rclone copy /home/tiedl25/Bidir/Luxor/test GoogleDrive:/Bidir/Luxor')

    def testFileAttrib(this):
        this.assertEqual(this.p._options(['IN_ATTRIB'], 'test', '/home/tiedl25/Bidir/Luxor'), 
        'rclone copy /home/tiedl25/Bidir/Luxor/test GoogleDrive:/Bidir/Luxor')

    def testDirCreate(this):
        this.assertEqual(this.p._options(['IN_CREATE', 'IN_ISDIR'], 'test', '/home/tiedl25/Bidir/Luxor'), 
        'rclone copy /home/tiedl25/Bidir/Luxor/test GoogleDrive:/Bidir/Luxor/test')

    def testDirMovedTo(this):
        this.assertEqual(this.p._options(['IN_MOVED_TO', 'IN_ISDIR'], 'test', '/home/tiedl25/Bidir/Luxor'), 
        'rclone copy /home/tiedl25/Bidir/Luxor/test GoogleDrive:/Bidir/Luxor/test')

    def testDirModify(this):
        this.assertEqual(this.p._options(['IN_MODIFY', 'IN_ISDIR'], 'test', '/home/tiedl25/Bidir/Luxor'), 
        'rclone copy /home/tiedl25/Bidir/Luxor/test GoogleDrive:/Bidir/Luxor/test')

    def testDirAttrib(this):
        this.assertEqual(this.p._options(['IN_ATTRIB', 'IN_ISDIR'], 'test', '/home/tiedl25/Bidir/Luxor'), 
        'rclone copy /home/tiedl25/Bidir/Luxor/test GoogleDrive:/Bidir/Luxor/test')

    def testFileMovedFrom(this):
        this.assertEqual(this.p._options(['IN_MOVED_FROM'], 'test', '/home/tiedl25/Bidir/Luxor'), 
        'rclone delete GoogleDrive:/Bidir/Luxor/test')

    def testFileDelete(this):
        this.assertEqual(this.p._options(['IN_DELETE'], 'test', '/home/tiedl25/Bidir/Luxor'), 
        'rclone delete GoogleDrive:/Bidir/Luxor/test')

    def testDirMovedFrom(this):
        this.assertEqual(this.p._options(['IN_MOVED_FROM', 'IN_ISDIR'], 'test', '/home/tiedl25/Bidir/Luxor'), 
        'rclone purge GoogleDrive:/Bidir/Luxor/test')

    def testDirDelete(this):
        this.assertEqual(this.p._options(['IN_DELETE', 'IN_ISDIR'], 'test', '/home/tiedl25/Bidir/Luxor'), 
        'rclone purge GoogleDrive:/Bidir/Luxor/test')


if __name__ == '__main__':
    unittest.main()