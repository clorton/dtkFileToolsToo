# dtkFileToolsToo
Python scripts for V2 serialized population file format

New file format:

1. 'IDTK' "magic number"
2. '0' padded, 12 character header size
3. Plain text header in JSON format
4. Simulation serialized to JSON and, optionally, compressed
5. 1+ nodes serialized to JSON and, optionally, compressed

Additional metadata in header:

* version (now == 2)
* engine = { "NONE" | "LZ4" | "SNAPPY" } snappy was the only engine in V1 thus compressed == snappy
* chunkcount - number of chunks of, optionally compressed, data = 1 (simulation) + # of nodes
* chunksizes - array with chunkcount # of entries with the size, in bytes, of chunk N
* [optional] author - string
* [optional] tool - string
