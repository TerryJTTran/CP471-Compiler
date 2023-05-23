#Author: Terry Tran
#Date: 29/01/23
#Compiler Phase 1, 2, 3
#Description: Program designed to read a text file, tokenize the words,
#  and identify which words are keywords and etc...
#pip install xlrd

#Imports
import sys
import pandas
import openpyxl
import io
import re
from collections import defaultdict

#Global File Variables
statusFileName = True
errorFileName = "error.cp"
tokenFileName = "token.cp"
keywordsFileName = "keywords.txt"
irFileName = "intermediate_code.txt"
FILE_EXTENTION = "cp"
lineCount = 0
fileName = ""
EOFState = False

#Open errors and token files
errorFile = open(errorFileName, "w", encoding="utf-8")
tokenFile = open(tokenFileName, "w", encoding="utf-8")

#Global Arrays
OPERATORS = {"+" : "ADD", "-" : "SUB", "*" : "MLT", "/" : "DIV", "%" : "MOD", "," : "COM", "." : "PER", ";" : "END"}
DELIMITERS = {"(" : "STR_BKT", ")" : "END_BKT", " " : "SPC"}

#Double Buffer Variables
BUFFERSIZE = 4
lexemeBegin = 0
forward = 0

#Lexical Analysis Variables
currentToken = ""
currentState = 0
nextState = 0
currentLine = 1
dataType = ""

#Load Keywords
KEYWORDS = open("keywords.txt", "r", encoding="utf-8").read().split(",")

#Symbol Table
symbolTableData = []
UpdatedTableData = []

#Load Transition Table
transitionTable = pandas.read_excel("Transition-Table-2.0.xlsx").values.tolist()

#Phase 2 - Variables
followSetDict = defaultdict(set)
firstSetDict = defaultdict(set)
LLOneDict = defaultdict(dict)
terminals = set()
nonterminals = set()
startSymbol = "<program>"

#Load Grammar Productions
GRAMMAR = open("grammar.txt", "r", encoding="utf-8").read().split("\n")
FIRSTANDFOLLOW = pandas.read_excel("First_and_Follow_Set_3.0.xlsx").values.tolist()
LEXEMES = []
SEMANTIC = []

# Phase 4 - IR File
INTERMEDIATEFILE = open(irFileName, "w", encoding="utf-8")
TO3TAC = []

#Confirm File Extension
def checkFileExt(fileName):
    
    #Split inputted file by '.' character to check last token for file type
    fileExtention = fileName.split(".")
    
    #Check if file type is '.cp' type, if not loop until valid type is entered
    while(len(fileExtention) > 0 and fileExtention[len(fileExtention) - 1] != FILE_EXTENTION):
        print("Invalid File.\nEnter filename (with '.cp' file extention included): ")
        fileName = input()
        fileExtention = fileName.split(".")
    return fileName

#Set datatype
def setDataType(state, symbols):
    global dataType, currentToken

    #If token is a integer
    if(state == 14):
        dataType = "INT"

    #If token is a float
    elif(state == 15):
        dataType = "FLT"

    #If token is a delimiter
    elif(state == 8):
        dataType = DELIMITERS[currentToken]

    #If token is a operator
    elif(state == 12):
        dataType = OPERATORS[currentToken]

    #If token is ,
    elif(state == 21):
        dataType = "COM"

    #If token is ;
    elif(state == 22):
        dataType = "SEMI"

    #If token keyword or variable
    elif(state == 13):
        
        #print(currentToken + " - " + str(currentToken in KEYWORDS))
        if(currentToken in KEYWORDS):
            dataType = "KEYWORD"
        else:
            dataType = "ID"
    
    #If token is <
    elif(state == 1):
        dataType = "LT"
        
    #If token is <=
    elif(state == 3):
        dataType = "LE"
        
    #If token is =
    elif(state == 4):
        dataType = "EQ"
        
    #If token is ==
    elif(state == 5):
        dataType = "EV"
        
    #If token is >
    elif(state == 6):
        dataType = "GT"
        
    #If token is >=
    elif(state == 7):
        dataType = "GE"

    return

#Create symbol table
def addToSymbolTable(token, dataType, value):
    global symbolTableData, LEXEMES
    if (dataType != "SPC" and token != ""):
        newEntry = [token, dataType, value]
        symbolTableData.append(newEntry)
        LEXEMES.append(token)
        SEMANTIC.append([token, dataType, value])
    return

# Create and add to updated symbol table
def addToUpdatedTable(node):
    global UpdatedTableData
    
    nodeArray = [node.line, node.lexeme, node.token, node.semantic, node.scope, node.type, node.param_types]

    UpdatedTableData.append(nodeArray)

# Export updated table to excel file
def exportUpdatedTable(filename, sheetname, data):
    workbook = pandas.DataFrame(data, columns=["Line", "Lexeme", "Token", "Semantic", "Scope", "Type", "Param_Types"])
    workbook.to_excel(filename + ".xlsx", sheetname, index=False)

#Export excel file
def exportExcel(filename, sheetname, data):
    workbook = pandas.DataFrame(data, columns=['Lexeme', 'Token Type', 'Line Number']) 
    workbook.to_excel(filename + ".xlsx", sheetname, index=False)
    return

#Lexical analysis function 
def getNextToken(token, state):
    transitionState = 0
    columnNumber = 0

    #Search for input symbol column
    for symbols in transitionTable[0]:
        
        #If symbol column found
        if (columnNumber > 0 and token in str(symbols)):
            
            #Set next transition using column number and current state
            transitionState = transitionTable[int(state)+1][columnNumber]
        
        #Else add to counter and continue to loop
        else:
           columnNumber += 1        

    if columnNumber == len(transitionTable[0]):
        transitionState = transitionTable[int(state)+1][columnNumber-1]

    return transitionState

#Create first, follow, and ll(1)table
def SetsAndTable():
    global firstSetDict, followSetDict, terminals, nonterminals, GRAMMAR
    
    # Gather all nonterminals
    for rule in GRAMMAR:
        lhs, rhs = rule.split(' ::= ')
        nonterminals.add(lhs)

    # Gather all terminals
    for rule in GRAMMAR:
        lhs, rhs = rule.split(' ::= ')
        rhs_symbols = rhs.split()
        for symbol in rhs_symbols:
            if symbol not in nonterminals:
                terminals.add(symbol)
    
    #FirstSet()
    #FollowSet()
    # Read file for first and follow
    for rule in FIRSTANDFOLLOW:
        
        first_symbols = rule[1].split(" | ")
        follow_symbols = rule[2].split(" | ")
        firstSetDict[rule[0]] = first_symbols
        followSetDict[rule[0]] = follow_symbols
    LookAHeadOne()
    return

#Create First Set Dictonary
def FirstSet():
    global terminals, nonterminals, firstSetDict, GRAMMAR
    #Search through all grammar rules
    for rule in GRAMMAR:
        #Split to left side and right side (Variable - Product)
        lhs, rhs = rule.split(' ::= ')
        nonterminals.add(lhs)
        rhs_symbols = rhs.split()
        
        #Search through products
        for symbol in rhs_symbols:
            
            #If symbol is terminal(no <>) or empty
            if symbol == '𝛜':
                #terminals.add(symbol)
                firstSetDict[symbol].add(symbol)
                break
            
            #Else search through variable for terminal
            else:
                first_s = firstSetDict[symbol]
                
                #If epsilon not in production
                if '𝛜' not in first_s:
                    firstSetDict[symbol].update(first_s)
                    break
                

                else:
                    first_s.remove('𝛜')
                    firstSetDict[symbol].update(first_s)
        
        #Else add epsilon
        else:
            firstSetDict[lhs].add('𝛜')

    return

#Create Follow Set Dictonary
def FollowSet():
    global GRAMMAR, followSetDict, terminals, nonterminals, startSymbol
    #Grab first not terminal
    startSymbol = GRAMMAR[0].split(' ::= ')[0]
    followSetDict[startSymbol].add('$')
    
    #Search through rest of productions
    for rule in GRAMMAR:
        #Split to left side and right side (Variable - Product)
        lhs, rhs = rule.split(' ::= ')
        rhs_symbols = rhs.split()
        
        #Search through productions
        for index, symbol in enumerate(rhs_symbols):
            
            #Check if non terminal
            if symbol not in nonterminals:
                
                #If index within number of productions update
                if index == len(rhs_symbols) - 1:
                    followSetDict[symbol].update(followSetDict[lhs])
                
                #Else Check if for next terminal
                else:
                    first_s = firstSetDict[rhs_symbols[index + 1]]
                    
                    if '𝛜' not in first_s:
                        followSetDict[symbol].update(first_s)
                    
                    else:
                        followSetDict[symbol].update(first_s - {'𝛜'})
                        followSetDict[symbol].update(followSetDict[lhs])

    return

#LL(1) Table
def LookAHeadOne():
    global GRAMMAR, terminals, LLOneDict, firstSetDict, followSetDict
    #Search through rules
    for rule in GRAMMAR:
        lhs, rhs = rule.split(' ::= ')
        rhs_symbols = rhs.split()
        first_rhs = set()
        
        #Search through production terms
        for symbol in rhs_symbols:
            
            #If term is a terminal add to first set
            if symbol in terminals:
                first_rhs.add(symbol)
                break
            
            #Else add first set for the nonterminal
            else:
                first_s = firstSetDict[symbol]
                
                #If empty rule not present set equal to first
                if '𝛜' not in first_s:
                    first_rhs.update(first_s)
                    break
                
                #Else set equal to first with empty removed
                else:
                    first_rhs.update(first_s - {'𝛜'})
        
        #Else set first equal to follow set of nonterminal
        else:
            first_rhs.update(followSetDict[lhs])

        #Add nonterminal and correct rules
        for term in first_rhs:
            LLOneDict[lhs][term] = rule

        #If empty in first of product look to follow set to add 
        if '𝛜' in first_rhs:
            
            for term in followSetDict[lhs]:
                LLOneDict[lhs][term] = rule
    return

#Syntactical Analysis
def Parse(inputText):
    global LLOneDict, startSymbol, errorFile

    #Start stack with start symbol and end symbol
    stack = ['$', startSymbol]
    input_index = 0
    inputText.append('$')
    #input_Tokens = inputText.split(" ")
    input_Tokens = inputText
    variable_index = 0

    # Run until stack is empty (input is completely parsed or error)    
    while stack:
        top = stack[-1]
        
        # 1. Pop the top symbol from the stack.
        # Production found pop from stack and move on
        if top != '$' and input_index == len(input_Tokens):
            return False
        
        #print("\n\nTop: " + top + "\tInput: " + input_Tokens[input_index] + "\tStack" + str(stack))
        stack.pop()
        

        productionFull = LLOneDict[top].get(input_Tokens[input_index], None)
        productionHasEmpty = LLOneDict[top].get('𝛜', None)
        

        # If empty character move to next in stack
        if top == '𝛜':
            continue
       
        # 2. If the symbol is a terminal and matches the current input symbol, consume the input symbol and move to the next symbol.
        elif top in terminals and top == input_Tokens[input_index]:
            input_index += 1

        # If terminal is letter
        elif top in terminals and top == input_Tokens[input_index][variable_index]:
            variable_index += 1

        # If the symbol is a terminal but does not match current input symbol in table throw error, "Expected {}"
        elif top in terminals and top != input_Tokens[input_index]:
            errorFile.write("\nSyntax error: unexpected token \'" + str(input_Tokens[input_index]) + "\', expected token \'" + str(top) + "\'")
            #raise ValueError("Syntax error: unexpected token \'" + str(input_Tokens[input_index]) + "\', expected token \'" + str(top) + "\'")
            #Panic Mode, push top back on top and check if next input is valid
            stack.append(top)
            input_index += 1
        
        # 3. If the symbol is a non-terminal, look up the corresponding entry in the parsing table based on the current input symbol.
        elif top in nonterminals:
            
            # If the parsing table entry is empty, then the input string is not valid according to the grammar or a variable name or a number. 
            if productionFull is None:
                #What if string variable search input by character
                    # check first character
                    if top == "<factor>" or top == "<symbol>" or top == "<var>" or top == "<id>" or top == "<term>" or  top == "<expr>" or top == "<exprseq>" or top == "<*exprseq>" or top == "<number>" or top == "<double>" or top == "<integer>":                         
                        productionFull = LLOneDict[top].get(input_Tokens[input_index][variable_index], None)
                        productionStart, productionEnd = productionFull.split(" ::= ")
                        productionEnd = productionEnd.split(" ")
                        stack.extend(reversed(productionEnd))

                    # Check next characters
                    elif top == "<*integer>" or top == "<*id>":
                        # Exceeded variable characters select empty
                        if (len(input_Tokens[input_index]) <= variable_index):
                            input_index += 1
                            variable_index = 0
                            continue
                        
                        # Else more characters in variable
                        else:
                            productionFull = LLOneDict[top].get(input_Tokens[input_index][variable_index], None)
                            productionStart, productionEnd = productionFull.split(" ::= ")
                            productionEnd = productionEnd.split(" ")
                            stack.extend(reversed(productionEnd))
                            
                        
                    # Iterate variable to ensure valid name
                    elif top == "<letter>" or top == "<digit>":
                        productionFull = LLOneDict[top].get(input_Tokens[input_index][variable_index], None)
                        productionStart, productionEnd = productionFull.split(" ::= ")
                        productionEnd = productionEnd.split(" ")
                        #print("\n\n" + str(productionEnd))
                        stack.extend(reversed(productionEnd))
            
                    
                    # If symbol does not exist in first and top has empty move to next in stack
                    elif productionHasEmpty is not None:
                        variable_index = 0
                        continue

                    # Not valid token at stage
                    else:
                        #Add to error file
                        errorFile.write("\nSyntax error: unexpected token \'" + str(input_Tokens[input_index]) + "\', expected token in \'" + str(top) + "\' first set")
                        #raise ValueError("Syntax error: unexpected token \'" + str(input_Tokens[input_index]) + "\', expected token \'" + str(top) + "\'")
                        #Panic Mode, push top back on top and check if next input is valid
                        stack.append(top)
                        input_index += 1

                
            # Parsing table entry found, push approriate production in reverse order
            else:
                variable_index = 0
                productionStart, productionEnd = productionFull.split(" ::= ")
                productionEnd = productionEnd.split(" ")

                # If the entry contains a production rule, push rule onto the stack in reverse order and loop all again without consuming terminal.
                if productionEnd != '𝛜':
                    stack.extend(reversed(productionEnd))
                
            
            # Else production is empty which means nothing needs to be pushed or popped

        # 4. If the stack is empty and the input string has been fully consumed, then the input string is valid according to the grammar.
        elif top == '$' and input_index == len(input_Tokens):
            return True
        

        # Else invalid token encountered
        #else:
        #    raise ValueError("Syntax error: unexpected token '{}'".format(input_Tokens[input_index]))

# Class to hold symbol attributes for table
class Symbol:
    def __init__(self, line, lexeme, token, semantic, scope=None, type=None, param_types=None):
        self.line = line
        self.lexeme = lexeme
        self.token = token
        self.semantic = semantic
        self.scope = scope
        self.type = type
        self.param_types = param_types
    
    def print(self):
        print(f'Line:{self.line}\nLexeme:{self.lexeme}\nToken:{self.token}\nSemantic:{self.semantic}\nScope:{self.scope}\nType:{self.type}\nParam Types:{self.param_types}\n\n')

# Class for table to hold symbols 
class SymbolTable:
    def __init__(self):
        self.table = []
        self.prevScope = None
        self.nextScope = None

    # Add symbol to table/scope
    def insert(self, symbol):
        self.table.append(symbol)

    # Look in table to see if lexeme was declared earlier and return either the symbol or none
    def lookup(self, node):
        currScope = self

        # While current scope is not none search for lexeme in scope
        while currScope is not None:
            for symbol in currScope.table:
                # If same token and lexeme
                if symbol.token == node.token and symbol.lexeme == node.lexeme:
                    return symbol
            
            # Current scope does not have lexeme search prev higher scope
            currScope = currScope.prevScope
        return None

    # Create and add new scope to table and return the new scope
    def enter_scope(self):
        new_scope = SymbolTable()
        new_scope.prevScope = self
        self.nextScope = new_scope
        return new_scope

    # Remove current scope from table and return old scope
    def exit_scope(self):
        old_scope = self.prevScope
        if (old_scope is not None):
            old_scope.nextScope = None
        self.prevScope = None
        return old_scope

#Semantic Analysis
def AnalyseSemantics():
    global SEMANTIC, errorFile, TO3TAC

    # Scope
    # Limited to blocks (if, else, while, def)

    # Type
    # Limited to int and double

    # Make table for global scope:
        # Include any literals, variables, or functions in global scope

    # Make table for block keywords:
        # Include any literals or variables in block scope

    """
    Send line by line as you finish syntax analysis to semeantic analyizer

    Destroy symbol table after function is used because variables wont be used outside block

    For While loops make new table 

    Link would be a pointer

    Lexeme is the type of token (Ex. Keyword) 

    Token is the actual value (Ex. While)

    Type (Ex. Int, double, variable, function name)

    Scope (for keywords make new symbol table and name them with number)

    """


    symbol_table = SymbolTable()
    ast = []
    count = 0
    scopeNum = None

    # Symbol Table Helper functions

    # Make new symbol table and scopeID
    def process_block(node, table, scopeNum):

        # If token is else (special case because it ends if scope and starts new scope)
        if node.token == "else":
            table = table.exit_scope()

        # Increase scope
        scopeNum += 1

        # Assign scope id to node
        node.scope = scopeNum

        # Add token to current scope table
        table.table.append(node)

        # Add symbol to table data
        addToUpdatedTable(node)


        # Create a new scope in the symbol table
        table = table.enter_scope()
        
        
        return table, scopeNum

    # Delete current symbol table and retrieve parent/new current scopeID
    def process_end(node, table, scopeNum):
        
        if table.table:

            # Assign scope id to node using previous token scope id
            node.scope = table.table[-1].scope

        # Check parent scope for scope id
        else:
            node.scope = scopeNum

        # Add token to current scope table
        table.table.append(node)

        # Add symbol to table data
        addToUpdatedTable(node)

        # Exit current scope and re-enter parent scope in symbol table
        table = table.exit_scope()
        return table

    # Check if previous and next token are of same type
    def process_typematch(node, table, index, symbolList, scopeNum):
        
        if table.table:

            # Assign scope id to node using previous token scope id
            node.scope = table.table[-1].scope

        # Check parent scope for scope id
        else:
            node.scope = scopeNum

        # Add token to current scope table
        table.table.append(node)

        # Add symbol to table data
        addToUpdatedTable(node)

        # Check if previous token is same type as next token
        prev = index-1
        after = index+1
        
        # Look for valid previous comparer
        while prev > 0 and (symbolList[prev].semantic != "NUM" or symbolList[prev].semantic != "VAR" or symbolList[prev].semantic != "FUN"):
            prev -= 1

        # Look for valid next comparer
        while after < len(symbolList) and (symbolList[after].semantic != "NUM" or symbolList[after].semantic != "VAR" or symbolList[after].semantic != "FUN"):
            after += 1

        if prev > 0 and after < len(symbolList):
            # If VAR or FUN look for type
            if symbolList[prev].semantic == "VAR" or symbolList[prev].semantic == "FUN":
                declareExist = table.lookup(symbolList[prev])
                    
                # Node found
                if declareExist != None:
                    symbolList[after].type = declareExist.type


            # If VAR or FUN look for type
            if symbolList[after].semantic == "VAR" or symbolList[after].semantic == "FUN":
                declareExist = table.lookup(symbolList[after])
                    
                # Node found
                if declareExist != None:
                    symbolList[after].type = declareExist.type

            
            if (symbolList[prev].type != symbolList[after].type):
                errorFile.write(f'\nSemantic Error at Line {node.line}: Mismatch type assignment. Type: {symbolList[prev].type} to {symbolList[after].type}')            
        
        return table
    
    # Check if variable was declared earlier
    def process_variable(node, table, scopeNum):
        
        if table.table:

            # Assign scope id to node using previous token scope id
            node.scope = table.table[-1].scope

        # Check parent scope for scope id
        else:
            node.scope = scopeNum

        # If referencing variable
        if node.type == None:
            declareExist = table.lookup(node)
            
            # Node found
            if declareExist != None:
                node.type = declareExist.type

            # Node never declared
            else:
                errorFile.write(f'\nSemantic Error at Line {node.line}: Undeclared Variable. Variable: {node.token}')            

        # Add token to current scope table
        table.table.append(node)

        # Add symbol to table data
        addToUpdatedTable(node)

        return table

    # Check if function is being called if so check if params match or if being declared make new scope
    def process_function(node, table, index, symbolList, scopeNum):
        
        if table.table:

            # Assign scope id to node using previous token scope id
            node.scope = table.table[-1].scope

        # Check parent scope for scope id
        else:
            node.scope = scopeNum

        # If referencing function
        if node.type == None:
            declareExist = table.lookup(node)
            
            # Node found
            if declareExist != None:
                node.type = declareExist.type

                # If params exist
                if node.param_types:

                    # Check if params match but how for variables? (loop params?)
                    indexCount = 0

                    # First assign types for variables by looking for var declarations for type
                    while indexCount < len(node.param_types):
                        parameter = node.param_types[indexCount]

                        if parameter != "INT" and parameter != "FLT":
                            
                            # Lookup variables to get types
                            declareVar = table.lookup(parameter)
                            
                            # Var found and replace var with type 
                            if declareVar != None:
                                node.param_types[indexCount] = declareVar.type
                        indexCount += 1
                    
                # If param types do not equal to declared param types
                if declareExist.param_types != node.param_types:
                    errorFile.write(f'\nSemantic Error at Line {node.line}: Mismatch parameter type function call. Type: {declareExist.param_types} to {node.param_types}')            
        
            # Node never declared
            else:
                errorFile.write(f'\nSemantic Error at Line {node.line}: Undeclared Function.')   
            
            # Add token to current scope table
            table.table.append(node)

            # Add symbol to table data
            addToUpdatedTable(node)         

        # If declaring function
        else:
            # Add token to current scope table
            table.table.append(node)

            # Add symbol to table data
            addToUpdatedTable(node)

            # Create a new scope in the symbol table
            table = table.enter_scope()

            # Increase scope
            scopeNum += 1

        return table, scopeNum

    # Check if return type matches function type and close scope
    def process_return(node, table, scopeNum):
        
        if table.table:

            # Assign scope id to node using previous token scope id
            node.scope = table.table[-1].scope

        # Check parent scope for scope id
        else:
            node.scope = scopeNum

        # Check if return param matches function return type (loop params?)


        # Add token to current scope table
        table.table.append(node)

        # Add symbol to table data
        addToUpdatedTable(node)
        return table

    # Simply add literal to table
    def process_literal(node, table, scopeNum):
        
        if table.table:
            # Assign scope id to node using previous token scope id
            node.scope = table.table[-1].scope

        # Check parent scope for scope id
        else:
            node.scope = scopeNum

        # Add token to current scope table
        table.table.append(node)

        # Add symbol to table data
        addToUpdatedTable(node)
        return table


    # Make list of symbol objects 
    while count < len(SEMANTIC):
        token = SEMANTIC[count]
        # ADD FUNCTIONALITY FOR DETERMINING SPECIFIC TYPES OF TOKENS (FUNCTIONS NEED SPECIAL FOR PARAMS, IDS VS FUNCTIONS)
        # WHAT ABOUT ARRAYS
        """
        Doubly Linked list of symbol tables as nodes 
        Concerned with matches context
        Include all symbols like orginal table
        Keywords that are start of scope are concerned only
        """
        
        # Token, Datatype, Line
        # Line, lexeme, token, semantic, scope, type, param_type
    
        # If Keyword (KEYWORD)
        if (token[1] == "KEYWORD"):
            # Start Block Keywords (If, While, def, else)
            if (token[0] == "if" or token[0] == "while" or token[0] == "def" or token[0] == "else"):
                ast.append(Symbol(token[2], token[1], token[0], "BLO", scopeNum, token[1], None))

            # End Block Keywords (od, fi, fed)
            elif (token[0] == "od" or token[0] == "fi" or token[0] == "fed"):
                ast.append(Symbol(token[2], token[1], token[0], "END", scopeNum, token[1], None))

            # Return keyword (return)
            elif (token[0] == "return"):
                ast.append(Symbol(token[2], token[1], token[0], "RTN", scopeNum, token[1], None))

            # Type keywords (int, double)
            elif(token[0] == "int" or token[0] == "double"):
                ast.append(Symbol(token[2], token[1], token[0], "TYP", scopeNum, token[1], None))

            # Other keywords (then,do,print,or,and,not)
            else:
                ast.append(Symbol(token[2], token[1], token[0], "KEY", scopeNum, token[1], None))
            

        # If Literal (INT, FLT)
        elif (token[1] == "INT" or token[1] == "FLT"):
            ast.append(Symbol(token[2], token[1], token[0], "NUM", scopeNum, token[1], None))

        # If Comparator
        elif (token[1] == "LT" or token[1] == "LE" or token[1] == "EV" or token[1] == "GT" or token[1] == "GE"):
            ast.append(Symbol(token[2], token[1], token[0], "COM", scopeNum, "COMPARATOR", None))

        # If Assignment
        elif (token[1] == "EQ"):
            ast.append(Symbol(token[2], token[1], token[0], "ASG", scopeNum, "ASSIGNMENT", None))

        # If Operator
        elif (token[1] == "ADD" or token[1] == "SUB" or token[1] == "MLT" or token[1] == "DIV" or token[1] == "MOD"):
            ast.append(Symbol(token[2], token[1], token[0], "OPR", scopeNum, "OPERATION", None))

        # If Variable or Function (ID)
        elif (token[1] == "ID"):
            # Get previous and previous previous tokens to determine if current id is a variable or function (function will have def token as prevPrev)
            prevPrev = SEMANTIC[count-2]
            prev = SEMANTIC[count-1]
            nextToken = SEMANTIC[count+1]
            typeID = ""

            # Is redeclaring allowed?

            # If function being declared
            if (prevPrev[0] == "def"):
                
                # Retrieve all param types for function
                paramsCount = 1
                curr = SEMANTIC[count+paramsCount]
                paramTypes = []
                
                # Search through function params (What if nested function, its stops at first end bracket)
                while (curr[1] != "END_BKT"):
                    
                    # If int keyword
                    if (curr[1] == "KEYWORD" and curr[0] == "int"):
                        paramTypes.append("INT")
                    
                    # If double keyword
                    elif (curr[1] == "KEYWORD" and curr[0] == "double"):
                        paramTypes.append("FLT")
                    
                    # Increment
                    paramsCount += 1
                    curr = SEMANTIC[count+paramsCount]
                    
                if prev[0] == "int":
                    typeID = "INT"
                else:
                    typeID = "FLT"

                ast.append(Symbol(token[2], token[1], token[0], "FUN", scopeNum, typeID, paramTypes))
            
            # If variable declared
            elif (prev[1] == "KEYWORD" and (prev[0] == "int" or prev[0] == "double")):
                if prev[0] == "int":
                    typeID = "INT"
                else:
                    typeID = "FLT"
                ast.append(Symbol(token[2], token[1], token[0], "VAR", scopeNum, typeID, None))

            # If function called (Set type to None to use as identifier to check for prior declaration)
            elif (nextToken[1] == "STR_BKT"):
                
                # Retrieve all param terms for function
                paramsCount = 1
                curr = SEMANTIC[count+paramsCount]
                paramTypes = []
                commaBuffer = False
                while (curr[1] != "END_BKT"):
                    
                    # if variable # Don't know what to do about figuring out var type (lookup is later and what if no declaration found)
                    if (commaBuffer == False and curr[1] == "ID"):
                        paramTypes.append(Symbol(curr[2], curr[1], curr[0], "VAR", scopeNum, None, None))
                        commaBuffer = True

                        # if function, what about function inception????
                        """if (commaBuffer == False and curr[1] == "ID"):
                        paramTypes.append(Symbol(curr[2], curr[1], curr[0], "VAR", scopeNum, None, None))
                        commaBuffer = True"""

                    # if number
                    elif (commaBuffer == False and (curr[1] == "INT" or curr[1] == "FLT")):
                        paramTypes.append(curr[1])
                        commaBuffer = True

                    # if comma
                    elif (curr[1] == "COM"):
                        commaBuffer = False

                    paramsCount += 1
                    curr = SEMANTIC[count+paramsCount]
                ast.append(Symbol(token[2], token[1], token[0], "FUN", scopeNum, None, paramTypes))
                # What about the types for the params in calls?
                # What about operations as params (a - b), solution assign the first var as the params type

            # If variable called (Set type to None to use as identifier to check for prior declaration)
            else:
                ast.append(Symbol(token[2], token[1], token[0], "VAR", scopeNum, None, None))
        
        # Else Literal (puncuation)
        else:
            ast.append(Symbol(token[2], token[1], token[0], "LIT", scopeNum, token[1], None))
        count += 1
    

    scopeNum = 0

    nodeCount = 0
    if (len(ast) > 0):
        # Traverse the parsed tokens
        while nodeCount < len(ast):

            # point to current node
            node = ast[nodeCount]
            
            # Start of scope
            if node.semantic == "BLO":
                symbol_table, scopeNum = process_block(node, symbol_table, scopeNum)

            # End of scope
            elif node.semantic == "END":
                symbol_table = process_end(node, symbol_table, scopeNum)

            # if assignment or comparator or operator
            elif node.semantic == "ASG" or node.semantic == "COM" or node.semantic == "OPR":
                symbol_table = process_typematch(node, symbol_table, nodeCount, ast, scopeNum)

            # If keyword that doesn't affect scope
            elif node.semantic == "KEY" or node.semantic == "TYP":
                symbol_table = process_literal(node, symbol_table, scopeNum)

            # If variable
            elif node.semantic == "VAR":
                symbol_table = process_variable(node, symbol_table, scopeNum)

            # If function
            elif node.semantic == "FUN":
                symbol_table, scopeNum = process_function(node, symbol_table, nodeCount, ast, scopeNum)
            
            # If return
            elif node.semantic == "RTN":
                symbol_table = process_return(node, symbol_table, scopeNum)

            # If literal
            elif node.semantic == "LIT" or node.semantic == "NUM":
                symbol_table = process_literal(node, symbol_table, scopeNum)

            # Increment to next token
            nodeCount += 1

    # Collct symbols for 3 tac conversion
    for symbol in ast:
        TO3TAC.append(symbol)

    return   

# Generate 3TAC
def generateIR():
    global TO3TAC, INTERMEDIATEFILE

    tempVarCount = 1
    blockCount = 1
    endCount = 1
    indexCount = 0



    """for symbol in TO3TAC:
        symbol.print()"""

    # Branch to main
    INTERMEDIATEFILE.write("BL main\n")

    while indexCount < len(TO3TAC):
        symbol = TO3TAC[indexCount]

        # Make labels for different scopes
        if symbol.semantic == "BLO":
            INTERMEDIATEFILE.write(f'{symbol.token}{blockCount}:\n')
            blockCount +=1

        # Make end label for closing scopes
        elif symbol.semantic == "END":
            INTERMEDIATEFILE.write(f'{symbol.token}{endCount}:\n')

        # Branch to function calls, while loops, if/else statements
        elif symbol.semantic == "FUN":
            INTERMEDIATEFILE.write(f'BL {symbol.token}\n')
        

        # Compare function for comparisons 
        elif symbol.semantic == "COM":
            INTERMEDIATEFILE.write(f'CMP {TO3TAC[indexCount-1]} {TO3TAC[indexCount+1]}\n')

        # Move function for assignments
        elif symbol.semantic == "ASG":
            INTERMEDIATEFILE.write(f'MOV {TO3TAC[indexCount-1]} {TO3TAC[indexCount+1]}\n')

        # Add/Sub/Mul/Div/Mod function for operators 
        elif symbol.semantic == "OPR":
            operation = ""
            if symbol.token == "+":        
               operation = "ADD"
            if symbol.token == "-":        
               operation = "SUB"
            if symbol.token == "*":        
               operation = "MUL"
            if symbol.token == "/":        
               operation = "DIV"
            if symbol.token == "%":        
               operation = "MOD"
            INTERMEDIATEFILE.write(f'{operation} {TO3TAC[indexCount-1]} {TO3TAC[indexCount+1]}\n')

        # print function for print
        elif symbol.semantic == "KEY" and symbol.token == "print":
            INTERMEDIATEFILE.write(f'PRT {TO3TAC[indexCount+1]}\n')

        # Make temps 
    
        indexCount += 1
    

    return

#Main
def main():
    global currentLine, EOFState, currentState, currentToken, nextState, dataType, symbolTableData, KEYWORDS, LLOneDict, firstSetDict, followSetDict, errorFile, tokenFile, UpdatedTableData
    SetsAndTable()

    #Grab file name from commandline
    try:
        fileName = sys.argv[1]
        fileName = checkFileExt(fileName)
    except:
        fileName = checkFileExt(fileName)


    #Writes Opening Divider to separate different file entries
    errorFile.write("--------------------------------\nErrors for file: " + fileName +"\n")
    tokenFile.write("--------------------------------\nTokens for file: " + fileName +"\n")
    
    #Read source code file
    with open(fileName, "rb") as sourceFile:

        #Make buffers
        buffer1 = bytearray(BUFFERSIZE)
        buffer2 = bytearray(BUFFERSIZE)

        #Load first buffer and returns number of bytes loaded
        bytes_read = sourceFile.readinto(buffer1)
        byte_pointer = bytes_read

        #Loop while buffer hasnt reached end symbol/byte
        while EOFState == False:
            
            
            #Read through buffer
            for symbols in buffer1:
                            
                #New line ASCII value
                if(symbols == 10 or symbols == 13):
                    #Add to symbol table
                    addToSymbolTable(currentToken, dataType, currentLine)

                    if symbols == 10:
                        #Increase line counter
                        currentLine += 1
                    nextState = 0
                    currentState = 0
                    
                    #Add token to file
                    tokenFile.write(currentToken + "\n")
                    
                    #Reset token data type
                    dataType = ""

                    #Reset current token tracker
                    currentToken = ""

                #Tab ASCII value
                elif(symbols == 9):
                    
                    #Add to symbol table
                    addToSymbolTable(currentToken, dataType, currentLine)

                    nextState = 0
                    currentState = 0
                    
                    #Add token to file
                    tokenFile.write(currentToken + "\n")
                    
                    #Reset token data type to SPC for Tab
                    dataType = "SPC"

                    #Add Tab spacing a token (For now could remove)
                    currentToken = chr(symbols)

                    #Add token to file
                    tokenFile.write(currentToken + "\n")

                    #Add to symbol table
                    addToSymbolTable(currentToken, dataType, currentLine)

                    #Reset token data type
                    dataType = ""

                    #Reset current token tracker
                    currentToken = ""


                #EOF value
                elif(symbols == 0):
                    EOFState = True
                    break


                #Do lexical analysis
                else:
                    #Retrieve next state based on next input and current state
                    nextState = getNextToken(chr(symbols).lower(), currentState)
                    #print(chr(symbols) + " \t--> " + str(nextState))
                    

                    #If state -1, invalid input error with next character
                    if(nextState == -1):
                        nextState = 0
                        #Skip input

                        #Add to error file
                        errorFile.write("Error at line " + str(currentLine) + ", caused by: " + chr(symbols) + "\n")


                    #If state -2, invalid input error with current character
                    elif(nextState == -2):
                        nextState = 0
                        currentState = 0
                        #Remove \ character
                        
                        #Add to error file
                        errorFile.write("Error at line " + str(currentLine) + ", caused by: " + currentToken + "\n")
                        
                        #Reset current token tracker
                        currentToken = ""


                    #If state 0 or 20 valid token final state, reset to 0 state
                    elif(nextState == 20 or nextState == 0):
                        #If start of token mark token data type
                        nextState = 0
                        
                        #Set data type for token
                        setDataType(currentState, symbols)

                        #Set current state based on next token after ending    
                        currentState = getNextToken(chr(symbols).lower(), 0)

                        #Add to symbol table
                        addToSymbolTable(currentToken, dataType, currentLine)

                        #Add token to file
                        tokenFile.write(currentToken + "\n")
                        
                        #Reset current token tracker
                        currentToken = "" + chr(symbols).lower()
                        
                        #Reset token data type
                        dataType = ""
                        
                        #Set data type for new token
                        setDataType(currentState, symbols)
                    

                    #If valid state
                    else:
                        #Add character to token
                        currentToken = currentToken + chr(symbols).lower()
                        currentState = nextState
                        
                        #Set data type for token
                        setDataType(nextState, symbols)
    
            
            #Check if EOF
            if(EOFState == False):
                #Load second buffer
                bytes_read = sourceFile.readinto(buffer2)
                
                #Set pointer to last byte read
                byte_pointer = byte_pointer + bytes_read
                sourceFile.seek(byte_pointer)
                
                #Switch between buffers
                buffer1, buffer2 = buffer2, buffer1
                
                #Reset buffer2 to remove previous characters filling array in case when next read is less than buffer size
                buffer2 = bytearray(BUFFERSIZE)
            
            #Reached end of file and checking for ending period
            elif(currentToken == "."):
                #Add to symbol table
                addToSymbolTable(currentToken, dataType, currentLine)

                #Add token to file
                tokenFile.write(currentToken + "\n")

    #Make symbol table excel file    
    exportExcel("Symbol_Table", "Sheet1", symbolTableData)
    
    Parse(LEXEMES)
    AnalyseSemantics()
    
    # Export updated symbol table excel file
    exportUpdatedTable("Updated_Table", "Sheet1", UpdatedTableData)
    
    generateIR()


main()