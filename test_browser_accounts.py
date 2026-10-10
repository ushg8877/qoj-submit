import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from test_submit import ns, g


class BrowserAccountTests(unittest.TestCase):
    def browser_mocks(self, root, kind='firefox', username='alice'):
        server = Mock(); server.server_address = ('127.0.0.1', 12345)
        proc = Mock(); proc.poll.return_value = None
        start = Mock(return_value=(proc, root / 'launch.log'))
        return dict(
            _linux_display_ok=Mock(return_value=True),
            _browser_binaries=Mock(return_value=[(kind, '/mock/browser')]),
            _kill_stale_login_browsers=Mock(), _free_port=Mock(return_value=12345),
            _start_ua_sniffer=Mock(return_value=(server, {'ua': 'browser-ua'})),
            _account_browser_profile=Mock(side_effect=lambda kind, site, user: root / (kind+'-'+user)),
            _firefox_default_profile=Mock(side_effect=AssertionError('must not use daily profile')),
            _firefox_user_agent=Mock(return_value='browser-ua'),
            _start_real_browser=start, _wait_debug_port=Mock(return_value=True),
            _cdp_harvest=Mock(return_value=('UOJSESSID=test', 'browser-ua', '<html>logged in</html>')),
            _firefox_sqlite_cookies=Mock(return_value={'UOJSESSID': 'test'}),
            Client=Mock(return_value=Mock(get=Mock(return_value=(200, 'https://qoj.ac/', '<html>logged in</html>')))),
            _session_ready=Mock(return_value=True), extract_username=Mock(return_value=username),
        )

    def test_default_login_always_starts_fresh_for_both_browsers(self):
        for kind in ['firefox', 'chromium']:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                mocks = self.browser_mocks(root, kind)
                with patch.dict(g, **mocks), patch.object(g['time'], 'sleep'), contextlib.redirect_stdout(io.StringIO()):
                    first = ns['_login_real_browser']('https://qoj.ac')
                    second = ns['_login_real_browser']('https://qoj.ac')
                self.assertEqual(first[0], 'UOJSESSID=test')
                self.assertEqual(second[0], 'UOJSESSID=test')
                calls = mocks['_start_real_browser'].call_args_list
                self.assertNotEqual(calls[0].args[3], calls[1].args[3])
                for call in calls:
                    self.assertTrue(call.kwargs['isolated'])
                    self.assertFalse(call.args[3].exists())
                mocks['_firefox_default_profile'].assert_not_called()
                self.assertEqual(mocks['_start_real_browser'].return_value[0].wait.call_count, 2)

    def test_named_accounts_use_separate_persistent_profiles(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mocks = self.browser_mocks(root)
            with patch.dict(g, **mocks), patch.object(g['time'], 'sleep'), contextlib.redirect_stdout(io.StringIO()):
                ns['_login_real_browser']('https://qoj.ac', 'alice')
                ns['_login_real_browser']('https://qoj.ac', 'alice')
                mocks['extract_username'].return_value = 'bob'
                ns['_login_real_browser']('https://qoj.ac', 'bob')
            calls = mocks['_start_real_browser'].call_args_list
            self.assertEqual(calls[0].args[3], calls[1].args[3])
            self.assertNotEqual(calls[0].args[3], calls[2].args[3])
            self.assertTrue(all(call.kwargs['isolated'] for call in calls))

    def test_profile_keys_include_site_username_and_browser(self):
        profile = ns['_account_browser_profile']
        paths = [profile('firefox', 'https://qoj.ac', 'alice'),
                 profile('firefox', 'https://qoj.ac', 'bob'),
                 profile('firefox', 'https://codeforces.com', 'alice'),
                 profile('chromium', 'https://qoj.ac', 'alice')]
        self.assertEqual(len(set(paths)), 4)

    def test_saving_new_login_preserves_previous_credentials(self):
        cfg = {'site': 'https://qoj.ac'}
        with patch.dict(g, save_global=Mock()):
            ns['save_account'](cfg, 'https://qoj.ac', 'session=alice', 'ua', 'alice')
            ns['save_account'](cfg, 'https://qoj.ac', 'session=bob', 'ua', 'bob')
        saved = ns['saved_accounts'](cfg, 'https://qoj.ac')
        self.assertEqual(saved['alice']['cookie'], 'session=alice')
        self.assertEqual(saved['bob']['cookie'], 'session=bob')

    def test_failed_launch_cleans_temporary_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            mocks = self.browser_mocks(Path(directory))
            mocks['_start_real_browser'].side_effect = OSError('cannot launch')
            with patch.dict(g, **mocks), contextlib.redirect_stdout(io.StringIO()):
                self.assertIsNone(ns['_login_real_browser']('https://qoj.ac'))
            profile = mocks['_start_real_browser'].call_args.args[3]
            self.assertFalse(profile.exists())
