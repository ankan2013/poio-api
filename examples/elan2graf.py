# -*- coding: utf-8 -*-
# Poio Tools for Linguists
#
# Copyright (C) 2009-2013 Poio Project
# Author: António Lopes <alopes@cidles.eu>
# URL: <http://media.cidles.eu/poio/>
# For license information, see LICENSE.TXT

import sys, getopt

from poioapi.io import elan
from poioapi import data

def main(argv):

    inputfile = ''
    outputfile = ''

    try:
        opts, args = getopt.getopt(argv,"hi:o:",["ifile=","ofile="])
    except getopt.GetoptError:
        print('elan2graf.py -i <inputfile> -o <outputfile>')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print('elan2graf.py -i <inputfile> -o <outputfile>')
            sys.exit()
        elif opt in ('-i', '--ifile'):
            inputfile = arg
        elif opt in ('-o', '--ofile'):
            outputfile = arg

    if inputfile == "" or outputfile == "":
        print('elan2graf.py -i <inputfile> -o <outputfile>')
        sys.exit()

    # Initialize
    data_hierarchy = ['utterance',['words',['part_of_speech']],
                      'phonetic_transcription','gestures',
                      'gesture_phases','gesture_meaning']

    elan_graf = elan.Elan(inputfile, data_hierarchy)

    # Create a GrAF object
    graph = elan_graf.elan_to_graf()

    # Create GrAF Xml files
    elan_graf.generate_graf_files()

    # Rendering the GrAF object to an Xml file
    elan_graf.graph_rendering(outputfile, graph)

    print('Finished')

if __name__ == "__main__":
    main(sys.argv[1:])