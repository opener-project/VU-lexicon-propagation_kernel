#!/usr/bin/env python 

########################
# List of changes
# 12-Feb-2013 --> added code for generating opener-lmf format
########################

import logging
import sys
import codecs
import operator
from collections import defaultdict
import getopt
from lxml import etree
import os
import glob
import shutil
import tempfile

from my_wordnet_lmf import My_wordnet
from my_seeds import My_seeds

class My_synset:
  def __init__(self,id):
    self.id = id
     
      
  def set_polarity(self,polarity,chain):
    self.polarity = polarity
    self.chain_relations = chain
    
  def compute_value(self,map_values):
    p = 1
    for relation in self.chain_relations:
      value = map_values[relation]
      p = p * value
    self.value = p / len(self.chain_relations)
    
  def get_inverted_polarity(self):
    if self.polarity.lower() == 'positive':
      return 'negative'
    if self.polarity.lower() == 'negative':
      return 'positive'
    if self.polarity.lower() == 'neutral':
      return 'neutral'
    
  def resolve_synset(self,map_values):
    value = 1
    for relation in self.chain_relations:
      value = value * map_values[relation]
    value = value / len(self.chain_relations)
    
    if value == 0:
      final_pol = 'neutral'
    elif value > 0:
      final_pol = self.polarity
    else:
      final_pol = self.get_inverted_polarity()
      value = value * -1    ## Converted to positive
      
    ##Computing the chain
    final_chain = self.polarity
    for rel in self.chain_relations:
      final_chain += ' -> ' + rel
    
    return final_pol,final_chain,value

  
  def __repr__(self):
    return 'ID:'+self.id+' Pos:'+str(self.pos)+' POL:'+str(self.polarity)+' RELS:'+str(self.chain_relations)
    
    

def load_relations(filename):
  my_rels = {}
  try:
    f = open(filename)
    for line in f:
      relation, value = line.strip().split(' ')
      my_rels[relation] = float(value)
    f.close()
  except Exception as e:
    print>>sys.stderr,'Error opening or reading file',filename
    print>>sys.stderr,str(e)
    sys.exit(-1)
  return my_rels
  
def usage(cmd):
  print 'Script for creating a sentiment polarity lexicon'
  print 'Usage: ',cmd,' parameters'
  print 'Parameters:'
  print '\tRequired:'
  print '\t\t--wn=FILE file with wordnet in LMF format'
  print '\t\t--seed-list=FILE file with list of seeds with polarities'
  print '\t\t--relations=FILE file with relations and weights'
  print '\t\t--out=FILE file to store the results'
  print '\t\t--seed-sense In case your seed list is based on senses and not synsets'
  print '\tOptional:'
  print '\t\t--log=FILE Filename where store the log (default no log)'
  print '\t\t--out-lemmas To force the output for lemma instead of synset (default is synsets)'
  print '\t\t--max-depth=INT Maximum depth in number of relations to expand each synset (default 5) '
  print '\tExample:'
  print '\t\t',cmd,' --wn=cornetto.lmf.xml --seed-list=file_seeds.txt --relations=my_rels.txt'
  
if __name__ == '__main__':
  logging.basicConfig(stream=sys.stderr,format='%(asctime)s - %(levelname)s - %(message)s',level=logging.DEBUG)
  seed_list_file = None
  wn_file = None
  relations_file = None
  log_file = None
  out_file = None
  seed_sense = False
  output_lemmas = False
  max_depth = 5
  try:
    opts, args = getopt.getopt(sys.argv[1:],"h",["seed-list=","wn=","relations=","out=","log=","max-depth=","seed-sense","out-lemmas"])
    for opt, arg in opts:
      if opt == "--seed-list":
        seed_list_file = arg
      elif opt == '--wn':
        wn_file = arg
      elif opt == '--relations':
        relations_file = arg
      elif opt == '--log':
        log_file = arg
      elif opt == '--out':
        out_file = arg
      elif opt == '--seed-sense':
        seed_sense = True
      elif opt == '--out-lemmas':
        output_lemmas = True
      elif opt == '--max-depth':
        max_depth = int(arg)
      elif opt == '-h':
        usage(sys.argv[0])
        sys.exit(0)
    
  except getopt.GetoptError:
    pass
    
    
 
  if wn_file == None:
    print>>sys.stderr,'Wornet file required'
    usage(sys.argv[0])
    sys.exit(-1)
    
  if seed_list_file == None:
    print>>sys.stderr,'Seef list required'
    usage(sys.argv[0])
    sys.exit(-1)

  if relations_file == None:
    print>>sys.stderr,'Relations file required'
    usage(sys.argv[0])
    sys.exit(-1)
    
  if out_file == None:
    print>>sys.stderr,'Output file required'
    usage(sys.argv[0])
    sys.exit(-1)
    
  logging.debug('Settings for this run')
  logging.debug('Seed list filename '+str(seed_list_file))
  logging.debug('Wordnet: '+str(wn_file))
  logging.debug('Relations file: '+str(relations_file))
  logging.debug('Log filename: '+str(log_file))
  logging.debug('Output filename: '+str(out_file))
  logging.debug('Seed list is senses (not synsets): '+str(seed_sense))
  logging.debug('Output lemmas instead of synsets: '+str(output_lemmas))
  logging.debug('Maximum depth in number of relations: '+str(max_depth))
  
  my_wn = My_wordnet(wn_file)
  my_seeds = My_seeds(seed_list_file)
  my_relations = load_relations(relations_file)
  
  
  value_for_direct = 5 + sum(my_relations.values())
  my_relations['direct'] = value_for_direct
  
  logging.debug('Max depth: '+str(max_depth))
  
  temp_folder = tempfile.mkdtemp()
  logging.debug('Created temp folder '+temp_folder)

  
  
  ## STEP 1 Propagate seed polarity to synsets:
  for cnt, (synset, polarity, pos) in enumerate(my_seeds):
        
    if cnt % max(1,int(5 * my_seeds.length() / 100)) == 0 :
      logging.debug('Processed '+str(cnt)+' seeds of '+str(my_seeds.length()))
    already_tagged = []
    already_visited = set()
    ## FIRST seed
    
    if seed_sense: # Map the sense to synset:
      synset = my_wn.sense_to_synset(synset)
    
    new_syn = My_synset(synset)
    new_syn.set_polarity(polarity,['direct'])

    already_tagged.append(new_syn)
    
    keep_looping = True
    while keep_looping:
      #print>>sys.stderr,'\tTagged, visited:',len(already_tagged), len(already_visited)
      keep_looping = False
      for source_synset in already_tagged:
        #print>>sys.stderr,'\t\tChecking',source_synset.id
        if source_synset.id not in already_visited:
          #print>>sys.stderr,'\t\t\tExpanding it...'
          already_visited.add(source_synset.id)
          for relation in my_relations.keys():  ##For each relation type:
            #print>>sys.stderr,'\t\t\t\tRelation: ',relation
            ## Get the synset related through this relation
            targets_synset = my_wn.get_relateds_synset(source_synset.id,relation)  
            for target_synset in targets_synset:
              #print>>sys.stderr,'\t\t\t\t\tTarget synset: ',target_synset
              new_chain_relation = source_synset.chain_relations[:]
              new_chain_relation.append(relation)
              new_synset = My_synset(target_synset)
              new_synset.set_polarity(source_synset.polarity,new_chain_relation)
              already_tagged.append(new_synset)
              #print>>sys.stderr,'\t\t\t\t\t\tAdded to already tagged'
              #print>>sys.stderr,'\t\t\t\t\t\tNew chain: ',new_chain_relation
              depth = len(new_chain_relation)
              if depth >= max_depth:
                already_visited.add(target_synset)  ## For not explore it later...
                #print>>sys.stderr,'\t\t\t\t\t\tAdded to already visited to not explode it because of maxdepth'
              else:
                #print>>sys.stderr,'\t\t\t\t\t\tKeep looping set to True'
                keep_looping = True
    ## NEXT SEED
    
    for synset in already_tagged:
      filename = os.path.join(temp_folder,synset.id)
      f = open(filename,'a')
      f.write(synset.polarity+'\t'+'\t'.join(synset.chain_relations)+'\n')
      f.close()
    del already_tagged
    del already_visited
      
  ## The final step is to resolve each synset with all the posible chains:
  log = None
  if log_file!=None:    log = codecs.open(log_file,'w',encoding='utf-8')
  
  final_solutions = {}
  best_overall_value = -1
  logging.debug('Resolving synsets')

  total_synsets = len(glob.glob(os.path.join(temp_folder,'*')))
  for cnt, filename in enumerate(glob.glob(os.path.join(temp_folder,'*'))):
    
    ## Load all the info for the synset
    synset_id = filename[filename.rfind('/')+1:]
    f = open(filename)
    possible_chains = []
    for line in f:
      fields = line.strip().split()
      polarity = fields[0]
      relations = fields[1:]
      new_synset = My_synset(synset_id)
      new_synset.set_polarity(polarity,relations)
      possible_chains.append(new_synset)
    f.close()
      
        
    if cnt % max(int(10 * total_synsets / 100),1) == 0 :
      logging.debug('Resolved '+str(cnt)+' synsets of '+str(total_synsets))

    if log!=None:
      print>>log,'Resolving synset :',synset_id
    
    options_for_synset = []
    for my_synset in possible_chains:
      final_pol,final_chain,value = my_synset.resolve_synset(my_relations)
      options_for_synset.append((final_pol,final_chain,value))
    options_for_synset.sort(key=operator.itemgetter(2),reverse=True)
    
    if log!=None:
      for fp, fc, fv in options_for_synset:
        print>>log,'  Pol:',fp
        print>>log,'  Val:',fv
        print>>log,'  Rel:',fc
        print>>log,'  '+'='*100
      
    best_value = options_for_synset[0][2]
    num_pos = num_neg = num_neu = 0
    for fp,fc,fv in options_for_synset:
      if fv == best_value:
        if fp =='positive': num_pos+=1
        elif fp=='negative': num_neg+=1
        elif fp=='neutral': num_neu+=1
      else:
        break
    if log!=None:
      print>>log, '  Num_pos:',num_pos
      print>>log, '  Num neg:',num_neg
      print>>log, '  Num neu:',num_neu
      final_pol=''
    
    if num_neu > num_pos and num_neu > num_neg:
      final_pol = 'neutral'
    else:
      if num_pos > num_neg:  final_pol = 'positive'
      elif num_neg > num_pos: final_pol = 'negative'
      else: final_pol = 'neutral'
      
    if log!=None:
      print>>log,'  Final_pol:',final_pol, best_value
      print>>log,'  '+'**'*100
      print>>log,'  '+'**'*100
      
    final_solutions[synset_id]=(final_pol,best_value)
    if best_value >= best_overall_value:
      best_overall_value = best_value
      

  ## End, just print the results
  #if best_overall_value > value_for_direct:
  #  best_overall_value = value_for_direct
    
    
  #The output should be 
    
  
  f = codecs.open(out_file,'w','utf-8')

  
  data = []
  max = -1
  if output_lemmas:
    
    if log: print>>log,'Calculating polarity for lemmas'
    
    for n,(lemma, synsets) in enumerate(my_wn.get_lemma_synsets()):     
      
      if log: print>>log,'\tResolving',lemma.encode('utf-8')
      sol = defaultdict(float)
      for s in synsets:
        pol,val = final_solutions.get(s,[None,None])
        if log: print>>log,'\t\t ',s, pol,'=',val
        if pol is not None:
          sol[pol]+=val
          
      if len(sol)!=0:
        final_pol, final_val = sorted(sol.items(),key=operator.itemgetter(1),reverse=True)[0]
        pos = my_wn.get_pos_for_synset(synsets[0])
        if final_val > max: 
          max = final_val
        data.append(('unknown',pos,final_pol,final_val,lemma))
        #print>>f,'unknown;'+pos+';'+final_pol+';'+str(final_val)+';'+str(best_overall_value)+';'+str(final_val*1.0/best_overall_value)+';'+lemma+';-1'

  else:
    
    n = 0 
    for synset, (polarity, value) in final_solutions.items():
      pos=my_wn.get_pos_for_synset(synset)
      if value>=max: max=value
      data.append((synset,pos,polarity,value,','.join(my_wn.lemmas_for_synset.get(synset,[]))))
#      print>>f, synset+';'+pos+';'+polarity+';'+str(value/best_overall_value)+';'+','.join(my_wn.lemmas_for_synset.get(synset,[]))+';-1'
  
  
  for synset,pos,pol,value,lemmas in data:
    print>>f,synset+';'+pos+';'+pol+';'+str(value/max)+';'+lemmas+';-1'
  f.close()
    

         
    

  f.close()
  logging.debug('Output in file '+out_file)

  if log!=None:
    log.close()
    
    
  shutil.rmtree(temp_folder)
  logging.debug('Deleted temp folder '+temp_folder)
        