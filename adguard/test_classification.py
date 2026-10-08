import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('merge',Path(__file__).with_name('merge.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class ClassificationTests(unittest.TestCase):
    def test_exceptions_by_semantics_not_source(self):
        for line in ('@@||EXAMPLE.COM^','foo.example#@#.banner','||example.org^$badfilter','||example.org^$script,badfilter'):
            self.assertTrue(m.is_exception(line),line)
        for line in ('||ads.example.com^','example.com##.ad','||domain.test^$important','/AdBanner[0-9]+/'):
            self.assertFalse(m.is_exception(line),line)

    def test_dns_only_classes(self):
        self.assertEqual(m.dns_black_rule('||ADS.EXAMPLE.COM^'), '||ads.example.com^')
        self.assertEqual(m.dns_black_rule('||ADS.EXAMPLE.COM^$important'), '||ads.example.com^$important')
        self.assertEqual(m.dns_black_rule('||ads.example.com^$IMPORTANT'), '||ads.example.com^$important')
        self.assertEqual(m.dns_white_rule('@@||ALLOW.EXAMPLE.COM^'), '@@||allow.example.com^')
        for value in ('||example.org^$important,third-party','||example.com/Path','example.com##.ad','||foo..com^'):
            self.assertIsNone(m.dns_black_rule(value))
        self.assertIsNone(m.dns_white_rule('||black.example.com^'))
        self.assertIsNone(m.dns_white_rule('@@||allow.example.com^$third-party'))

    def test_white_source_kept_without_syntax_filter(self):
        black_source = ['||ads.example.com^', '@@||safe.example.com^']
        white_source = ['@@||login.example.com^', '||bad-from-white.example.com^', 'example.com#@#.banner']
        black = [m.dns_black_rule(x) for x in black_source]
        white = m.dedupe_preserve_order(m.normalize(x) for x in black_source if x.startswith('@@'))
        white += m.dedupe_preserve_order(m.normalize(x) for x in white_source)
        self.assertEqual([x for x in black if x], ['||ads.example.com^'])
        self.assertIn('||bad-from-white.example.com^', white)
        self.assertIn('example.com#@#.banner', white)
        self.assertIn('@@||safe.example.com^', white)

    def test_case_sensitive_parts_preserved(self):
        rules=['||EXAMPLE.COM^','||example.com^','@@||Allow.COM^','example.com##.AdBanner','/Tracking[A-Z]+/','||example.com/Path?Token=AbC$script']
        normalized=m.dedupe_preserve_order(m.normalize(x) for x in rules)
        self.assertEqual(normalized,['||example.com^','@@||allow.com^','example.com##.AdBanner','/Tracking[A-Z]+/','||example.com/Path?Token=AbC$script'])

if __name__=='__main__':unittest.main()
