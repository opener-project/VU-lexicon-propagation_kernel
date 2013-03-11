#!/usr/bin/env python

from lxml import etree
import sys

if sys.stdin.isatty():
  print 'Usage: cat lexicon.lmf | ',sys.argv[0]
  sys.exit(0)

dtd = etree.DTD('opener_lmf.dtd')
tree = etree.parse(sys.stdin,etree.XMLParser(remove_blank_text=True))

res = dtd.validate(tree)
if res:
  print 'Correct. The input lexicon complies with the DTD'
else:
  print 'Error!!'
  print(dtd.error_log.filter_from_errors()[0])
print
sys.exit(0)