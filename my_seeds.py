import logging
import sys
import codecs

class My_seeds:
  def __init__(self,filename):
    self.seeds = []  ## (sense, polarity, pos)
    self.map = {}
    try:
      f = codecs.open(filename,encoding='utf-8')
    except Exception as e:
      logging.error('Error opening file '+filename)
      logging.error(str(e))
      sys.exit(-1)
      
    for line in f:
      tokens = line.strip().split('/')
      if len(tokens) != 3:
        logging.debug('Skipping line '+line+' . Specify sense/polarity/pos')
      else:
        sense,polarity,pos = tokens
        self.seeds.append((sense,polarity,pos))
        self.map[sense]=polarity
    f.close()
    logging.debug('Loaded '+str(len(self.seeds))+' seeds')
    
  def __iter__(self):
    for s,pol,pos in self.seeds:
      yield (s,pol,pos)
      
  def length(self):
    return len(self.seeds)
    
  def get_polarity(self,synset):
    return self.map.get(synset,None)
