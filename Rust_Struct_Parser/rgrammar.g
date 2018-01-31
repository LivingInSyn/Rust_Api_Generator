//start with a value
?start: statement+

//a value is 1 or mroe statements
//?value: statement+

//a statement should be inlined if it only
//has one element, which is a struct, a use, or a 
//comment
?statement: struct
    | usedecl
    | comment
    | impl
    | externcrate

//a use is made up of one or more namespaces
//the keyword use and a semicolon
usedecl: "use" namespace+ ";"
?namespace: ["::"] rtype

//define extern crate statements
externcrate: "extern" "crate" name [optionalas] ";"
?optionalas: "as" name


//define what an impl statement looks like, 
//we're going to ignore these going forward
impl: ["unsafe"] "impl" name "for" name "{}"

//a struct may or may not have a reprc statement on it
//we are only going to parse those WITH a repr c_char
//it then has to be public
//and has a list of decls inside of braces
struct:  [reprc] [ispub] "struct" name "{" decl+ "}"

//decls need to be public for us to move them,
//so it's optional, it can omit a trailing comma
//for the last one
//also allow comments inside of structs
decl: [ispub] name ":" modifiedtype [","]
    | comment

?ispub: "pub"

//a modified type might be a pointer for ffi structs
?modifiedtype: [pointer] rtype

//types to translate
?rtype: name
    | array

//arrays are a type and an int
array: "[" modifiedtype ";" /[0-9]+/ "]"

//pointers are mut or const
pointer: "*" mutable
    | "*" const

mutable: "mut"
const: "const"

//names are alpha-start, alphanumeric/_ after
?name: /[a-z_A-Z][a-z_A-Z0-9]*/

//we're only handling single line comments right 
//now, might pre-process multilines out
comment: /\/\/[^\n]*/

//define what reprc looks like
reprc: "#[repr(C)]"

//for use by lark
%import common.ESCAPED_STRING
%import common.WS
%ignore WS