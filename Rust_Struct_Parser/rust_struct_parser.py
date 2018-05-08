'''transforms rust struct file into other languages'''
import argparse
import os
import pprint
import re
import logging
from TreeToObj import TreeToObj
from TreeBuilder import TreeBuilder

#build the lookup tables

class NoWriter:
    '''a hacky way to handle not writing to a file we don't want to'''
    def write(self, _):
        '''does nothing'''
        pass

    def close(self):
        '''does nothing'''
        pass

class StructConverter:
    '''converts structs from rust to cpp, c# and python'''
    CSTYPEMAP = {
        #1 bit
        'bool': 'byte',
        #8-bits
        # a c_char is a signed byte
        # also, see https://doc.servo.org/std/os/raw/type.c_char.html
        # for why it's a signed byte, not unsigned
        'c_char': 'sbyte',
        'i8': 'sbyte',
        'c_schar': 'sbyte',
        #but a c_char that's a pointer is a string
        'c_char_pntr': 'string',
        'u8': 'byte',
        'c_uchar': 'byte',
        #16 bits
        'u16': 'ushort',
        'c_ushort': 'ushort',
        'i16': 'short',
        'c_short': 'short',
        #32 bits
        #ints
        'c_void': 'IntPtr',
        'u32': 'uint',
        'c_uint': 'uint',
        'i32': 'int',
        'c_int': 'int',
        #floats
        'f32': 'float',
        'c_float': 'float',
        #64 bits
        #ints
        'i64': 'long',
        'c_long': 'long',
        'c_longlong': 'long',
        'u64': 'ulong',
        'c_ulong': 'ulong',
        'c_ulonglong': 'ulong',
        #floats
        'c_double': 'double',
        'f64': 'double',
        #NOTE! i128 and other 128 bit integer/float types are still on
        # rust nightly only, so we won't support them
    }

    CPPTYPEMAP = {
        'bool': 'bool',
        #8-bits
        # a c_char is a signed byte
        # also, see https://doc.servo.org/std/os/raw/type.c_char.html
        # for why it's a signed byte, not unsigned
        'c_char': 'signed char',
        'c_char_pntr': 'char*',
        'i8': 'signed char',
        'c_schar': 'signed char',
        'u8': 'unsigned char',
        'c_uchar': 'unsigned char',
        #16 bits
        'u16': 'unsigned short',
        'c_ushort': 'unsigned short',
        'i16': 'short',
        'c_short': 'short',
        #32 bits
        #ints
        'c_void': 'void*',
        'u32': 'unsigned int',
        'c_uint': 'unsigned int',
        'i32': 'int',
        'c_int': 'int',
        #floats
        'f32': 'float',
        'c_float': 'float',
        #64 bits
        #ints
        'i64': 'long long int',
        'c_long': 'long long int',
        'c_longlong': 'long long int',
        'u64': 'unsigned long long int',
        'c_ulong': 'unsigned long long int',
        'c_ulonglong': 'unsigned long long int',
        #floats
        'c_double': 'double',
        'f64': 'double',
        #NOTE! i128 and other 128 bit integer/float types are still on
        # rust nightly only, so we won't support them
    }

    PYTYPEMAP = {
        'bool': 'c_bool',
        #8-bits
        # a c_char is a signed byte
        # also, see https://doc.servo.org/std/os/raw/type.c_char.html
        # for why it's a signed byte, not unsigned
        'c_char': 'c_byte',
        'c_char_pntr': 'c_char_p',
        'i8': 'c_byte',
        'c_schar': 'c_byte',
        'u8': 'c_ubyte',
        'c_uchar': 'c_ubyte',
        #16 bits
        'u16': 'c_ushort',
        'c_ushort': 'c_ushort',
        'i16': 'c_short',
        'c_short': 'c_short',
        #32 bits
        #ints
        'c_void': 'c_void_p',
        'u32': 'c_uint',
        'c_uint': 'c_uint',
        'i32': 'c_int',
        'c_int': 'c_int',
        #floats
        'f32': 'c_float',
        'c_float': 'c_float',
        #64 bits
        #ints
        'i64': 'c_longlong',
        'c_long': 'c_longlong',
        'c_longlong': 'c_longlong',
        'u64': 'c_ulonglong',
        'c_ulong': 'c_ulonglong',
        'c_ulonglong': 'c_ulonglong',
        #floats
        'c_double': 'c_double',
        'f64': 'c_double',
        #NOTE! i128 and other 128 bit integer/float types are still on
        # rust nightly only, so we won't support them
    }

    CSHEADERS = ["using System;", "using System.Linq;",
                 "using System.Runtime.InteropServices;\n\n",
                 "namespace {}\n{{"]

    CPPHEADERS = ['#include <stdbool.h>', '#include <cstdint>\n',
                  '#ifndef {0}_H', '#define {0}_H\n']

    #there are no extra headers for python right now
    #we import ctypes at the end so that we only import what we need
    PYHEADERS = []

    def __init__(self, input_file, out_path, out_name):
        self.builder = TreeBuilder()
        self.xformer = TreeToObj()
        self.xformtree = None
        self.in_file = input_file
        self.out_path = out_path
        self.out_name = out_name
        self.multiline_regex = re.compile(r"/\*(?:(?!\*/).)*\*/", re.DOTALL) # pylint: disable=E1101
        #if the output path doesn't exist, create it
        if not os.path.exists(self.out_path):
            os.makedirs(self.out_path)

    def _comment_pre_processor(self):
        '''removes multiline comments from the input file'''
        with open(self.in_file) as infile:
            content = infile.read()
        with open('temp_infile.temp', 'w') as tempfile:
            tempfile.write(self.multiline_regex.sub('', content))

    @staticmethod
    def _start_file(outfile, towrite, namespace):
        '''writes headers to a file given a file to write to,
        lines to write, and a namespace'''
        for line in towrite:
            outfile.write(line.format(namespace) + "\n")

    def _write_py_headers(self, imports):
        '''write just the python headers that we used'''
        with open(os.path.join(self.out_path, '{}_temp.py'.format(self.out_name)), mode='r') as temp:
            with open(os.path.join(self.out_path, '{}.py'.format(self.out_name)), mode='w') as pyf:
                ctype_line = "from ctypes import "
                for ctype in imports:
                    ctype_line += "{}, ".format(ctype)
                ctype_line = ctype_line[0:-2] + "\n\n"
                pyf.write(ctype_line)
                for line in temp.readlines():
                    pyf.write(line)
        os.remove(os.path.join(self.out_path, '{}_temp.py'.format(self.out_name)))

    def _write_simple_types(self, filetypes, field, pyimports):
        '''write simple types into struct definition'''
        filetypes["cs"].write("\t\tpublic {} {};\n".format(self.get_cs_map(field[2]), field[1]))
        filetypes["cpp"].write("\t{} {};\n".format(self.get_cpp_map(field[2]), field[1]))
        filetypes["pyf"].write('        ("{}", {}),\n'.format(field[1], self.get_py_map(field[2], pyimports)))

    @staticmethod
    def _write_interstruct_comment(filetypes, field):
        '''write inter-comment structs into struct definition'''
        filetypes["cs"].write("\t\t" + field[1] + "\n")
        filetypes["cpp"].write("\t" + field[1] + "\n")
        filetypes["pyf"].write('        #{}\n'.format(field[1].replace("//", "")))

    def _write_pointers(self, filetypes, field, pyimports):
        #for c#, if it's a c_char pointer, add an extra line
        if field[2][1] == 'c_char':
            filetypes["cs"].write("\t\t[MarshalAs(UnmanagedType.LPStr)]\n")
        #otherwise, look it up and write it
        filetypes["cs"].write("\t\tpublic {} {};\n".format(self.get_cs_map(field[2][1], True), field[1]))
        
        #for python and c++, if it's a c_char, add _pntr to the end
        if field[2][1] == "c_char":
            charfield = field[2][1]+"_pntr"
        else:
            charfield = field[2][1]
        filetypes["cpp"].write("\t{} {};\n".format(self.get_cpp_map(charfield), field[1]))
        filetypes["pyf"].write('        ("{}", {}),\n'.format(field[1],
                                                              self.get_py_map(charfield, pyimports)))

    def _write_arrays(self, filetypes, field, pyimports):
        arrtype = field[2][1][0]
        arrlen = field[2][1][1]
        is_pntr = field[2][1][2]
        #cs
        cstype = self.get_cs_map(arrtype, is_pntr)
        if cstype != "string":
            filetypes["cs"].write("\t\t[MarshalAs(UnmanagedType.ByValArray, SizeConst = {})]\n"
                                  .format(arrlen))
        else:
            filetypes["cs"].write("\t\t[MarshalAs(UnmanagedType.LPArray, ArraySubType=UnmanagedType.LPStr, SizeConst={})]\n"
                                  .format(arrlen))
        filetypes["cs"].write("\t\tpublic {0}[] {1};\n"
                              .format(self.get_cs_map(arrtype, is_pntr),
                                      field[1]))
        #cpp
        filetypes["cpp"].write("\t{} {}[{}];\n"
                               .format(self.get_cpp_map(arrtype), field[1], arrlen))
        #python
        pytowrite = '        ("{}", {} * {}),\n'.format(field[1], self.get_py_map(arrtype, pyimports), arrlen)
        filetypes["pyf"].write(pytowrite)

    def _build_filetypes(self, filetypes):
        #cpp
        if "cpp" in filetypes:
            filetypes["cpp"] = open(os.path.join(self.out_path, '{}.h'.format(self.out_name)), mode='w')
        else:
            filetypes["cpp"] = NoWriter()
        #python
        if "pyf" in filetypes:
            filetypes["pyf"] = open(os.path.join(self.out_path,
                                                 '{}_temp.py'.format(self.out_name)), mode='w')
        else:
            filetypes["pyf"] = NoWriter()
        #c#
        if "cs" in filetypes:
            filetypes["cs"] = open(os.path.join(self.out_path, '{}.cs'.format(self.out_name)), mode='w')
        else:
            filetypes["cs"] = NoWriter()

    def convert(self, filetypes):
        '''runs the converter'''
        #run the pre-processor, removes multiline comments
        logging.debug("removing multiline comments")
        self._comment_pre_processor()
        logging.debug("multiline comments removed, tempfile written")
        #runs the struct conversion
        with open('temp_infile.temp') as infile:
            #build the tree and pretty print it
            tree = self.builder.get_tree(infile.read())
            logging.debug("======\nLark Tree:\n======")
            logging.debug(tree.pretty())
            xformtree = self.xformer.transform(tree)
            logging.debug('======\ntransformed tree:\n======\n')
            #if log level is debug...
            if logging.getLogger().isEnabledFor(logging.DEBUG):
                pprinter = pprint.PrettyPrinter()
                pprinter.pprint(self.xformer.transform(tree))
            #cpp
            self._build_filetypes(filetypes)
            #make the start of each file
            #cs first
            self._start_file(filetypes["cs"], StructConverter.CSHEADERS, self.out_name)
            #cpp
            self._start_file(filetypes["cpp"], StructConverter.CPPHEADERS, self.out_name)
            #python
            self._start_file(filetypes["pyf"], StructConverter.PYHEADERS, None)
            #for python, we don't want to import *, so we're going to start
            #a list of our imports, the only one we know we'll need right now
            #is Structure
            pyimports = ["Structure"]

            for item in xformtree:
                if isinstance(item, tuple):
                    #if it's a main level comment
                    if item[0] == 'comment':
                        filetypes["cs"].write("\t" + item[1] + "\n")
                        filetypes["cpp"].write(item[1] + "\n")
                        filetypes["pyf"].write(item[1].replace("//", "#") + "\n")
                    #if it's a struct
                    if item[0] == 'struct':
                        ###declare the structs'''
                        #cs
                        filetypes["cs"].write("\t[StructLayout(LayoutKind.Sequential)]\n")
                        filetypes["cs"].write("\tpublic struct {}\n\t{{\n".format(item[1]))
                        #cpp
                        filetypes["cpp"].write("typedef struct {}Tag {{\n".format(item[1]))
                        #python
                        filetypes["pyf"].write("class {}(Structure):\n".format(item[1]))
                        filetypes["pyf"].write("    _fields_ = [\n")
                        ###foreach item in the struct, write it
                        for field in item[2]:
                            #if it's a comment inside of a struct:
                            if field is not None and field[0] == 'comment':
                                self._write_interstruct_comment(filetypes, field)
                            #if it's anything but a comment...
                            elif field is not None:
                                #if it's a simple type, it won't be a tuple:
                                if not isinstance(field[2], tuple):
                                    self._write_simple_types(filetypes, field, pyimports)
                                #if it's a more complex type
                                else:
                                    #if it's a pointer:
                                    if field[2][0][0] == 'pointer':
                                        self._write_pointers(filetypes, field, pyimports)
                                    #if it's an array
                                    elif field[2][0] == 'array':
                                        self._write_arrays(filetypes, field, pyimports)
                        #close out the struct
                        filetypes["cs"].write("\t}\n\n")
                        filetypes["cpp"].write("}} {};\n\n".format(item[1]))
                        filetypes["pyf"].write("        ]\n\n")
            #close the cs and cpp file
            filetypes["cs"].write("}")
            filetypes["cpp"].write("#endif")
            #close the files
            for _, filetype in filetypes.items():
                filetype.close()
        #write python headers
        if not isinstance(filetypes["pyf"], NoWriter):
            self._write_py_headers(pyimports)
        #delete temp file
        os.remove('temp_infile.temp')
        print("\n======\nDone\n======!")

    @staticmethod
    def get_cs_map(key, ispointer=False):
        '''gets from c-sharp type map'''
        if key in StructConverter.CSTYPEMAP:
            #handle if it's a c_char pointer
            if ispointer and key == "c_char":
                key = key + "_pntr"
            return StructConverter.CSTYPEMAP[key]
        return key

    @staticmethod
    def get_cpp_map(key):
        '''gets from cpp type map'''
        if key in StructConverter.CPPTYPEMAP:
            return StructConverter.CPPTYPEMAP[key]
        return key

    @staticmethod
    def get_py_map(key, used_keys):
        '''gets from python type map'''
        if key in StructConverter.PYTYPEMAP:
            if StructConverter.PYTYPEMAP[key] not in used_keys:
                used_keys.append(StructConverter.PYTYPEMAP[key])
            return StructConverter.PYTYPEMAP[key]
        return key

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Translate Rust structs into other languages. ")# pylint: disable=C0103
    parser.add_argument("input_file", help="The Rust struct to translate")
    parser.add_argument("-o", "--output_path", help="The path to output to", default="output")
    parser.add_argument("-p", "--prefix", help="The namespace/filename prefix for the output files",
                        default="output")
    parser.add_argument("-l", "--languages",
                        help="""The language types to convert to as a comma separated list. Supports python, cpp, csharp""", # pylint: disable=C0301
                        default=["python", "cpp", "csharp"],
                        nargs="*")
    parser.add_argument("-v", "--verbose", help="turn verbosity on or off", action="store_true")
    #parse the args
    args = parser.parse_args() # pylint: disable=C0103
    #build struct converter
    SC = StructConverter(args.input_file, args.output_path, args.prefix)
    #build filetypes object
    FILES = {}
    for language in args.languages:
        if language == "python":
            FILES["pyf"] = None
        elif language == "cpp":
            FILES["cpp"] = None
        elif language == "csharp":
            FILES["cs"] = None
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    else:
        logging.basicConfig(level=logging.WARN, format='%(message)s')
    SC.convert(FILES)
