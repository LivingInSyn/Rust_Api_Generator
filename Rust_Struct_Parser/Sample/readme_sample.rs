extern crate libc;
use std::marker::Send;

unsafe impl Send for foo {}
#[repr(C)]
pub struct foo {
    //I'm a comment that stays
    pub an_i16: i16,
    pub a_c_char: *mut c_char,
    pub c_void: *mut c_void,
    /* I won't be here*/
    pub an_array: [i32;10],    
}

pub struct bar {
    pub baz: i16,
}