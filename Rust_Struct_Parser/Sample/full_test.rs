extern crate libc;
extern crate lib2 as bob;

use libc::c_void;
use std::os::raw::c_char;
use std::marker::Send;

unsafe impl Send for foo {}
#[repr(C)]
pub struct foo {
    //I'm a comment that stays
    pub an_i16: i16,
    pub a_c_char: *mut c_char,
    pub c_void: *mut c_void,
}

#[repr(C)]
pub struct bar {
    pub unsigned_32bit: u32,
    pub arraytest: [u8;10],
    pub pntr_array: [*mut c_char;4],
}

//I also stay, but all the comments below do not
#[repr(C)]
pub struct foobar {
    pub bob: /* I'm a comment! */ foo,
    /*
    here's a comment
    */
    pub tom: bar, /*
    start a multiline comment
    */ pub something: bool,
}