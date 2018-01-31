from lark import Lark

class TreeBuilder:
    '''builds a tree using a grammar'''
    def __init__(self):
        with open("rgrammar.g", 'r') as grammarfile:
            self.parser = Lark(grammarfile.read(), parser="lalr")
            #self.parser = Lark(grammarfile.read())

    def get_tree(self, filetext):
        return self.parser.parse(filetext)
