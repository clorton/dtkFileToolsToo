#!/usr/bin/python

from __future__ import print_function
import argparse
import dtkFileToolsToo as dtk
import serialization_tools as jgz

_endings = [ 'th', 'st', 'nd', 'rd', 'th', 'th', 'th', 'th', 'th', 'th' ]


def main(source_filename, dest_filename, ignore_nodes, keep_individuals):

    print('Ignoring nodes {0}'.format(ignore_nodes))
    print('Keeping infections in humans {0}'.format(keep_individuals))

    print("Reading file: '{0}'".format(source_filename))
    source = dtk.DtkFile(source_filename)

    for index in range(0, len(source.nodes)):
        print('Reading {0}{1} node'.format(index, _endings[index%10]), end='')
        obj = source.nodes[index]
        node = obj.node
        print(', externalId = {0}'.format(node.externalId))
        if node.externalId not in ignore_nodes:
            print('Zeroing vector infections')
            jgz.zero_vector_infections(node.m_vectorpopulations)
            print('Zeroing human infections')
            jgz.zero_human_infections(node.individualHumans, keep_individuals)
            print('Saving updated node')
            source.nodes[index] = obj
        else:
            print('Ignoring node {0}'.format(index))

    print("Writing file: '{0}'".format(dest_filename))
    source.write(dest_filename)

    return

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("destination")
    parser.add_argument("-i", "--ignore", default=[], type=int, nargs="*")
    parser.add_argument("-k", "--keep", default=[], type=int, nargs="*")

    args = parser.parse_args()

    main(args.source, args.destination, args.ignore, args.keep)
