#!/usr/bin/env python
'''
Created on May 17, 2013

@author: ruben
'''

import sys
from collections import defaultdict
from operator import itemgetter

def solve_by_average(list_polarities):
    total = defaultdict(float)
    count = defaultdict(int)
    for pol,conf in list_polarities:
        total[pol] += float(conf)
        count[pol] += 1
    
    final_pol = [(polarity,total[polarity]*1.0/count[polarity]) for polarity in total.keys()]
    final_pol.sort(key=itemgetter(1),reverse=True)
    best_value = final_pol[0][1]
    tied = sum(1 for pol,val in final_pol if val==best_value)
    if tied > 1:
        return 'neutral',best_value
    else:
        return final_pol[0]
    
    
def solve_by_max(list_polarities):
    max_for_pol = {}
    for pol,val in list_polarities:
        if pol not in max_for_pol or val>max_for_pol[pol]:
            max_for_pol[pol] = val
    
    del list_polarities
    list_polarities = max_for_pol.items()
    
    list_polarities.sort(key=itemgetter(1),reverse=True)
    best_value = list_polarities[0][1]
    tied = sum(1 for pol,val in list_polarities if val==best_value)
        
    if tied == 1:
        return list_polarities[0]
    elif tied == 2:
        if list_polarities[0][0]=='neutral': return list_polarities[1]
        if list_polarities[1][0]=='neutral': return list_polarities[0]
        return list_polarities[0]
    elif tied == 3:
        return 'neutral',best_value
    else:
        return list_polarities[0]
    
def majority(list_polarities):
    count = defaultdict(int)
    accum = defaultdict(float)
    for pol,conf in list_polarities:
        count[pol] += 1
        accum[pol] += float(conf)

    list_counts = count.items()
    list_counts.sort(key=itemgetter(1),reverse=1)
    if len(list_counts) == 1:
        pol = list_counts[0][0]
        conf = accum[pol]/list_counts[0][1]
        return pol, conf
    else:
        if list_counts[0][1] == list_counts[1][1]:
            pol = 'neutral'
            conf = accum[list_counts[0][0]]/count[list_counts[0][0]]
            return pol, conf
        else:
            pol = list_counts[0][0]
            conf = accum[pol] / list_counts[0][1]
            return pol, conf
  
  
if __name__ == '__main__':
    
    if len(sys.argv) == 1:
        print>>sys.stderr,'Specify the type of conversion required:'
        print>>sys.stderr,sys.argv[0],' -max --> for selecting the polarity with maximum confidence'
        print>>sys.stderr,sys.argv[0],' -avg --> for selecting the polarity with greater average confidence'
        print>>sys.stderr,sys.argv[0],' -maj --> for selecting the polarity with greater average confidence'
        sys.exit(-1)
        
    type_of_solving = sys.argv[1]
    
    polarities_for_lemma = {}
    for line in sys.stdin:
        fields = line.strip().split(';')
        pos = fields[1]
        polarity = fields[2]
        confidence = fields[3]
        lemmas = fields[4].split(',')
        for lemma in lemmas:
            if (lemma,pos) in polarities_for_lemma:
                polarities_for_lemma[(lemma,pos)].append((polarity,confidence))
            else:
                polarities_for_lemma[(lemma,pos)]=[(polarity,confidence)]

    for (lemma,pos),polarities in polarities_for_lemma.items():
        if type_of_solving == '-max':
            pol, conf = solve_by_max(polarities)
        elif type_of_solving == '-avg':
            pol,conf = solve_by_average(polarities)
        elif type_of_solving == '-maj':
            pol,conf = majority(polarities)
        else:
            pol, conf = solve_by_max(polarities)
            
        if float(conf) >= 0.9999: 
          my_freq='1'
        else: 
          my_freq='-1'
        print 'unknown;'+pos+';'+pol+';'+str(conf)+';'+lemma+';'+my_freq
        print>>sys.stderr,'#'*20
        print>>sys.stderr,'Resolving ',lemma,pos,'   Assigned polarity ',pol,'with AVG conf: ',conf
        for p,c in polarities:
            print>>sys.stderr,'   '+p+': ',c
        print>>sys.stderr
    sys.exit(0)