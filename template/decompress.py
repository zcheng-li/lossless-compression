#!/usr/bin/python

# Needed for struct.unpack

import struct

# Initialize our list of phrases

phrases = ( 'the', # position 0
        'and', # position 1
        'to', # position 2
        'was', # position 3
        'you',  # position 4
        'that', # position 5
        'of', # position 6
        'with', # position 7
        'have', # position 8
        'her', # position 9
        'had', # position 10
        'not', # position 11
        'in', # position 12
        'she', # position 13
        'a', # position 14
        'b', # position 15
        'c', # position 16
        'd', # position 17
        'e', # position 18
        'f', # position 19
        'g', # position 20
        'h', # position 21
        'i', # position 22
        'j', # position 23
        'k', # position 24
        'l', # position 25
        'm', # position 26
        'n', # position 27
        'o', # position 28
        'p', # position 29
        'q', # position 30
        'r', # position 31
        's', # position 32
        't', # position 33
        'u', # position 34
        'v', # position 35
        'w', # position 36
        'x', # position 37
        'y', # position 38
        'z', # position 39
       '\n', # position 40
        ' ', # position 41
        '!', # position 42
        '"', # position 43
        '&', # position 44
        '\'', # position 45
        '(', # position 46
        ')', # position 47
        ',', # position 48
        '-', # position 49
        '.', # position 50
        '0', # position 51
        '1', # position 52
        '2', # position 53
        '3', # position 54
        '4', # position 55
        '5', # position 56
        '6', # position 57
        '7', # position 58
        '8', # position 59
        '9', # position 60
        ':', # position 61
        ';', # position 62
        '?', # position 63
)

# Open the input and output files. 'rb' is needed on some platforms
# to indicate that 'compressed' is a binary file.

fin = open('compressed','rb')
fout = open('out.txt','w')

# Read in the entire compressed file

indata = fin.read();

while len(indata) > 0:

    # Python has an "unpack" function that will take a string and
    # interpret it as a given type. Here we ask it to interpret the
    # first 3 bytes of the remaining compressed file + a dummy byte
    # as an unsigned, little-endian, integer.

    fourphrases = struct.unpack("<I", indata[0:3] + b'\0')[0]

    # delete three bytes from the beginning of the file since we
    # have already extracted them.

    indata = indata[3:];

    # We have 4 phrases, each using 6 bits, encoded across the
    # unsigned integer fourphrases.

    for i in range(0,4):

        ind = (fourphrases >> 6*i) & 63
        fout.write(phrases[ind])

# 'compressed' does not include the final newline so we output it here

fout.write('\n');

# Close input and output files

fin.close()
fout.close()
