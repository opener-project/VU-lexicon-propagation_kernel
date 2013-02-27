VU-lexicon-propagation_kernel
=============================

These scripts implement the propagation algorithm for automatically generation of sentiment lexicons from WordNet.
There are two main scripts to generate a lexicon:
1) propagate_wn.py --> this script propagates a list of seeds over WordNet and generates and intermediate CSV format
2) from_csv_to_lmf.py --> this script reads the previous CSV format and generates the final Opener-LMF lexicon


Installation and requirements
-----------------------------

The scripts are Python, so you need to have Python installed in your machine (version >=2.6). Also you need the lxml library for XML
processing. To install this requirement, you can just run:
````shell
$ pip install -r requirements.txt
````
There is nothing else required to run these scripts.


General Approach
----------------

The general approach to generate a lexicon these are the required steps:

1. Get the WordNet in LMF format for your language
2. Generate/translate a list of seeds
3. Create the list with the relations you want to use for the propagation
4. Run the script propagate_wn.py to generate the CSV file
5. Manually check the most frequent words of your language and modify that CSV file
6. From the corrected CSV, with the from_csv_to_lmf.py script, generate the final LMF lexicon


Seed list
---------

The seed list has to be stored in a file, wit a seed per line, with the format:
synset/polarity/pos

For instance:  
n_n-531677/negative/n  
n_n-531685/neutral/n  
n_n-531697/positive/n  
n_n-531759/negative/n  
n_n-531792/neutral/n  
n_n-531952/neutral/n  
......

The seed list can be based also in sense identifiers instead of synset identifiers, but the use of synsets ids
is strongly recommended.


Relations file
--------------

The WordNet relations that you want to use for the propagation have to be stored in a file. You have to be sure that the
labels for the relations match with the labels of the relations in your WordNet. You have to associate a weight to each
relation, that will represent how the strength of a polarity is modified when it is propagated through that relation. For
instance: we have a synset with a positive polarity with strength 3, and we propagate this positive polarity to all its
hyponyms. In the relations file we defined a weight to 0.1 for HYPONYMY, so all the hyponyms will get a positive polarity
with a weight of 0.3 (3*0.1). If the weight is negative, we will invert the polarity when propagation throught that kind
of relations

In our experiments, we have used the following configuration for the relations file with good results, so it could be a good
idea to use also these relations addapted to your own labels in case they differ.  

NEAR_SYNONYM 2  
NEAR_ANTONYM -2  
HAS_HYPONYM 1  
HAS_HYPERONYM 0.5  


Script propagate_wn.py
----------------------

You can get the usage of this script by simply running:
````shell
$ python propagate_wn.py -h
````

The options and parameters for this script are the following:
* Required:
  *  --wn=FILE file with wordnet in LMF format
  *  --seed-list=FILE file with list of seeds with polarities
  *  --relations=FILE file with relations and weights
  *  --out=FILE file to store the results in CSV format
  *  --seed-sense In case your seed list is based on senses and not synsets
  
* Optional:
  *  --log=FILE Filename where store the log (default no log)
  *  --out-lemmas To force the output at lemma level instead of synset (default is synsets)
  *  --max-depth=INT Maximum depth in number of relations to expand each synset (default 5) 
	
Example:
````shell
$ python propagate_wn.py  --wn=cornetto.lmf.xml --seed-list=file_seeds.txt --relations=my_rels.txt --out my_output.csv
````
    
    
Script from_csv_to_lmf.py
------------------------

This script reads the CSV and generates the final Opener-LMF format. To run the program:
````shell
$ cat my_output.csv | python from_csv_to_lmf.py > my_lexicon.lmf
````

There is one option (-verbose) you can set to the program:
````shell
$ cat my_output.csv | python from_csv_to_lmf.py -verbose > my_lexicon.lmf
````

With the verbose option we will create one lexical entry for each lemma. So for instance if we have in our CSV output:
n_n-526797;N;neutral;0.5;scheepmaker,scheepsbouwer,scheepsmaker

This means that the synset n_n-526797, which is a noun (N), has a neutral polarity with strength 0.5, and the words in this synset
are three:scheepmaker, scheepsbouwer and scheepsmaker.
If we create the LMF lexicon without the verbos option, there will be only one lexical entry for scheepmaker, with the synset
n_n-526797 and the neutral polarity associated (The polarity actually is linked to the synset and not to the word).
With the verbose option, we will have three lexical entries, one for each word in the synset, with the same information.


Contact
------
Ruben Izquierdo
Vrije University of Amsterdam
ruben.izquierdobevia@vu.nl


