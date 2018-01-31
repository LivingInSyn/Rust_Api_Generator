'''holds the class that turns a lark tree into usable objects'''
from lark import Transformer
from lark.lexer import Token

class TreeToObj(Transformer):
    def start(self, items):
        return list(items)
    
    def usedecl(self, _):
        #a use decl is made up of 1+ names and a type at the end
        #but we're not using it, just return none right now
        return None

    def externcrate(self, _):
        return None

    def optionalas(self, _):
        return None

    def comment(self, item):
        #just return the comment with an appropriate label
        return ("comment", item[0].value)

    def impl(self, _):
        #we don't care about impl's, return None
        return None

    def pointer(self, item):
        #return {"pointer": is_mutable}
        if(item[0].data == 'mutable'):
            return ("pointer", True)
        else:
            return ("pointer", False)

    def array(self,item):
        '''return ('array', (type, number, is_pointer))'''
        #we need to check if item is a tuple[0] is a tuple first
        #if it's it's a pointer
        if not isinstance(item[0], tuple):
            return ("array", (item[0].value, item[1].value, False))
        else:
            return("array", (item[0][1], item[1].value, True))
    
    def modifiedtype(self, item):
        #should only be called on pointers, others get simplified to rtypes
        #returns the pointer object, decoded by 'pointer()' and the type
        return (item[0], item[1].value)

    def decl(self, item):
        #for each decl, we need to know if it's private, its name, and its type
        #return either an already processed tuple OR
        #('field', name, type)
        #make sure 0 is a tuple
        if isinstance(item[0], tuple):
            #if it's a public decl:
            if item[0][0] == "public" and item[0][1]:
                #if it's not a tuple, it's a `simple` type, return it
                if not isinstance(item[2], tuple):
                    return ('field', item[1].value, item[2].value)
                #otherwise, return the preprocessed tuple
                else:
                    return ('field', item[1].value, item[2])
            #otherwise it's already processed, just return it:
            else:
                return item[0]
        #if we hit a token, return none, it's not public
        elif isinstance(item[0], Token):
            return None
        print("\n")
        return item

    def ispub(self, _):
        return ("public", True)

    def reprc(self, _):
        return ("reprc", True)

    def struct(self, item):
        #if item[0] isn't a tuple it's not reprc or public, return none
        if not isinstance(item[0], tuple):
            return None
        elif len(item) > 2:
            #if it's not reprc, return none
            if item[0][0] != "reprc":
                return None
            #if it's reprc, but not public, return none
            if item[1][0] != "public":
                return None
            #now we know it's reprc and public, return ('struct', 'name', [])
            name = item[2].value
            fields = item[3:]
            return ('struct', name, fields)
        else:
            #something went wrong, return none
            return None