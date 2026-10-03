import contextlib
import io
import json
import os
import runpy
import sqlite3
import struct
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ['QOJ_SUBMIT_NOVENV'] = '1'
ns = runpy.run_path(str(Path(__file__).with_name('submit')))
g = ns['save_account'].__globals__
QOJ = 'https://qoj.ac'
CF = 'https://codeforces.com'


def literal_lz4(raw):
    n = len(raw)
    block = bytearray([min(n, 15) << 4])
    if n >= 15:
        n -= 15
        while n >= 255:
            block.append(255)
            n -= 255
        block.append(n)
    return b'mozLz40\0' + struct.pack('<I', len(raw)) + block + raw


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.saver = patch.dict(g, save_global=Mock())
        self.saver.start()
        self.addCleanup(self.saver.stop)

    def test_legacy_migration_and_two_accounts(self):
        cfg = dict(site=QOJ, username='alice', cookie='session=a', user_agent='ua-a')
        ns['save_account'](cfg, QOJ, 'session=b', 'ua-b', 'bob')
        self.assertEqual(set(ns['saved_accounts'](cfg, QOJ)), {'alice', 'bob'})
        self.assertEqual(ns['get_account'](cfg, QOJ)['username'], 'bob')
        with patch.dict(g, load_global=lambda: cfg), contextlib.redirect_stdout(io.StringIO()):
            ns['cmd_account'](SimpleNamespace(username='alice', site=None))
        self.assertEqual(ns['get_account'](cfg, QOJ)['cookie'], 'session=a')
        client = Mock()
        with patch.dict(g, Client=client):
            ns['make_client'](cfg, dict(site=QOJ))
        self.assertEqual(client.call_args.kwargs['cookie'], 'session=a')
        self.assertEqual(client.call_args.kwargs['user_agent'], 'ua-a')

    def test_legacy_preserved_on_login_to_another_site(self):
        cfg = dict(site=QOJ, username='alice', cookie='session=q', user_agent='q-ua')
        ns['save_account'](cfg, CF, 'session=cf', 'cf-ua', 'alice')
        self.assertEqual(ns['get_account'](cfg, QOJ)['cookie'], 'session=q')
        self.assertEqual(ns['get_account'](cfg, CF)['cookie'], 'session=cf')

    def test_logout_only_removes_active_and_never_touches_browser(self):
        cfg = {}
        ns['save_account'](cfg, QOJ, 'a=1', 'ua', 'alice')
        ns['save_account'](cfg, QOJ, 'b=1', 'ua', 'bob')
        killer = Mock()
        with patch.dict(g, _kill_stale_login_browsers=killer):
            ns['_forget_saved_login'](cfg, QOJ)
        killer.assert_not_called()
        self.assertFalse(ns['get_account'](cfg, QOJ).get('cookie'))
        self.assertEqual(set(ns['saved_accounts'](cfg, QOJ)), {'alice'})
        with patch.dict(g, load_global=lambda: cfg), contextlib.redirect_stdout(io.StringIO()):
            ns['cmd_account'](SimpleNamespace(username='alice', site=None))
        self.assertEqual(ns['get_account'](cfg, QOJ)['cookie'], 'a=1')

    def test_separate_browser_profiles_per_account_and_site(self):
        paths = {ns['_account_browser_profile']('firefox', site, username)
                 for site in (QOJ, CF) for username in ('alice', 'bob')}
        self.assertEqual(len(paths), 4)
        self.assertEqual(ns['_account_browser_profile']('firefox', QOJ, 'alice'),
                         ns['_account_browser_profile']('firefox', QOJ, 'alice'))
        path = ns['_account_browser_profile']('firefox', QOJ, '../../outside')
        self.assertNotIn('..', path.parts)

    def test_invalid_selection_does_not_change_config(self):
        cfg = {}
        ns['save_account'](cfg, QOJ, 'a=1', 'ua', 'alice')
        before = json.dumps(cfg, sort_keys=True)
        with patch.dict(g, load_global=lambda: cfg), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                ns['cmd_account'](SimpleNamespace(username='missing', site=None))
        self.assertEqual(json.dumps(cfg, sort_keys=True), before)

    def test_account_listing_hides_credentials(self):
        cfg = {}
        ns['save_account'](cfg, QOJ, 'secret-cookie=secret-value', 'secret-ua', 'alice')
        out = io.StringIO()
        with patch.dict(g, load_global=lambda: cfg), contextlib.redirect_stdout(out):
            ns['main'](['accounts'])
        self.assertIn('* alice', out.getvalue())
        self.assertNotIn('secret', out.getvalue())
        self.assertFalse(ns['looks_like_submit_target']('accounts'))
        self.assertFalse(ns['looks_like_submit_target']('account'))

    def test_mismatched_browser_account_not_saved(self):
        client = Mock()
        page = '<nav><a href="/user/profile/bob">bob</a><a href="/logout">Logout</a></nav>'
        client.get.return_value = (200, QOJ, page)
        cfg = {}
        with patch.dict(g, Client=Mock(return_value=client)), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                ns['_finalize_login'](cfg, QOJ, '__Host-UOJSESSID=x', 'ua', False, expected='alice')
        self.assertEqual(cfg, {})

    def test_new_browser_cookie_verified_and_saved(self):
        page = '<nav><a href="/user/profile/alice">alice</a><a href="/logout">Logout</a></nav>'
        client = Mock()
        client.get.return_value = (200, QOJ, page)
        client.cookie_header.return_value = '__Host-UOJSESSID=new-session'
        cfg = {}
        with patch.dict(g, Client=Mock(return_value=client)), contextlib.redirect_stdout(io.StringIO()):
            ns['_finalize_login'](cfg, QOJ, '__Host-UOJREMEMBER=remember', 'ua', False, expected='alice')
        self.assertEqual(ns['get_account'](cfg, QOJ)['username'], 'alice')
        self.assertEqual(ns['get_account'](cfg, QOJ)['cookie'], '__Host-UOJSESSID=new-session')


class FirefoxCookieTests(unittest.TestCase):
    def test_new_cookie_needs_confirmed_login(self):
        page = '<nav><a href="/logout">Logout</a></nav>'
        for cookie in ('__Host-UOJSESSID=x', '__Host-UOJREMEMBER=x'):
            self.assertTrue(ns['_session_ready'](cookie, page, QOJ))
            self.assertFalse(ns['_session_ready'](cookie, '', QOJ))
            self.assertFalse(ns['_session_ready'](cookie, '<title>Just a moment...</title>', QOJ))
        self.assertTrue(ns['_session_ready']('UOJSESSID=x; uoj_username=alice', '', QOJ))

    def test_compressed_session_and_sqlite_merge_filtering(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            session = dict(cookies=[
                dict(host='qoj.ac', name='__Host-UOJSESSID', value='session', originAttributes={'firstPartyDomain':'','geckoViewSessionContextId':'','partitionKey':'','privateBrowsingId':0,'userContextId':0}),
                dict(host='evilqoj.ac', name='evil', value='bad'),
                dict(host='qoj.ac', name='private', value='bad', originAttributes={'privateBrowsingId':1}),
                dict(host='qoj.ac', name='expired', value='bad', expiry=1),
            ])
            (root/'sessionstore.jsonlz4').write_bytes(literal_lz4(json.dumps(session).encode()))
            db = sqlite3.connect(root/'cookies.sqlite')
            db.execute('CREATE TABLE moz_cookies(host TEXT, name TEXT, value TEXT, expiry INTEGER, originAttributes TEXT)')
            db.execute("INSERT INTO moz_cookies VALUES ('qoj.ac','__Host-UOJREMEMBER','remember',9999999999,'')")
            db.execute("INSERT INTO moz_cookies VALUES ('.qoj.ac','cf_clearance','clearance',9999999999,'')")
            db.execute("INSERT INTO moz_cookies VALUES ('qoj.ac','old','bad',1,'')")
            db.commit(); db.close()
            cookies = ns['_firefox_sqlite_cookies'](root)
            self.assertEqual(cookies, {'__Host-UOJSESSID':'session','__Host-UOJREMEMBER':'remember','cf_clearance':'clearance'})

    def test_latest_session_wins_over_old_backup(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            backups = root/'sessionstore-backups'; backups.mkdir()
            for path, value, timestamp in ((root/'sessionstore.jsonlz4','old',100), (backups/'recovery.jsonlz4','new',200)):
                path.write_bytes(literal_lz4(json.dumps(dict(cookies=[dict(host='qoj.ac',name='__Host-UOJSESSID',value=value)])).encode()))
                os.utime(path, (timestamp,timestamp))
            self.assertEqual(ns['_firefox_sqlite_cookies'](root), {'__Host-UOJSESSID':'new'})

    def test_corrupt_session_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'sessionstore.jsonlz4').write_bytes(b'mozLz40\0bad')
            self.assertEqual(ns['_firefox_sqlite_cookies'](root), {})

    def test_lz4_overlapping_match(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'sessionstore.jsonlz4'
            expected = b'{"x":"' + b'a'*20 + b'"}'
            prefix = b'{"x":"a'
            block = bytes([len(prefix)<<4 | 15])+prefix+b'\x01\x00\x00'+b'\x20"}'
            p.write_bytes(b'mozLz40\0'+struct.pack('<I',len(expected))+block)
            self.assertEqual(ns['_read_firefox_session'](p), {'x':'a'*20})

    def test_cookie_json_accepts_new_names(self):
        raw = '{"Request Cookie":{"__Host-UOJSESSID":"x","__Host-UOJREMEMBER":"y"}}'
        self.assertEqual(ns['parse_cookie_input'](raw), '__Host-UOJSESSID=x; __Host-UOJREMEMBER=y')


if __name__ == '__main__':
    unittest.main()
