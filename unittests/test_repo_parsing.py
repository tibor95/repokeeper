import unittest
from repokeeper.repokeeper import Repo_Base, RepoContent
from mock import patch


# class Testing(unittest.TestCase):

#     @patch('repokeeper.repokeeper.Logger.log')
#     @patch('repokeeper.repokeeper.get_conf_content')
#     def setUp(self, fake_conf, fake_log):
#         fake_conf.return_value = (['gqview', 'fakepck'], 'a', 'b', 'c')
#         self.rb = Repo_Base()

#     @patch('repokeeper.repokeeper.Logger.log')
#     @patch('repokeeper.repokeeper.Repo_Base.list_files_in_repo')
#     def test_basic(self, fake_list, fake_log):
#         fake_list.return_value = ['gqview-2.0.4-6-x86_64.pkg.tar.zst',
#         'gqview-2.0.3-6-x86_64.pkg.tar.zst',
#         'gqview-2.0.4-7-x86_64.pkg.tar.zst',
#         'viber-13.3.1.22-1-x86_64.pkg.tar.zst',
#         'viber-13.3.1.22-0-x86_64.pkg.tar.zst',
#         'viber-13.3.1.21-0-x86_64.pkg.tar.zst']
#         required_but_with_newer_version, in_repo_not_required, newest_required_in_repo = \
#         self.rb.parse_localrepo()
#         self.assertEqual(len(required_but_with_newer_version), 2)
#         self.assertEqual(len(in_repo_not_required), 3)
#         self.assertEqual(len(newest_required_in_repo), 1)
#         self.assertEqual(newest_required_in_repo['gqview'].file, 'gqview-2.0.4-7-x86_64.pkg.tar.zst')
    
class Test_RepoObject(unittest.TestCase):

    # @patch('repokeeper.repokeeper.Logger.log')
    # @patch('repokeeper.repokeeper.get_conf_content')
    # def setUp(self, fake_conf, fake_log):
    #     fake_conf.return_value = (['gqview', 'fakepck'], 'a', 'b', 'c')
    #     self.rb = Repo_Base()

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
        for item in ro._content:
            print(item)
        self.assertEqual(len(ro.new_versions), 2)
        self.assertEqual(len(ro.old_versions), 4)
        self.assertEqual(len(ro.new_but_not_in_config), 1)
        self.assertEqual(ro.list_pck_names, set(["gqview", "viber"]))
        self.assertEqual(ro.get_highest_version('gqview'), '2.0.4.7')
        #self.assertEqual(newest_required_in_repo['gqview'].file, 'gqview-2.0.4-7-x86_64.pkg.tar.zst')



