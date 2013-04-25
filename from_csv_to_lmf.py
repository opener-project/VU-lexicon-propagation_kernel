#!/usr/bin/env python

import sys
from lxml import etree

if __name__ == '__main__':
  if sys.stdin.isatty():
    print>>sys.stderr,'Input stream required.'
    print>>sys.stderr,'Example usage: cat my_lexicon.utf8.csv |',sys.argv[0],'-verbose'
    print>>sys.stderr,'\t-verbose option to generate the lexicon with all the lemmas for one synset'
    print>>sys.stderr,'\tInput file format: synset;polarity;value;lemma1,lemma2,lemma3  OR'
    print>>sys.stderr,'\tInput file format: synset;polarity;value;lemma1,lemma2,lemma3;sentiment_modifier (intensifier,shifter...)'
    print>>sys.stderr,'''\nIn case you ran the propagate_wn.py with the output lemmas option the CSV file
can contain 2 types of lines:'''
    print>>sys.stderr,'\tInput file format: unknown;polarity;value;lemma OR'
    print>>sys.stderr,'\tInput file format: unknown;polarity;value;lemma;modifier'
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
  my_lexicon.set('languageCoding','UTF-8')
  my_lexicon.set('label','sentiment')
  my_lexicon.set('language',"-")

  my_root.append(my_lexicon)
  n=0
  for line in sys.stdin:
    tokens = line.decode('utf-8').strip().split(';')
    if len(tokens)!=6 and len(tokens)!=7:
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
      freq = tokens[5]
      
      my_lemmas = []
      if verbose:
        my_lemmas = lemmas
      else:
        my_lemmas = [lemmas[0]]
        
      if len(tokens) == 7:
        modifier = tokens[6]
      else:
        modifier = None
        
      for my_lemma in my_lemmas:
        if modifier is None:
          lex_ent = etree.Element('LexicalEntry',attrib={'id':'id_'+str(n),'partOfSpeech':pos})
        else:
          lex_ent = etree.Element('LexicalEntry',attrib={'id':'id_'+str(n),'partOfSpeech':pos,'type':modifier})
        n+=1
        my_lexicon.append(lex_ent)
        ## LEMMA
        l_obj = etree.Element('Lemma',attrib={'writtenForm':my_lemma})
        lex_ent.append(l_obj)
        
        #### SENSE
        sense = etree.Element('Sense')
        if modifier is not None:
          method = 'manual'
          value ='1'
        elif freq=='-1':
          method = 'automatic'
        else:
          method = 'manual'
          value = '1'
        sense.append(etree.Element('Confidence',attrib={'score':str(value),'method':method}))
        refs = etree.Element('MonolingualExternalRefs')
        if synset != 'unknown':
          refs.append(etree.Element('MonolingualExternalRef',attrib={'externalReference':str(synset)}))
        sense.append(refs)
        if modifier is None:
          sense.append(etree.Element('Sentiment',attrib={'polarity':polarity}))
        else:
          sense.append(etree.Element('Sentiment'))
        sense.append(etree.Element('Domain'))
        lex_ent.append(sense)

  my_tree = etree.ElementTree(my_root)
  my_tree.write(sys.stdout,encoding='UTF-8',pretty_print=1, xml_declaration=1)
    