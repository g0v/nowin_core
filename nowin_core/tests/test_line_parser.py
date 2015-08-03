import unittest

from nowin_core.source.line_parser import LineParser


class TestLineParser(unittest.TestCase):

    def makeOne(self):
        return LineParser()

    def testParser(self):
        p = self.makeOne()

        p.feed('abc')
        line = p.getLine()
        self.assertEqual(line, None)

        p.feed('\r\n')
        line = p.getLine()
        self.assertEqual(line, 'abc')
        line = p.getLine()
        self.assertEqual(line, None)

        # write lots line
        p.feed('111\r\n222\r\n3333')
        lines = list(p.iterLines())
        self.assertEqual(['111', '222'], lines)
        line = p.getLine()
        self.assertEqual(line, None)

        p.feed('\r\ntext')
        line = p.getLine()
        self.assertEqual(line, '3333')
        line = p.getLine()
        self.assertEqual(line, None)

        # write nothing
        p.feed('')
        line = p.getLine()
        self.assertEqual(line, None)

        p.feed('\r\n')
        lines = list(p.iterLines())
        self.assertEqual(lines, ['text'])

        self.assertEqual(list(p.iterLines()), [])


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestLineParser))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
