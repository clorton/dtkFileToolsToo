#!/usr/bin/python

from __future__ import print_function
import argparse
import json
import lz4
import os
import snappy
import time
import sys

_NONE = 'NONE'
_LZ4 = 'LZ4'
_SNAPPY = 'SNAPPY'


# noinspection PyCamelCase
class uncompressed(object):

    @classmethod
    def compress(cls, data):
        return data

    @classmethod
    def uncompress(cls, data):
        return data


__engines__ = {_LZ4: lz4, _SNAPPY: snappy, _NONE: uncompressed}


class _Class:
    def __init__(self, dictionary):
        self.__dict__ = dictionary
        return


class SerialObject(dict):
    # noinspection PyDefaultArgument
    def __init__(self, dictionary={}):
        super(SerialObject, self).__init__(dictionary)
        self.__dict__ = self

        return


class DtkHeader(SerialObject):
    # noinspection PyDefaultArgument
    def __init__(self, dictionary={}):
        super(DtkHeader, self).__init__(dictionary)

        return

    def __str__(self):
        return json.dumps(self, separators=(',', ':'))

    def __len__(self):
        return len(self.__str__())


class Chunks(object):
    def __init__(self, dtk_file):
        self._dtk_file = dtk_file
        return

    def __iter__(self):
        index = 0
        while index < len(self):
            yield self[index]
            index += 1

    def __getitem__(self, index):
        chunk = self._dtk_file._chunks[index]
        return chunk

    def __setitem__(self, index, value):
        self._dtk_file._set_chunk(index, value)
        return

    def __len__(self):
        return len(self._dtk_file._chunks)

    def append(self, value):
        self._dtk_file._chunks.append(value)


class Contents(object):
    def __init__(self, dtk_file):
        self._dtk_file = dtk_file
        return

    def __iter__(self):
        index = 0
        while index < len(self):
            yield self[index]
            index += 1

    def __getitem__(self, index):
        contents = self._dtk_file._get_contents(index)
        return contents

    def __setitem__(self, index, value):
        self._dtk_file._set_contents(index, value)
        return

    def __len__(self):
        return len(self._dtk_file._chunks)


class Objects(object):
    def __init__(self, dtk_file, offset=0):
        self._dtk_file = dtk_file
        self._offset = offset
        return

    def __iter__(self):
        index = 0
        while index < len(self):
            yield self[index]
            index += 1

    def __getitem__(self, index):
        item = self._dtk_file._get_object(index + self._offset)
        return item

    def __setitem__(self, index, value):
        self._dtk_file._set_object(index + self._offset, value)
        return

    def __len__(self):
        return len(self._dtk_file._chunks) - self._offset


class DtkFile:

    def __init__(self, filename=None):

        self.filename = filename
        self._chunks = []
        self.chunks = Chunks(self)
        self.contents = Contents(self)
        self.objects = Objects(self)
        self.nodes = Objects(self, 1)

        if filename is not None:
            with open(self.filename, 'rb') as handle:
                _check_magic(handle)
                header_size, self.header = _read_header(handle)

                scheme = self.header.metadata.engine.upper()
                if scheme not in __engines__:
                    raise UserWarning("File's compression engine ('{0}') is unknown.".format(self.header.metadata.engine))
                self.engine = __engines__[scheme]

                # 'IDTK' + len(size) + len(header)
                offset = 4 + 12 + header_size
                for size in self.header.metadata.chunksizes:
                    handle.seek(offset)
                    self.chunks.append(handle.read(size))
                    offset += size
        else:
            self.header = DtkHeader({'metadata': SerialObject({'engine':_LZ4})})
            self.header.metadata.version = 2
            self.header.metadata.author = os.environ['USERNAME'] if 'USERNAME' in os.environ else os.environ['USER']
            self.header.metadata.tool = os.path.basename(__file__)
            self.header.metadata.engine = _LZ4
            self.engine = __engines__[self.header.metadata.engine]

        return

    # Properties

    @property
    def version(self):
        return self.header.metadata.version

    @version.setter
    def version(self, version):
        self.header.metadata.version = version
        return

    @property
    def date(self):
        return self.header.metadata.date

    @property
    def author(self):
        return self.header.metadata.author

    @author.setter
    def author(self, author):
        self.header.metadata.author = author
        return

    @property
    def tool(self):
        return self.header.metadata.tool

    @tool.setter
    def tool(self, tool):
        self.header.metadata.tool = tool
        return

    @property
    def compressed(self):
        return self.header.metadata.engine.upper() != 'NONE'

    @property
    def compression_scheme(self):
        return self.header.metadata.engine

    @compression_scheme.setter
    def compression_scheme(self, value):
        self.header.metadata.engine = value.upper()
        self.engine = __engines__[self.header.metadata.engine]
        return

    # Helper functions

    def _set_chunk(self, index, data):

        while len(self._chunks) <= index:
            self._chunks.append('')

        self._chunks[index] = data

        return

    def _get_contents(self, index):
        """ Returns the uncompressed contents of a file chunk """

        contents = self._chunks[index]
        try:
            contents = self.engine.decompress(contents)
        except ValueError as err:
            raise UserWarning("Couldn't decompress chunk - '{0}'".format(err))

        return contents

    def _set_contents(self, index, contents):

        data = self.engine.compress(contents)
        self._set_chunk(index, data)

        return

    def _get_object(self, index):
        """ Returns the data in a chunk as a Python object """

        contents = self._get_contents(index)
        obj = json.loads(contents, object_hook=SerialObject)

        return obj

    def _set_object(self, index, obj):

        text = json.dumps(obj, separators=(',', ':'))
        self._set_contents(index, text)

    @property
    def simulation(self):
        simulation = self._get_object(0)
        return simulation

    @simulation.setter
    def simulation(self, value):

        text = json.dumps(value, separators=(',', ':'))
        # TODO - what if len(text) > length engine can handle?
        data = self.engine.compress(text)
        self._set_chunk(0, data)

        return

    def write(self, filename):

        self._sync_header()

        with open(filename, 'wb') as handle:
            _write_magic_number(handle)
            _write_header_size(len(str(self.header)), handle)
            _write_header(str(self.header), handle)
            _write_chunks(self._chunks, handle)

        return

    def _sync_header(self):

        metadata = self.header.metadata
        metadata.date = time.strftime('%a %b %d %H:%M:%S %Y')
        metadata.bytecount = reduce(lambda acc, chunk: acc + len(chunk), self.chunks, 0)
        metadata.chunkcount = len(self.chunks)
        metadata.chunksizes = [len(chunk) for chunk in self.chunks]

        return

# Read helper functions

def _check_magic(handle):

    magic = handle.read(4)
    if magic != 'IDTK':
        raise UserWarning("File has incorrect magic 'number': '{0}'".format(magic))

    return


def _read_header(handle):

    size_string = handle.read(12)
    header_size = int(size_string)
    _check_header_size(header_size)
    header_text = handle.read(header_size)
    header = _try_parse_header_text(header_text)

    metadata = header.metadata

    if 'version' not in metadata:
        metadata.version = 1
    if metadata.version < 2:
        metadata.engine = 'SNAPPY' if metadata.compressed else 'NONE'
        metadata.chunkcount = 1
        metadata.chunksizes = [metadata.bytecount]
    _check_version(metadata.version)

    _check_chunk_sizes(metadata.chunksizes)

    # return header_text, header
    return header_size, header


def _check_header_size(header_size):

    if header_size <= 0:
        raise UserWarning("Invalid header size: {0}".format(header_size))

    return


def _try_parse_header_text(header_text):

    try:
        header = json.loads(header_text, object_hook=DtkHeader)
    except ValueError as err:
        raise UserWarning("Couldn't decode JSON header '{0}'".format(err))

    return header


def _check_version(version):

    if version <= 0 or version > 2:
        raise UserWarning("Unknown version: {0}".format(version))

    return


def _check_chunk_sizes(chunk_sizes):

    for size in chunk_sizes:
        if size <= 0:
            raise UserWarning("Invalid chunk size: {0}".format(size))

    return


def __do_read__(commandline_arguments):

    if commandline_arguments.output is not None:
        prefix = commandline_arguments.output
    else:
        root, _ = os.path.splitext(commandline_arguments.filename)
        prefix = root

    if commandline_arguments.raw:
        extension = 'bin'
    else:
        extension = 'json'

    dtk_file = DtkFile(commandline_arguments.filename)

    if commandline_arguments.header:
        with open(commandline_arguments.header, 'wb') as handle:
            json.dump(dtk_file.header, handle, indent=2, separators=(',', ':'))

    print('File metadata: {0}'.format(dtk_file.header.metadata))

    for index in range(len(dtk_file.chunks)):
        if commandline_arguments.raw:
            # Write raw chunks to disk
            output = dtk_file.chunks[index]
        else:
            if commandline_arguments.unformatted:
                # Expand compressed contents, but don't serialize and format
                output = dtk_file.contents[index]
            else:
                # Expand compressed contents, serialize, write out formatted
                obj = dtk_file.objects[index]
                output = json.dumps(obj, indent=2, separators=(',', ':'))

        if index == 0:
            output_filename = '.'.join([prefix, 'simulation', extension])
        else:
            output_filename = '.'.join([prefix, 'node-{:0>5}'.format(index), extension])

        with open(output_filename, 'wb') as handle:
            handle.write(output)

    return


def __do_write__(args):

    print("Writing file '{0}'".format(args.filename), file=sys.stderr)
    print("Reading simulation data from '{0}'".format(args.simulation), file=sys.stderr)
    print("Reading node data from {0}".format(args.nodes), file=sys.stderr)
    print("Author = {0}".format(args.author), file=sys.stderr)
    print("Tool = {0}".format(args.tool), file=sys.stderr)
    print("{0} contents".format("Compressing" if args.compress else "Not compressing"), file=sys.stderr)
    print("{0} contents".format("Verifying" if args.verify else "Not verifying"), file=sys.stderr)
    print("Using compression engine '{0}'".format(args.engine), file=sys.stderr)

    dtk_file = DtkFile()
    dtk_file.author = args.author
    dtk_file.tool = args.tool
    dtk_file.compression_scheme = args.engine

    _prepare_simulation_data(args.simulation, dtk_file)
    _prepare_node_data(args.nodes, dtk_file)

    dtk_file.write(args.filename)

    return


def _prepare_simulation_data(filename, dtk_file):

    with open(filename, 'rb') as handle:
        data = handle.read()
        # Do not use dtk_file.simulation property because this is text rather than a Python object
        dtk_file.contents[0] = data

    return


def _prepare_node_data(filenames, dtk_file):

    index = 1
    for filename in filenames:
        with open(filename, 'rb') as handle:
            data = handle.read()
            # Do not use dtk_file.nodes here because this is text rather than a Python object
            dtk_file.contents[index] = data
            index += 1

    return


# Write helper functions

def _write_magic_number(handle):

    handle.write('IDTK')

    return


def _write_header_size(size, handle):

    size_string = '{:>12}'.format(size)     # decimal value right aligned in 12 character space
    handle.write(size_string)

    return


def _write_header(string, handle):

    handle.write(string)

    return


def _write_chunks(chunks, handle):

    for chunk in chunks:
        handle.write(chunk)

    return


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help='add_subparsers help')

    read_parser = subparsers.add_parser('read', help='read help')
    read_parser.add_argument('filename')
    read_parser.add_argument('--header', default=None, help='Write header to file', metavar='<filename>')
    read_parser.add_argument('-r', '--raw', default=False, action='store_true', help='Write raw contents of chunks to disk')
    read_parser.add_argument('-u', '--unformatted', default=False, action='store_true', help='Write unformatted (compact) JSON to disk')
    read_parser.add_argument('-o', '--output', default=None, help='Output filename prefix, defaults to input filename with .json extension')
    read_parser.set_defaults(func=__do_read__)

    username = os.environ['USERNAME'] if 'USERNAME' in os.environ else os.environ['USER']
    tool_name = os.path.basename(__file__)

    write_parser = subparsers.add_parser('write', help='write help')
    write_parser.add_argument('filename', help='Output .dtk filename')
    write_parser.add_argument('simulation', help='Filename for simulation JSON')
    write_parser.add_argument('nodes', nargs='+', help='Filename(s) for node JSON')
    write_parser.add_argument('-a', '--author', default=username, help='Author name for metadata [{0}]'.format(username))
    write_parser.add_argument('-t', '--tool', default=tool_name, help='Tool name for metadata [{0}]'.format(tool_name))
    write_parser.add_argument('-u', '--uncompressed', default=True, action='store_false', dest='compress', help='Do not compress contents of new .dtk file')
    write_parser.add_argument('-v', '--verify', default=False, action='store_true', help='Verify JSON in simulation and nodes.')
    write_parser.add_argument('-e', '--engine', default='LZ4', help='Compression engine {NONE|LZ4|SNAPPY} [LZ4]')
    write_parser.set_defaults(func=__do_write__)

    commandline_args = parser.parse_args()
    commandline_args.func(commandline_args)
