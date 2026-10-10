import contextlib
import io
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from test_submit import ns, g, contest


class ProblemStandingsTests(unittest.TestCase):
    def page(self, scores, ids=None, partial=False):
        return '<script>contest_type="ICPC"; problems=' + json.dumps(ids or [100]) + '; score=' + json.dumps(scores) + '; var icpc_partial_scores=' + json.dumps(partial) + ';</script>'

    def test_status_and_team_counts(self):
        for points, failures, pending, expected in [(100, 0, 0, '+(0)'), (100, 2, 0, '+(2)'), (0, 2, 0, '-(3)'), (0, 2, 1, '?(3)'), (97, 2, 0, '+(2)')]:
            with self.subTest(expected=expected):
                scores = {'alice': {'0': [points, 60, 1, failures, 100, pending]},
                          'bob': [[100, 70, 2, 0, 100, 0]], 'carol': [[0, 70, 3, 0, 100, 0]]}
                result = ns['parse_qoj_problem_standings'](self.page(scores), contest())['100']
                self.assertEqual(result['status'], expected)
                self.assertEqual(result['solved'], 1 + int(expected.startswith('+')))

    def test_unsubmitted_and_empty_php_array(self):
        for scores in [{}, [], {'bob': [[100, 60, 1, 0, 100, 0]]}, {'alice': [None]}]:
            result = ns['parse_qoj_problem_standings'](self.page(scores), contest())
            self.assertEqual(result['100']['status'], '')

    def test_partial_score_and_pending(self):
        scores = {'alice': [[97, 60, 1, 2, 100, 0, 0, 0]]}
        result = ns['parse_qoj_problem_standings'](self.page(scores, partial=True), contest())
        self.assertEqual(result['100'], {'status': '-(3)', 'solved': 0})
        scores['alice'][0][5], scores['alice'][0][7] = 1, 4
        result = ns['parse_qoj_problem_standings'](self.page(scores, partial=True), contest())
        self.assertEqual(result['100']['status'], '?(4)')

    def test_single_quoted_type_and_declarations(self):
        page = "<script>var contest_type='ICPC'; var problems=[100]; var score={};</script>"
        self.assertEqual(ns['parse_qoj_problem_standings'](page, contest())['100']['solved'], 0)

    def test_invalid_data_is_not_empty_success(self):
        for page in ['<html>Login</html>', self.page({}, ids=[101]), self.page({'alice': [[100]]})]:
            with self.subTest(page=page), self.assertRaises(OSError):
                ns['parse_qoj_problem_standings'](page, contest())

    def test_fetch_rejects_login_and_http_error(self):
        for response in [(200, 'https://qoj.ac/login', '<form></form>'), (503, contest()['contest_url']+'/standings', '')]:
            client = Mock(); client.get.return_value = response
            with self.assertRaises(OSError):
                ns['fetch_qoj_problem_standings'](client, contest())

    def test_sort_and_ties(self):
        problems = {k: {'id': k, 'title': 'Title '+k} for k in ['C2', 'C1', 'B', 'A']}
        standings = {k: {'status': '', 'solved': 5 if k != 'A' else 0} for k in problems}
        with contextlib.redirect_stdout(io.StringIO()) as out:
            ns['_print_problems'](problems, standings, True, True)
        self.assertEqual([line.split()[0] for line in out.getvalue().splitlines() if 'Title ' in line], ['B', 'C1', 'C2', 'A'])

    def test_current_account_and_failure(self):
        fetch = Mock(return_value={'100': {'status': '+(2)', 'solved': 10}})
        args = SimpleNamespace(sort_by_solved=False, offline=False, debug=False)
        with patch.dict(g, require_contest=Mock(return_value=(Path('unused'), contest())), load_global=Mock(return_value={}), get_account=Mock(return_value={'username': 'bob'}), make_client=Mock(), fetch_qoj_problem_standings=fetch), contextlib.redirect_stdout(io.StringIO()) as out:
            ns['cmd_problems'](args)
            self.assertEqual(fetch.call_args.args[1]['username'], 'bob')
            self.assertIn('+(2)', out.getvalue())
            fetch.side_effect = OSError('unavailable')
            ns['cmd_problems'](args)
            self.assertIn('?              ?', out.getvalue())
            args.sort_by_solved = True
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                ns['cmd_problems'](args)

    def test_offline_and_alias(self):
        make = Mock()
        with patch.dict(g, require_contest=Mock(return_value=(Path('unused'), contest())), make_client=make), contextlib.redirect_stdout(io.StringIO()):
            ns['cmd_problems'](SimpleNamespace(offline=True, sort_by_solved=False))
        make.assert_not_called()
        self.assertTrue(ns['build_parser']().parse_args(['list', '--sort-by-solved']).sort_by_solved)
