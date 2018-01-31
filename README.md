# Rust_Api_Generator
a toolset for autogenerating rust APIs and translating structs. This tool utilizes an excellent parser written by Erez Shinan called Lark (https://github.com/erezsh/lark) to build abstract syntax trees utilizing context free grammars.

## Rust Struct Parser
This tool takes in a file containing rust struct definitions and outputs struct definitions in other programming languages. Currently supported languages are:

* Python
* C#
* C++

Currently the tool moves single line comments (//...) and removes all multi-line comments (/* ... */)

### Example:
Imagine you have a rust file with the following contents:
```rust
extern crate libc;
use std::marker::Send;

unsafe impl Send for foo {}
#[repr(C)]
pub struct foo {
    //I'm a comment that stays
    pub an_i16: i16,
    pub a_c_char: *mut c_char,
    pub c_void: *mut c_void,
}

pub struct bar {
    pub baz: i16,
}
```

Next run the tool:

```
python .\rust_struct_parser.py .\Sample\readme_sample.rs -o .\test_output\
```

In the 'test_output' directory you would have the following files:

Note that you will not see 'bar' translated because it doesn't have a ```#[repr(C)]``` on it, and won't work correctly in an API

#### C#

```c#
using System;
using System.Linq;
using System.Runtime.InteropServices;


namespace output
{
	[StructLayout(LayoutKind.Sequential)]
	public struct foo
	{
		//I'm a comment that stays
		public short an_i16;
		[MarshalAs(UnmanagedType.LPStr)]
		public string a_c_char;
		public IntPtr c_void;
	}

}
```

#### C++
```C++
#include <stdbool.h>
#include <cstdint>

#ifndef output_H
#define output_H

typedef struct fooTag {
	//I'm a comment that stays
	short an_i16;
	signed char a_c_char;
	void* c_void;
} foo;
```

#### Python
```python
from ctypes import Structure, c_short, c_byte, c_void_p

class foo(Structure):
    _fields_ = [
        #I'm a comment that stays
        ("an_i16", c_short),
        ("a_c_char", c_byte),
        ("c_void", c_void_p),
        ]

```

