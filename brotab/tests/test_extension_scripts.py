"""The Chrome extension can't evaluate script strings under Manifest V3, so it
recognises the scripts brotab sends with regexes instead.  Check that each
regex still matches the script it is meant to recognise."""
import json
import re
import shutil
import subprocess
from importlib import resources
from unittest import TestCase
from unittest import skipUnless

NODE = shutil.which('node')


def chrome_background():
    return resources.files('brotab').joinpath(
        'extension/chrome/background.js').read_text(encoding='utf8')


def js_string_constant(source, name):
    match = re.search(r"^const %s = '(.*)';$" % name, source, re.MULTILINE)
    return match.group(1).replace('\\\\', '\\')


def js_regex_assigned_to(source, name):
    match = re.search(r'const %s = code\.match\((/.*/[a-z]*)\);' % name, source)
    return match.group(1)


@skipUnless(NODE, 'node is needed to evaluate the extension regexes')
class TestChromeScriptRecognition(TestCase):
    def node_match(self, regex_literal, text):
        script = 'console.log(JSON.stringify(%s.exec(%s)))' % (regex_literal, json.dumps(text))
        out = subprocess.run([NODE, '-e', script], check=True,
                             capture_output=True, text=True).stdout
        return json.loads(out)

    def test_words_script_is_recognised(self):
        source = chrome_background()
        script = (js_string_constant(source, 'GET_WORDS_SCRIPT')
                  .replace('#match_regex#', r'/\w+/g')
                  .replace('#join_with#', '"\\n"'))
        match = self.node_match(js_regex_assigned_to(source, 'wordsMatch'), script)
        self.assertIsNotNone(match, script)
        self.assertEqual(match[1], r'/\w+/g')
        self.assertEqual(match[2], '"\\n"')
