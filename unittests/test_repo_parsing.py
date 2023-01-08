import unittest
from repokeeper.repokeeper import RepoContent
from mock import patch
    
class Test_RepoObject(unittest.TestCase):


    @patch('repokeeper.repokeeper.Logger.log')
    @patch('repokeeper.repokeeper.glob.glob')
    def test_basic(self, fake_glob, fake_log):
        fake_glob.return_value = ['gqview-2.0.4-6-x86_64.pkg.tar.zst',
        'gqview-2.0.3-6-x86_64.pkg.tar.zst',
        'gqview-2.0.4-7-x86_64.pkg.tar.zst',
        'viber-13.3.1.22-1-x86_64.pkg.tar.zst',
        'viber-13.3.1.22-0-x86_64.pkg.tar.zst',
        'viber-13.3.1.21-0-x86_64.pkg.tar.zst']
        ro = RepoContent('aaaaa', ['gqview', 'fakepck'])
        for item in ro.list():
            self.assertIsInstance(item, str)
        self.assertEqual(len(ro.new_versions), 2)
        self.assertEqual(len(ro.old_versions), 4)
        self.assertEqual(len(ro.new_but_not_in_config), 1)
        self.assertEqual(ro.list_pck_names, set(["gqview", "viber"]))
        self.assertEqual(ro.get_highest_version('gqview'), '2.0.4.7')
        #self.assertEqual(newest_required_in_repo['gqview'].file, 'gqview-2.0.4-7-x86_64.pkg.tar.zst')



