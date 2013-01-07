# -*- coding: utf-8 -*-
# Poio Tools for Linguists
#
# Copyright (C) 2009-2012 Poio Project
# Author: António Lopes <alopes@cidles.eu>
# URL: <http://www.cidles.eu/ltll/poio>
# For license information, see LICENSE.TXT
"""This module contains classes to access Elan data.
The class Eaf is a low level API to .eaf files.

EafGlossTree, EafPosTree, etc. are the classes to
access the data via tree, which also contains the
original .eaf IDs. Because of this EafTrees are
read-/writeable.
"""

import os
import re
import codecs

from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring

from poioapi.io import header
from poioapi.io.parser import XmlContentHandler

from graf import Graph, GrafRenderer
from graf import Node, Edge
from graf import Annotation, AnnotationSpace
from graf import Region

class Elan:
    """
    Class that will handle elan files.

    """

    def __init__(self, filepath):
        """Class's constructor.

        Parameters
        ----------
        filepath : str
            Path of the elan file.

        """

        self.filename = os.path.basename(filepath)
        self.filepath = filepath
        (self.basedirname, _) = os.path.splitext(os.path.abspath(self.filepath))

        # Create the header file
        self.header = header.CreateHeaderFile(self.basedirname)
        self.data_structure_hierarchy = []

        self.xml_files_map = {}

    def elan_to_graf(self):
        """This method will recieve the parsed elements
        of an elan file. Then will create a GrAF object
        based in the information from the parsed elements.
        This method will also create the data structure
        hierarchy and theirs respective constraints.

        Returns
        -------
        graph : object
            GrAF object.

        See Also
        --------
        _create_data_structure

        """

        graph = Graph()

        parser = XmlContentHandler(self.filepath)
        parser.parse()

        tier_counter = 0

        data_structure_basic = []
        constraints_dict = dict()

        # Mandatory to give an author to the file
        self.header.author = 'CIDLeS'
        self.header.filename = self.filename.split('.eaf')[0]
        self.header.primaryfile = self.filename
        self.header.dataType = 'Elan file' # Type of the origin data file

        for element in parser.elan_list:

            # Common to all the nodes
            node_attributes = element[1]

            add_annotation_space = False
            only_have_annotations = True
            additional_information = True

            if element[0] == 'TIER':

                node_id = "tier-n"+str(tier_counter)
                node = Node(node_id)

                # Annotation
                ann_name = 'tier'
                ann_id = "tier-"+str(tier_counter)
                annotation = Annotation(ann_name, None, ann_id)

                for attributes in element[1]:
                    attribute = attributes.split(' - ')
                    feature = attribute[0]
                    value = attribute[1]
                    annotation.features[feature] = value

                node.annotations.add(annotation)
                graph.nodes.add(node)

                annotation_space = AnnotationSpace(ann_name)
                annotation_space.add(annotation)

                graph.annotation_spaces.add(annotation_space)

                from_node = node

                tier_counter+=1

                tier_id = [tier for tier in node_attributes if
                           'TIER_ID - ' in tier][0].split(' - ')[1]

                linguistic_type_ref = [ling_type for ling_type
                                       in node_attributes
                                       if 'LINGUISTIC_TYPE_REF - ' in
                                          ling_type][0].split(' - ')[1]

                try:
                    parent_ref = [parent for parent in node_attributes
                                           if 'PARENT_REF - ' in
                                              parent][0].split(' - ')[1]
                except IndexError as indexError:
                    parent_ref = None

                if not tier_id in data_structure_basic:
                    data_structure_basic.append((tier_id, parent_ref))

                if not tier_id in self.header.annotation_list:
                    self.header.add_annotation(self.filename, tier_id)
                    self.header.add_annotation_attributes(tier_id,
                        'tier', node_attributes)
                    for linguistic_type in parser.linguistic_type_list:
                        linguistic_type_id = [ling_type_id for ling_type_id
                                              in linguistic_type
                                              if 'LINGUISTIC_TYPE_ID - ' in
                                                 ling_type_id][0].split(' - ')[1]

                        if linguistic_type_ref == linguistic_type_id:
                            self.header.add_annotation_attributes(tier_id,
                                'linguistic_type', linguistic_type)
                            try:
                                constraint = [const for const in linguistic_type
                                              if 'CONSTRAINTS - ' in
                                                 const][0].split(' - ')[1]
                            except IndexError as indexError:
                                constraint = None

                            constraints_dict[tier_id] = constraint

                            break

                if not any([key for key in self.xml_files_map.keys()
                            if tier_id in key]):

                    # Creates the Xml Header (graphHeader)
                    element_tree = Element('graph',
                        {'xmlns':'http://www.xces.org/ns/GrAF/1.0/'})
                    graph_header = SubElement(element_tree,
                        'graphHeader')
                    labels_declaration = SubElement(graph_header,
                        'labelsDecl')
                    dependencies = SubElement(graph_header,
                        'dependencies')
                    if parent_ref is not None:
                        dependes_on = SubElement(dependencies,
                            'dependsOn', {'f.id':parent_ref})
                    annotation_spaces = SubElement(graph_header,
                        'annotationSpaces')
                    annotation_space = SubElement(annotation_spaces,
                        'annotationSpace',{'as.id':linguistic_type_ref})

                    # Add the element in a map that will contains the elements
                    # of each tier
                    self.xml_files_map[tier_id] = element_tree

                additional_information = False

            if element[0] == 'ALIGNABLE_ANNOTATION':

                # Anchors for the regions
                anchors = node_attributes
                anchor_1 = anchors[1].split(' - ')
                anchor_1 = parser.time_slot_dict[anchor_1[1]]
                anchor_2 = anchors[0].split(' - ')
                anchor_2 = parser.time_slot_dict[anchor_2[1]]
                anchors = [anchor_1, anchor_2]

                # Annotation
                ann_name = linguistic_type_ref
                ann_id = node_attributes[2].split(' - ')[1]
                annotation_value = element[3].split(' - ')[1]
                annotation = Annotation(ann_name, None, ann_id)
                annotation.features['annotation_value'] = annotation_value

                index = re.sub("\D", "", ann_id)

                node_id = tier_id+"-n"+index
                node = Node(node_id)

                region_id = tier_id+"-r"+index
                region = Region(region_id, *anchors)

                edge_id = element[0]+"-e"+index
                edge = Edge(edge_id, from_node, node)

                node.annotations.add(annotation)
                node.add_region(region)

                depends = element[2].split(' - ')[1]

                if not depends in graph.header.depends_on:
                    graph.header.add_dependency(depends)

                graph.regions.add(region)
                graph.edges.add(edge)
                graph.nodes.add(node)

                # Reference to the node that the
                # annotation belongs to
                reference_local = node_id

                add_annotation_space = True
                only_have_annotations = False
                additional_information = False

            if element[0] == 'REF_ANNOTATION':

                # Annotation
                ann_name = linguistic_type_ref
                ann_id = node_attributes[1].split(' - ')[1]
                # The REF_ANNOTATION are annotation that points
                # to another annotation
                reference_local = node_attributes[1].split(' - ')[0]
                annotation_value = element[3].split(' - ')[1]
                annotation = Annotation(ann_name, None, ann_id)
                annotation.features['annotation_value'] = annotation_value

                index = re.sub("\D", "", ann_id)

                node_id = tier_id+"-n"+index
                node = Node(node_id)

                node.annotations.add(annotation)
                graph.nodes.add(node)

                add_annotation_space = True
                additional_information = False

            if add_annotation_space:

                # Adding elements to Xml file
                if not only_have_annotations:
                    graph_node = SubElement(element_tree, 'node',
                            {'xml:id':node_id})
                    # Link
                    SubElement(graph_node, 'link', {'targets':region_id})
                    # Edge
                    SubElement(element_tree, 'edge', {'from':from_node.id,
                                                      'to':node_id,
                                                      'xml:id':edge_id})
                    # Region
                    SubElement(element_tree, 'region',
                            {'anchors':anchor_1+" "+anchor_2,
                             'xml:id':region_id})

                annotation_space = AnnotationSpace(linguistic_type_ref)
                annotation_space.add(annotation)

                graph.annotation_spaces.add(annotation_space)

                graph_annotation = SubElement(element_tree, 'a',
                        {'as':linguistic_type_ref,
                         'label':linguistic_type_ref,
                         'ref':reference_local,
                         'xml:id':annotation.id})
                features = SubElement(graph_annotation, 'fs')
                feature = SubElement(features, 'f', {'name':'annotation_value'})
                feature.text = annotation_value

                self.xml_files_map[tier_id] = element_tree

            # Save the additional information in a
            # extra list in the graph
            if additional_information:
                graph.additional_information.append(element)

        # Close the header file
        self.header.create_header()

        # Create the data structure hierarchy based on the elan tiers
        self.data_structure_hierarchy = \
        self._create_data_structure(data_structure_basic)

        return graph

    def _create_data_structure(self, data_structure_basic):
        """This method will create the data structure hierarchy
        based on the tiers from the elan file.

        Parameters
        ----------
        data_structure_basic : array_like
            Array with the tiers not order.

        Returns
        -------
        data_structure_hierarchy: array_like
            Array with the tiers arrange by the correct order.

        """

        data_structure_hierarchy = []
        data_hierarchy_dict = dict()

        # Mapping the tiers with the parent
        # references (Dependencies)
        for structure_element in data_structure_basic:
            tier = structure_element[0]
            empty_parents = True
            child_list = []
            for parents in data_structure_basic:
                parent = parents[1]
                if tier == parent:
                    child_list.append(parents[0])
                    empty_parents = False

            if empty_parents:
                data_hierarchy_dict[tier] = None
            else:
                data_hierarchy_dict[tier] = child_list

        # List that will help to filter which elements in
        # data structure were appended
        tiers_gray_list = []

        # Creating the final data_structure_hierarchy
        for structure_element in data_structure_basic:
            tier = structure_element[0]
            for dict_elements in data_hierarchy_dict.items():
                key = dict_elements[0]
                elements = dict_elements[1]
                if key == tier:
                    if elements is None:
                        if not key in tiers_gray_list:
                            data_structure_hierarchy.append(key)
                    else:
                        auxiliar_list = []
                        for element in elements:
                            for dict_elts in data_hierarchy_dict.items():
                                if dict_elts[0] == element:
                                    if dict_elts[1] is not None:
                                        auxiliar_list.append([element,dict_elts[1]])
                                    else:
                                        auxiliar_list.append(element)
                                    tiers_gray_list.append(element)
                                    break

                        if not key in tiers_gray_list:
                            data_structure_hierarchy.append([key, auxiliar_list])

        return data_structure_hierarchy

    def _create_graf_files(self, graph, header, data_structure):
        """This method will create the GrAF Xml files.
        But first is need to create the GrAF object in
        order to get the values.
        This method will also create a metafile that will
        gathered all the data information to recreate the
        elan files and to access to the data structure
        hierarchy, the vocabulary, the media descriptor
        and all the important information.

        Parameters
        ----------
        graph : object
            GrAF object.
        header : object
            Header object.
        data_structure : array_like
            Array like with the data structure hierarchy.

        """

        for tree_element in self.xml_files_map.items():
            tier_name = tree_element[0]
            filepath = self.basedirname+"-"+tier_name+".xml"
            file = open(filepath,'wb')
            element_tree = tree_element[1]
            doc = minidom.parseString(tostring(element_tree))
            file.write(doc.toprettyxml(indent='  ', encoding='utf-8'))
            file.close()

        # Generate the metadata file
        metafile_tree = Element('metadata')

        SubElement(metafile_tree, 'header_file').text =\
        os.path.basename(header.filename)

        SubElement(metafile_tree, 'data_structure_hierarchy').text =\
        str(data_structure)

        file_tag = SubElement(metafile_tree, "file",
                {"data_type":header.dataType})

        if graph.additional_information is not None:
            miscellaneous = SubElement(file_tag, "miscellaneous")
            current_parent_element = None
            for element in graph.additional_information:
                tag = element[0]
                attributes = element[1]

                try:
                    depends = [depends for depends in element
                               if 'DEPENDS - ' in
                                  depends]
                except IndexError as indexError:
                    depends = None

                try:
                    tag_value = [tag_value for tag_value in element
                                 if 'VALUE - ' in
                                    tag_value]
                except IndexError as indexError:
                    tag_value = None

                attribute_map = {}

                for attribute in attributes:
                    attr = attribute.split(' - ')
                    name = attr[0]
                    val = attr[1]
                    attribute_map[name] = val

                if not depends:
                    current_parent_element = SubElement(miscellaneous,
                        tag, attribute_map)
                    if tag_value:
                        value = tag_value[0].split(' - ')[1]
                        current_parent_element.text = value
                else:
                    if tag_value:
                        value = tag_value[0].split(' - ')[1]
                        SubElement(current_parent_element, tag,
                            attribute_map).text = value
                    else:
                        SubElement(current_parent_element, tag,
                            attribute_map)

        filename = self.basedirname+"-metafile.xml"
        file = open(filename,'wb')
        doc = minidom.parseString(tostring(metafile_tree))
        file.write(doc.toprettyxml(indent='  ', encoding='utf-8'))
        file.close()

    def graph_rendering(self, outputfile, graph):
        """This method will convert a GrAF object to a
        Xml files respecting GrAF standards.
        To use the rendering is need to install the
        Graf-Python Library,

        Parameters
        ----------
        outputfile : str
            Path to the outputfile with the renderer GrAF.
        graph : object
            GrAF object.

        """

        graf_render = GrafRenderer(outputfile+"_tmp")
        graf_render.render(graph)

        # Indent the Xml file
        file = codecs.open(outputfile,'w','utf-8')
        xml = minidom.parse(outputfile+"_tmp")
        file.write(xml.toprettyxml(' '))
        file.close()

        # Delete the temp file
        os.remove(outputfile+"_tmp")

class GrafToElan:
    """
    Class that will transform the GrAF files
    in Elan file.

    """

    def __init__(self, header_file, data_structure_hierarchy):
        """Class's constructor.

        Parameters
        ----------
        header_file : str
            Path of the header file.
        data_structure_hierarchy : array_like
            Data structure with tiers hierarchy.

        """

        self.filepath = header_file
        (self.basedirname, _) = os.path.splitext(os.path.abspath(self.filepath))
        self.dirname = os.path.dirname(self.filepath)
        self.data_structure_hierarchy = data_structure_hierarchy