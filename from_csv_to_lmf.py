#!/usr/bin/env python

import sys
from lxml import etree

if __name__ == '__main__':
  if sys.stdin.isatty():
    print>>sys.stderr,'Input stream required.'
    print>>sys.stderr,'Example usage: cat my_lexicon.utf8.csv |',sys.argv[0],'-verbose'
    print>>sys.stderr,'\t-verbose option to generate the lexicon with all the lemmas for one synset'
    print>>sys.stderr,'\tInput file format: synset;polarity;value;lemma1,lemma2,lemma3'
    print>>sys.stderr
    print>>sys.stderr
    sys.exit(-1)
    
    
  verbose = False
  if len(sys.argv)==2:
    if sys.argv[1]=='-verbose':
      verbose = True
    else:
      print>>sys.stderr,'Option ',sys.argv[1],'not recognized. Verbosity=',verbose
  

    
  my_root = etree.Element('LexicalResource')
  my_global = etree.Element('GlobalInformation')
  my_global.set('label','Created with the standard propagation algorithm')
  my_root.append(my_global)
  my_lexicon = etree.Element('Lexicon')
  my_root.append(my_lexicon)
  n=0
  for line in sys.stdin:
    tokens = line.decode('utf-8').strip().split(';')
    if len(tokens)!=5:
      print>>sys.stderr,'Skipped line because has not the correct format'
    else:
      synset = tokens[0]
      pos = tokens[1]
      polarity = tokens[2]
      try:
        value = float(tokens[3])
      except:
        value=-1
      lemmas = tokens[4].split(',')
      
      my_lemmas = []
      if verbose:
        my_lemmas = lemmas
      else:
        my_lemmas = [lemmas[0]]
        
      for my_lemma in my_lemmas:
        lex_ent = etree.Element('LexicalEntry',attrib={'id':'id_'+str(n),'partOfSpeech':pos})
        n+=1
        my_lexicon.append(lex_ent)
        l_obj = etree.Element('Lemma',attrib={'writtenForm':my_lemma})
        lex_ent.append(l_obj)
        sense = etree.Element('Sense')
        sense.append(etree.Element('Sentiment',attrib={'polarity':polarity}))
        if synset != 'unknown':
          sense.append(etree.Element('MonolingualExternalReference',attrib={'reference':str(synset)}))

        lex_ent.append(etree.Element('Confidence',attrib={'value':str(value)}))
        lex_ent.append(sense)

  my_tree = etree.ElementTree(my_root)
  my_tree.write(sys.stdout,encoding='UTF-8',pretty_print=1, xml_declaration=1)
    