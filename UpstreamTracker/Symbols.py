import os,sys,inspect
import git
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir) 
import Constants.constants as cst
from pycparser import c_parser, c_ast, parse_file

# A simple visitor for FuncDef nodes that prints the names and
# locations of function definitions.
class FuncDefVisitor(c_ast.NodeVisitor):
    def visit_FuncDef(self, node):
        print('%s at %s' % (node.decl.name, node.decl.coord))


def show_func_defs(filename):
    # Note that cpp is used. Provide a path to your own cpp or
    # make sure one exists in PATH.
    ast = parse_file(filename, use_cpp=True,
                     cpp_args=r'-Iutils/fake_libc_include')

    v = FuncDefVisitor()
    v.visit(ast)

def get_c_functions(filenames):
    for file in filenames:
        if file[-2:] == ".c":
            show_func_defs(cst.PathToLinux+"/"+file)
        print("-------------------End of file "+file+" ---------------------")